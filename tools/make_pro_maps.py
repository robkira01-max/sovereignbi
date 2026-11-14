"""
MizanBI — Cartes professionnelles Djibouti (Option A cartopy)
Génère 2 cartes print-quality :
  - dj_pro_map_population.png   : choroplèthe population 2024 (Jenks)
  - dj_pro_map_sante.png        : structure sanitaire + ratio hab/agent
Requires: cartopy mapclassify contextily geopandas pyproj matplotlib
Install : /home/kali/sovereignbi/.venv/bin/pip install cartopy mapclassify contextily
"""
import math, json, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.ticker as mticker
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
from shapely.geometry import shape
import cartopy.crs as ccrs
import cartopy.feature as cfeature
try:
    from cartopy.mpl.gridliner import LongitudeFormatter, LatitudeFormatter
except ImportError:
    from cartopy.mpl.gridliner import LONGITUDE_FORMATTER as LongitudeFormatter
    from cartopy.mpl.gridliner import LATITUDE_FORMATTER as LatitudeFormatter
import mapclassify
import contextily as ctx
warnings.filterwarnings('ignore')

# ─── Paramètres ──────────────────────────────────────────────────────────────
PROJ   = ccrs.UTM(zone=38)          # projection locale Djibouti
GEO    = ccrs.PlateCarree()         # WGS-84
BBOX   = [41.6, 44.6, 10.7, 13.1]  # lon_min, lon_max, lat_min, lat_max

REGION_MAP = {
    'Djibouti-ville': 'Djibouti',
    'djibouti_ville': 'Djibouti',
    'Ali-Sabieh':     'Ali Sabieh',
}
def norm(r): return REGION_MAP.get(str(r), r)

ORDER = ['Djibouti','Arta','Ali Sabieh','Dikhil','Tadjourah','Obock']

# ─── Chargement données ───────────────────────────────────────────────────────
print("Chargement données…")
pop = pd.read_csv('data/instad/population_region.csv')
pop['region_norm'] = pop['region'].map(norm)
rp24 = (pop[pop['annee_recensement'] == 2024]
        .groupby('region_norm')
        .agg(pop_tot=('population_totale','sum'))
        .reset_index())
pop_dict = dict(zip(rp24['region_norm'], rp24['pop_tot']))

sante = pd.read_csv('data/instad/structures_sante.csv')
sante['region_norm'] = sante['region'].map(norm)
rs = (sante.groupby('region_norm')
           .agg(nb_struct=('structure','count'),
                total_pers=('total_personnel','sum'))
           .reset_index())
rs_dict_pers   = dict(zip(rs['region_norm'], rs['total_pers']))
rs_dict_struct = dict(zip(rs['region_norm'], rs['nb_struct']))

sante_gps = sante[sante['lat'].notna() & sante['lon'].notna()].copy()

# ─── GeoDataFrame ADM1 ───────────────────────────────────────────────────────
gdf = gpd.read_file('data/geo/dji_adm1.geojson').to_crs('EPSG:4326')
gdf['region'] = gdf['shapeName'].map(lambda x: x)
gdf['pop_2024']        = gdf['region'].map(pop_dict).astype(float)
gdf['total_pers']      = gdf['region'].map(rs_dict_pers).astype(float)
gdf['nb_struct']       = gdf['region'].map(rs_dict_struct).astype(float)
gdf['area_km2']        = gdf.to_crs('EPSG:32638').geometry.area / 1e6
gdf['pop_density']     = gdf['pop_2024'] / gdf['area_km2']
gdf['hab_par_agent']   = gdf['pop_2024'] / gdf['total_pers']
gdf['centroid_lon']    = gdf.geometry.centroid.x
gdf['centroid_lat']    = gdf.geometry.centroid.y

# Fix centroid Djibouti-ville (trop compressé)
gdf.loc[gdf['region']=='Djibouti','centroid_lat'] = 11.70

print("GDF prêt:", gdf[['region','pop_2024','pop_density','hab_par_agent']].to_string())

# ─── Palettes ColorBrewer ────────────────────────────────────────────────────
# Blues pour population density
CMAP_BLUES = LinearSegmentedColormap.from_list(
    'blues_dj', ['#f0f9ff','#bae6fd','#38bdf8','#0ea5e9','#0369a1','#1e3a5f'], N=256)
# Orange-Red pour hab/agent (inverse : bon = vert, mauvais = rouge)
CMAP_RISK = LinearSegmentedColormap.from_list(
    'risk_dj', ['#dcfce7','#bbf7d0','#86efac','#f97316','#dc2626','#7f1d1d'], N=256)

