"""
MizanBI — Carte imprimable de Djibouti-ville (PDF, A3 paysage).

Couches : communes et 91 quartiers officiels (CERD admin_pol 2014), bâtiments
classés par usage, routes, hydrographie, voie ferrée (levé CERD 1/2 500, 2014).
Lit uniquement les fichiers de data/geo/ ; aucun accès réseau.

Usage :
    .venv/bin/python tools/make_djibouti_ville_map.py [sortie.pdf]
    ... --commune Balbala|Boulaos|Ras-Dika   (carte d'une commune, tous les quartiers nommés)
    ... --no-licence-warning                 (retire la ligne rouge sur la licence CERD)
"""
import argparse
import gzip
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

GEO = Path(__file__).resolve().parent.parent / "data" / "geo"
UTM = "EPSG:32638"  # UTM 38N, projection locale (mètres)
SEA, LAND = "#cfe3f1", "#f6f2e9"
INK, MUTED = "#0f172a", "#475569"

BUILDING_STYLE = {  # cat -> (libellé, couleur)
    "habitat": ("Habitat", "#9a8f80"),
    "habitat_dur": ("Bâtiment en dur (étages)", "#6b6258"),
    "education": ("Éducation", "#2563eb"),
    "sante": ("Santé", "#dc2626"),
    "administration": ("Administration", "#0891b2"),
    "commerce": ("Commerce, hôtellerie", "#ea580c"),
    "religion": ("Culte", "#7c3aed"),
    "industrie": ("Industrie, entrepôts", "#525252"),
    "reseaux": ("Réseaux, énergie, eau", "#ca8a04"),
    "culture": ("Culture", "#059669"),
    "ruine": ("Ruines", "#a8a29e"),
}


def read(name: str) -> gpd.GeoDataFrame:
    path = GEO / name
    src = gzip.open(path) if name.endswith(".gz") else path
    return gpd.read_file(src).to_crs(UTM)


def scale_bar(ax, km: float) -> None:
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    bx, by = x0 + (x1 - x0) * 0.05, y0 + (y1 - y0) * 0.05
    half = km * 1000 / 2
    for i, color in enumerate((INK, "white")):
        xs = [bx + i * half, bx + (i + 1) * half]
        ax.plot(xs, [by, by], color=INK, lw=7.5, solid_capstyle="butt", zorder=19)
        ax.plot(xs, [by, by], color=color, lw=5, solid_capstyle="butt", zorder=20)
    for v, lbl in ((0, "0"), (half, f"{km / 2:g}"), (2 * half, f"{km:g} km")):
        ax.text(bx + v, by + (y1 - y0) * 0.012, lbl, ha="center", fontsize=8,
                color=INK, zorder=21,
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])


def north_arrow(ax) -> None:
    ax.annotate("", xy=(0.95, 0.93), xytext=(0.95, 0.86), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=2, mutation_scale=20),
                zorder=20)
    ax.text(0.95, 0.945, "N", transform=ax.transAxes, ha="center", fontsize=13,
            fontweight="bold", color=INK, zorder=20)


