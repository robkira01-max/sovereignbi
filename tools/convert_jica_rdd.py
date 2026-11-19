"""Convert the JICA thematic shapefiles of the Republic of Djibouti (hydrogeology, climate, soils, water points)
to WGS84 GeoJSON (gzip) and register them in data/geo/catalog.yaml as DRAFT + DISABLED layers.

Source (per the project owner, 2026-11-19): JICA — NOT CERD. Licence NOT confirmed: layers stay draft/disabled until
a written licence is obtained (project rule: no layer without a verified licence).

Usage:  python3 -P tools/convert_jica_rdd.py <dir "RDD avec toutes thèmes"> <dir cartarcgis> [--dry-run]
(geopandas required; run from outside the data directory.)
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

os.environ["SHAPE_RESTORE_SHX"] = "NO"      # jamais de reconstruction silencieuse : un index invalide doit faire échouer

import geopandas as gpd  # noqa: E402
import yaml  # noqa: E402

def glob_escape(x: str) -> str:
    return x.replace("[", "[[]")


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "geo" / "jica"
CATALOG = ROOT / "data" / "geo" / "catalog.yaml"
SOURCE = "JICA (source indiquée par le propriétaire, 2026-11-19) — jeu « RDD toutes thèmes », données ~2007-2008"
LICENSE = "Licence NON confirmée — à obtenir par écrit auprès de la JICA / du détenteur avant tout usage"
SIMPLIFY_M = 5.0          # tolerance in metres (UTM 38N) before reprojection

# id, relative path (root key "rdd" or "arc"), fr name, en name, fr desc, en desc, name column, encoding, rename
LAYERS = [
    ("jica_systemes_aquiferes", "rdd", "RDD SYSTEME AQUIFERES/systemeAquif.shp", "Systèmes aquifères", "Aquifer systems",
     "61 polygones de systèmes aquifères (classe SystAquif, libellé Name).", "61 aquifer-system polygons (class SystAquif, label Name).", "Name", "cp1252"),
    ("jica_debit_aquiferes", "rdd", "RDD débit aquifère/debiaquif.shp", "Débit des aquifères (classes)", "Aquifer yield (classes)",
     "61 polygones, classe de débit (champ Debit). La légende des classes est à obtenir.", "61 polygons, yield class (field Debit). Class legend to be obtained.", "Name", "cp1252"),
    ("jica_pluie_moyenne", "rdd", "RDD PLUIE MOYENNE ANNUEL/pluiemoyenne.shp", "Pluie moyenne annuelle (mm)", "Mean annual rainfall (mm)",
     "14 polygones d'isohyètes, pluie moyenne annuelle en mm (champ Pluiemoyen).", "14 isohyet polygons, mean annual rainfall in mm (field Pluiemoyen).", "Pluiemoyen", "cp1252"),
    # Sols : Nm_sols.shp est tronqué/corrompu (enregistrement invalide à l'octet 668920) — en attente d'une copie saine.
    ("jica_etp", "arc", "fichiers climat/ETP/ETP.shp", "Évapotranspiration potentielle (ETP)", "Potential evapotranspiration (ETP)",
     "11 polygones d'ETP (champ ETP).", "11 PET polygons (field ETP).", "ETP", "cp1252"),
    ("jica_etr", "arc", "fichiers climat/ETR/ETR.shp", "Évapotranspiration réelle (ETR)", "Actual evapotranspiration (ETR)",
     "3 polygones d'ETR (champ ETR).", "3 AET polygons (field ETR).", "ETR", "cp1252"),
    ("jica_zones_climatiques", "arc", "fichiers climat/ZONES CLIMATIQUES/zoneclim.shp", "Zones climatiques", "Climate zones",
     "7 zones climatiques (champ zoneclimat).", "7 climate zones (field zoneclimat).", "zoneclimat", "cp1252"),
]
WATER_POINTS = [   # "finalisé" versions only (curated); one layer per region, merged into one point layer
    ("Ali-Sabieh", "RDD POINT D EAU&QUALITE DEAU/RDD PONT D EAU/Region d'Ali-Sabieh/Point_d'eau_Ali-Sabieh_Finalisé.shp"),
    ("Arta", "RDD POINT D EAU&QUALITE DEAU/RDD PONT D EAU/Region d'Arta/Point_d'eau_Arta_finalisé.shp"),
    ("Obock", "RDD POINT D EAU&QUALITE DEAU/RDD PONT D EAU/Region d'Obock/Point_d'eau_Finalisé.shp"),
    ("Dikhil", "RDD POINT D EAU&QUALITE DEAU/RDD PONT D EAU/Region de Dikhil/Point_d'eau_de_Dikhil_finalisé.shp"),
    ("Tadjourah", "RDD POINT D EAU&QUALITE DEAU/RDD PONT D EAU/Region de Tadjourah/Point_d'eau_Tadjourah_finalisé.shp"),
]


def read(path: Path, encoding: str) -> gpd.GeoDataFrame:
    """Lit une COPIE de la couche : les données sources (Downloads) ne sont jamais ouvertes en place ni modifiées."""
    with tempfile.TemporaryDirectory() as tmp:
        for side in path.parent.glob(glob_escape(path.stem) + ".*"):
            shutil.copy2(side, Path(tmp) / side.name)
        gdf = gpd.read_file(Path(tmp) / path.name, encoding=encoding)
    if gdf.crs is None:
        sys.exit(f"CRS manquant pour {path.name}: refus de deviner la projection")
    if gdf.crs.to_epsg() != 32638:
        sys.exit(f"CRS inattendu ({gdf.crs}) pour {path.name}")
    return gdf


def finish(gdf: gpd.GeoDataFrame, polygons: bool) -> gpd.GeoDataFrame:
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if polygons:
        gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_M, preserve_topology=True).buffer(0)
    return gdf.to_crs(4326)


def write(layer_id: str, gdf: gpd.GeoDataFrame, dry: bool) -> int:
    fc = json.loads(gdf.to_json(drop_id=True))
    for f in fc["features"]:
        for k, v in list(f["properties"].items()):
            if isinstance(v, float) and v != v:
                f["properties"][k] = None
    raw = json.dumps(fc, ensure_ascii=False, separators=(",", ":"))
    if not dry:
        OUT.mkdir(parents=True, exist_ok=True)
        with gzip.open(OUT / f"{layer_id}.geojson.gz", "wt", encoding="utf-8", compresslevel=9) as fh:
            fh.write(raw)
    return len(fc["features"])


def entry(layer_id, name_fr, name_en, d_fr, d_en, geom, n, name_col, coverage="Djibouti — national"):
    return {
        "id": layer_id, "name_fr": name_fr, "name_en": name_en, "description_fr": d_fr, "description_en": d_en,
        "format": "geojson", "geometry_type": geom, "source": SOURCE, "license": LICENSE, "license_url": "",
        "date_acquired": date.today().isoformat(), "coverage": coverage, "feature_count": n, "status": "draft",
        "enabled": False, "api_endpoint": f"/api/v1/geo/dj/{layer_id}", "file_path": f"data/geo/jica/{layer_id}.geojson.gz",
        "name_column": name_col,
        "warnings": [{"fr": "Licence non confirmée : couche désactivée. Ne pas diffuser avant accord écrit.",
                      "en": "Licence not confirmed: layer disabled. Do not distribute before written agreement."}],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("rdd"), ap.add_argument("arc")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    roots = {"rdd": Path(a.rdd), "arc": Path(a.arc)}
    entries = []
    for lid, key, rel, nfr, nen, dfr, den, col, enc in LAYERS:
        p = roots[key] / rel
        if not p.exists():
            sys.exit(f"Introuvable : {p}")
        gdf = finish(read(p, enc), polygons=True)
        n = write(lid, gdf, a.dry_run)
        entries.append(entry(lid, nfr, nen, dfr, den, "Polygon", n, col))
        print(f"{lid:28} {n:5} entités")
    parts = []
    for region, rel in WATER_POINTS:
        p = roots["rdd"] / rel
        if not p.exists():
            sys.exit(f"Introuvable : {p}")
        g = read(p, "cp850")
        g["region"] = region
        parts.append(g[["NOM_PT_D_E", "region", "geometry"]].rename(columns={"NOM_PT_D_E": "nom"}))
    wp = finish(gpd.GeoDataFrame(__import__("pandas").concat(parts, ignore_index=True), crs=parts[0].crs), polygons=False)
    n = write("jica_points_eau", wp, a.dry_run)
    entries.append(entry("jica_points_eau", "Points d'eau (5 régions, versions finalisées)", "Water points (5 regions, finalised versions)",
                         f"{n} points d'eau (nom, région). Attributs détaillés (profondeur, type d'ouvrage…) non repris : à valider.",
                         f"{n} water points (name, region). Detailed attributes (depth, structure type…) not carried over: to be validated.",
                         "Point", n, "nom", coverage="5 régions (hors Djibouti-ville)"))
    print(f"{'jica_points_eau':28} {n:5} entités")
    if a.dry_run:
        print("dry-run : rien d'écrit")
        return
    cat = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    ids = {e["id"] for e in entries}
    cat["layers"] = [l for l in cat["layers"] if l["id"] not in ids] + entries     # idempotent
    CATALOG.write_text(yaml.safe_dump(cat, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    print(f"{len(entries)} couches enregistrées (draft, désactivées) dans {CATALOG.name}")


if __name__ == "__main__":
    main()