# ─── Fonction dessin fond de carte ───────────────────────────────────────────
def _make_axes(fig, pos, title):
    ax = fig.add_subplot(pos, projection=PROJ)
    ax.set_extent(BBOX, crs=GEO)

    # Fond océan
    ax.add_feature(cfeature.OCEAN.with_scale('10m'), facecolor='#dbeafe', zorder=0)
    ax.add_feature(cfeature.LAND.with_scale('10m'),  facecolor='#f5f0e8', zorder=1)
    ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=0.8, zorder=4)
    ax.add_feature(cfeature.BORDERS.with_scale('10m'),   linewidth=0.6,
                   linestyle='--', edgecolor='#64748b', zorder=4)
    ax.add_feature(cfeature.RIVERS.with_scale('10m'),    linewidth=0.4,
                   edgecolor='#93c5fd', zorder=3)

    # Graticule
    gl = ax.gridlines(crs=GEO, draw_labels=True, linewidth=0.4,
                      color='#94a3b8', alpha=0.6, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.xlocator   = mticker.FixedLocator([42, 43, 44])
    gl.ylocator   = mticker.FixedLocator([11, 12, 13])
    gl.xformatter = LongitudeFormatter()
    gl.yformatter = LatitudeFormatter()
    gl.xlabel_style = {'size': 7, 'color': '#475569'}
    gl.ylabel_style = {'size': 7, 'color': '#475569'}

    ax.set_title(title, fontsize=11, fontweight='bold', pad=10, color='#1e293b')
    return ax

def _scale_bar(ax, length_km=100, loc=(0.08, 0.06)):
    """Barre d'échelle propre."""
    x0, y0 = loc
    deg = length_km / (111.32 * math.cos(math.radians(11.9)))
    # Convert from axes fraction to data
    xl, yl = ax.get_xlim(), ax.get_ylim()
    dx = (xl[1]-xl[0]); dy = (yl[1]-yl[0])
    ax.annotate('', xy=(x0*dx+xl[0] + deg*(dx/abs(BBOX[1]-BBOX[0])), y0*dy+yl[0]),
                xytext=(x0*dx+xl[0], y0*dy+yl[0]),
                xycoords='data', textcoords='data',
                arrowprops=dict(arrowstyle='-', color='#1e293b', lw=2))
    ax.text(x0*dx+xl[0] + deg*(dx/abs(BBOX[1]-BBOX[0]))/2,
            y0*dy+yl[0] - dy*0.025,
            f'{length_km} km', ha='center', fontsize=7.5, color='#1e293b',
            transform=ax.transData)

def _north_arrow(ax):
    ax.annotate('N', xy=(0.96, 0.14), xycoords='axes fraction',
                ha='center', va='center', fontsize=10, fontweight='bold',
                color='#1e293b',
                path_effects=[pe.withStroke(linewidth=2, foreground='white')])
    ax.annotate('', xy=(0.96, 0.13), xytext=(0.96, 0.08),
                xycoords='axes fraction',
                arrowprops=dict(arrowstyle='-|>', color='#1e293b',
                                mutation_scale=14, lw=1.5))

# ════════════════════════════════════════════════════════════════════════════
#  MAP 1 — Densité de population 2024 (Jenks Natural Breaks)
# ════════════════════════════════════════════════════════════════════════════
print("Génération Carte 1 — Population…")
fig1 = plt.figure(figsize=(11, 12), facecolor='white')
fig1.suptitle(
    'République de Djibouti\nDensité de Population par Région — 2024 (projeté)',
    fontsize=13, fontweight='bold', y=0.99, color='#0f172a')

ax1 = _make_axes(fig1, 111, '')

# Classification Jenks
vals = gdf['pop_density'].dropna().values
classifier = mapclassify.FisherJenks(vals, k=5)
bounds  = [0] + list(classifier.bins)
colors5 = [CMAP_BLUES(i/4) for i in range(5)]
norm5   = BoundaryNorm(bounds, ncolors=256)

# Draw regions
for _, row in gdf.iterrows():
    cls = int(classifier.find_bin(row['pop_density'])[0])
    face = colors5[cls]
    ax1.add_geometries([row.geometry], crs=GEO,
                       facecolor=face, edgecolor='#1e293b',
                       linewidth=1.2, zorder=5)
    # Label
    effect = [pe.withStroke(linewidth=2.5, foreground='white')]
    ax1.text(row['centroid_lon'], row['centroid_lat'],
             f"{row['region']}\n{row['pop_2024']:,.0f} hab.\n"
             f"({row['pop_density']:.1f} hab/km²)",
             transform=GEO, ha='center', va='center',
             fontsize=7.5, color='#0f172a', fontweight='bold',
             path_effects=effect, zorder=8)

# Colorbar
sm1 = ScalarMappable(cmap=CMAP_BLUES, norm=norm5)
sm1.set_array([])
cbar1 = fig1.colorbar(sm1, ax=ax1, shrink=0.42, pad=0.03,
                       orientation='vertical', extend='neither')
cbar1.set_label('hab./km²', fontsize=8.5)
cbar1.ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x,_: f'{x:.1f}'))
cbar1.ax.tick_params(labelsize=7.5)
# Tick at class breaks
cbar1.set_ticks(bounds)