def main(out: Path, commune: str | None = None, licence_warning: bool = True) -> None:
    communes = read("admin_communes.geojson")
    quartiers = read("admin_quartiers.geojson")
    bati = read("cerd_batiments.geojson.gz")
    routes = read("cerd_routes.geojson.gz")
    hydro = read("cerd_hydro.geojson.gz")
    rail = read("cerd_rail.geojson.gz")

    pts = bati.geometry.centroid
    if commune:
        target = communes[communes["nom"] == commune]
        if target.empty:
            raise SystemExit(f"Commune inconnue : {commune!r} (attendu : {sorted(communes['nom'])})")
        # Cadrage sur les quartiers de la commune (la limite communale inclut de la mer vide).
        quartiers_c = quartiers[quartiers["commune"] == commune]
        minx, miny, maxx, maxy = quartiers_c.total_bounds
        pad = 400
        # Décompte de la légende : bâtiments dont le centroïde est dans la commune.
        bati = bati[pts.within(target.geometry.union_all())]
        scope_q = quartiers_c
        label_min_ha = 0.0
        label_size = 7.0
        bar_km = 1
    else:
        # Cadrage sur la zone bâtie (0,5e-99,5e centile) plutôt que sur les communes
        # entières, dont de grandes étendues vides réduiraient le détail.
        minx, maxx = pts.x.quantile([0.005, 0.995])
        miny, maxy = pts.y.quantile([0.005, 0.995])
        pad = 1500
        scope_q = quartiers
        label_min_ha = 40.0
        label_size = 5.2
        bar_km = 2
    minx, miny, maxx, maxy = minx - pad, miny - pad, maxx + pad, maxy + pad

    fig = plt.figure(figsize=(16.54, 11.69), facecolor="white")  # A3 paysage
    ax = fig.add_axes([0.03, 0.07, 0.70, 0.83])
    ax.set_facecolor(SEA)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    for s in ax.spines.values():
        s.set_color(INK)
        s.set_linewidth(1.2)

    communes.plot(ax=ax, color=LAND, edgecolor="none", zorder=1)
    # Couches de masse rastérisées (86 776 polygones) ; limites et textes restent vectoriels.
    hydro.plot(ax=ax, color="#7fb2d8", edgecolor="none", zorder=2, rasterized=True)
    routes.plot(ax=ax, color="#ffffff", edgecolor="#b8b0a2", linewidth=0.15,
                zorder=3, rasterized=True)
    for cat, (_, color) in BUILDING_STYLE.items():
        sub = bati[bati["cat"] == cat]
        if len(sub):
            sub.plot(ax=ax, color=color, edgecolor="none", zorder=4, rasterized=True)
    rail.plot(ax=ax, color="#1f2937", linewidth=0.8, linestyle=(0, (4, 2)), zorder=5)

    quartiers.boundary.plot(ax=ax, color="#64748b", linewidth=0.35, zorder=6)
    communes.boundary.plot(ax=ax, color=INK, linewidth=1.6, zorder=7)

    halo = [pe.withStroke(linewidth=2.5, foreground="white")]
    for _, r in communes.iterrows():
        if commune:  # sur une carte de commune, pas de nom de commune au milieu des quartiers
            break
        p = r.geometry.representative_point()
        ax.text(p.x, p.y, r["nom"].upper(), ha="center", va="center", fontsize=15,
                fontweight="bold", color=INK, alpha=0.75, path_effects=halo, zorder=10)
    for _, r in scope_q.iterrows():
        if r["superficie_ha"] >= label_min_ha:  # grands quartiers seulement sur la vue d'ensemble
            p = r.geometry.representative_point()
            ax.text(p.x, p.y, r["nom"].title(), ha="center", va="center", fontsize=label_size,
                    color="#1e293b",
                    path_effects=[pe.withStroke(linewidth=1.5, foreground="white")],
                    zorder=9)

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    scale_bar(ax, bar_km)
    north_arrow(ax)

    title = f"Djibouti-ville — commune de {commune}" if commune else "Djibouti-ville"
    subtitle = (f"{len(scope_q)} quartiers officiels, bâtiments par usage, voirie et hydrographie"
                if commune else
                "Communes, quartiers officiels, bâtiments par usage, voirie et hydrographie")
    fig.text(0.03, 0.955, title, fontsize=26, fontweight="bold", color=INK)
    fig.text(0.03, 0.925, subtitle, fontsize=12, color=MUTED)
    fig.text(0.73, 0.955, "MizanBI", fontsize=14, fontweight="bold", color=INK, ha="right")

    lax = fig.add_axes([0.75, 0.07, 0.23, 0.83])
    lax.axis("off")
    counts = bati["cat"].value_counts()
    handles = [Patch(facecolor=c, edgecolor="none",
                     label=f"{lbl}  ({counts.get(k, 0):,})".replace(",", " "))
               for k, (lbl, c) in BUILDING_STYLE.items()]
    leg1 = lax.legend(handles=handles, title="BÂTIMENTS (usage)", loc="upper left",
                      frameon=False, fontsize=9.5, title_fontsize=10.5,
                      alignment="left", bbox_to_anchor=(0, 1.0))
    lax.add_artist(leg1)
    other = [
        Patch(facecolor="white", edgecolor="#b8b0a2", label="Routes et emprises routières"),
        Patch(facecolor="#7fb2d8", edgecolor="none", label="Hydrographie"),
        Line2D([0], [0], color="#1f2937", lw=1.2, linestyle=(0, (4, 2)), label="Voie ferrée"),
        Line2D([0], [0], color="#64748b", lw=0.8, label=f"Limite de quartier ({len(scope_q)})"),
        Line2D([0], [0], color=INK, lw=2, label="Limite de commune"),
    ]
    lax.legend(handles=other, title="AUTRES COUCHES", loc="upper left", frameon=False,
               fontsize=9.5, title_fontsize=10.5, alignment="left",
               bbox_to_anchor=(0, 0.58))

    stats = "\n".join(f"{c} : {n} quartiers" for c, n in scope_q.groupby("commune").size().items())
    lax.text(0, 0.30, "DÉCOUPAGE OFFICIEL", fontsize=10.5, fontweight="bold", color=INK,
             transform=lax.transAxes)
    lax.text(0, 0.255, stats, fontsize=9.5, color=INK, va="top", transform=lax.transAxes,
             linespacing=1.6)
    lax.text(0, 0.10,
             "Projection : UTM zone 38N (EPSG:32638)\n"
             + ("Tous les quartiers sont nommés." if commune else "Étiquettes : quartiers de plus de 40 ha seulement."),
             fontsize=8.5, color=MUTED, va="top", transform=lax.transAxes, linespacing=1.5)

    fig.text(0.03, 0.040,
             "Source : CERD (Centre d'Études et de Recherche de Djibouti) — admin_pol et levé "
             "photogrammétrique 1/2 500 (ITRF2005, 2014), données fournies par le propriétaire du projet.",
             fontsize=8.5, color=MUTED)
    if licence_warning:
        fig.text(0.03, 0.020,
                 "Carte de travail : licence de réutilisation des données CERD non confirmée par écrit — "
                 "ne pas diffuser. Limites à valider par les autorités djiboutiennes. "
                 "Information, pas document opposable.",
                 fontsize=8.5, color="#b91c1c")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="pdf", dpi=200, facecolor="white")
    plt.close(fig)
    print(f"→ {out} ({out.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("out", nargs="?", default="carte_djibouti_ville.pdf")
    ap.add_argument("--commune", help="Balbala, Boulaos ou Ras-Dika")
    ap.add_argument("--no-licence-warning", action="store_true",
                    help="retire la ligne rouge (licence CERD non confirmée)")
    a = ap.parse_args()
    main(Path(a.out), a.commune, licence_warning=not a.no_licence_warning)