_north_arrow(ax1)

# Source + légende classification
fig1.text(0.01, 0.005,
    'Projection : UTM Zone 38N (EPSG:32638)  ·  Classification : Fisher-Jenks (k=5)\n'
    'Sources : INSTAD/RGPH (pop. 2009-2024 projetée)  ·  GADM ADM1 (CC BY 4.0)  ·  Natural Earth 10m',
    fontsize=6.5, color='#64748b', style='italic')

fig1.tight_layout(rect=[0, 0.03, 1, 0.97])
out1 = '/home/kali/dj_pro_map_population.png'
fig1.savefig(out1, dpi=200, bbox_inches='tight', facecolor='white')
plt.close(fig1)
print(f"  → {out1}")

# ════════════════════════════════════════════════════════════════════════════
#  MAP 2 — Accès aux soins : habitants par agent de santé (2020)
# ════════════════════════════════════════════════════════════════════════════
print("Génération Carte 2 — Santé…")
fig2 = plt.figure(figsize=(11, 12), facecolor='white')
fig2.suptitle(
    'République de Djibouti\nAccès aux Soins — Habitants par Agent de Santé (2020)',
    fontsize=13, fontweight='bold', y=0.99, color='#0f172a')

ax2 = _make_axes(fig2, 111, '')

# Quantile breaks on hab_par_agent
vals2 = gdf['hab_par_agent'].dropna().values
clf2  = mapclassify.Quantiles(vals2, k=5)
bounds2 = [0] + list(clf2.bins)
colors5b = [CMAP_RISK(i/4) for i in range(5)]
norm5b   = BoundaryNorm(bounds2, ncolors=256)

for _, row in gdf.iterrows():
    cls = int(clf2.find_bin(row['hab_par_agent'])[0])
    face = colors5b[cls]
    ax2.add_geometries([row.geometry], crs=GEO,
                       facecolor=face, edgecolor='#1e293b',
                       linewidth=1.2, zorder=5)
    effect = [pe.withStroke(linewidth=2.5, foreground='white')]
    ax2.text(row['centroid_lon'], row['centroid_lat'],
             f"{row['region']}\n{row['hab_par_agent']:.0f} hab/agent\n"
             f"({row['nb_struct']:.0f} structures)",
             transform=GEO, ha='center', va='center',
             fontsize=7.5, color='#0f172a', fontweight='bold',
             path_effects=effect, zorder=8)

# Structures sanitaires (points)
staff_max = sante_gps['total_personnel'].max()
for _, row in sante_gps.iterrows():
    s = max(18, (row['total_personnel'] / staff_max) * 320)
    ax2.scatter(row['lon'], row['lat'], s=s,
                color='#1d4ed8', alpha=0.80,
                edgecolors='white', linewidths=0.6,
                transform=GEO, zorder=9, marker='o')

# Legend structures
for size_val, label in [(1,'1-10'),(50,'50'),(200,'200'),(460,'460+')]:
    s = max(18, (size_val / staff_max) * 320)
    ax2.scatter([], [], s=s, color='#1d4ed8', alpha=0.80,
                edgecolors='white', linewidths=0.6, label=label)
leg = ax2.legend(title='Personnel\nde santé', loc='lower right',
                 fontsize=7.5, title_fontsize=7.5,
                 framealpha=0.85, markerscale=1.0)

# Seuil OMS annotation
ax2.text(0.01, 0.97,
    '⚠  Seuil OMS : < 1 000 hab./agent recommandé',
    transform=ax2.transAxes, fontsize=8, color='#dc2626',
    va='top', style='italic',
    path_effects=[pe.withStroke(linewidth=2, foreground='white')])

# Colorbar
sm2 = ScalarMappable(cmap=CMAP_RISK, norm=norm5b)
sm2.set_array([])
cbar2 = fig2.colorbar(sm2, ax=ax2, shrink=0.42, pad=0.03,
                       orientation='vertical')
cbar2.set_label('Hab. par agent de santé', fontsize=8.5)
cbar2.set_ticks(bounds2)
cbar2.ax.tick_params(labelsize=7.5)
cbar2.ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x,_: f'{x:.0f}'))

_north_arrow(ax2)

fig2.text(0.01, 0.005,
    'Projection : UTM Zone 38N (EPSG:32638)  ·  Classification : Quantiles (k=5)\n'
    'Sources : INSTAD Annuaire Statistique Santé 2020  ·  GADM ADM1 (CC BY 4.0)  ·  Natural Earth 10m',
    fontsize=6.5, color='#64748b', style='italic')

fig2.tight_layout(rect=[0, 0.03, 1, 0.97])
out2 = '/home/kali/dj_pro_map_sante.png'
fig2.savefig(out2, dpi=200, bbox_inches='tight', facecolor='white')
plt.close(fig2)
print(f"  → {out2}")
print("Terminé.")
