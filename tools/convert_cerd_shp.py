"""Convert CERD Djibouti shapefiles (EPSG:32638 UTM 38N) → WGS84 GeoJSON.

Usage:
    python tools/convert_cerd_shp.py [--src PATH] [--out PATH] [--dry-run]

Layers converted (heavy ones excluded — Batiments 33k, vegetation 8k):
  cerd_equipements_scolaires    31 polygons — schools
  cerd_equipements_sociaux      81 polygons — socioeconomic facilities
  cerd_secteurs_adressage       14 polygons — address sectors
  cerd_communes                  2 polygons — communes
  cerd_ilots                  4010 polygons — city blocks (simplified)
  cerd_lignes_bus                5 lines    — bus routes
  cerd_terminus_bus              6 points   — bus terminals
  cerd_voirie                 1447 lines    — road hierarchy (simplified)
  cerd_ouvrages                 22 polygons — bridges / crossings
  cerd_typologies_urbaines      27 polygons — urban typology
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import geopandas as gpd
except ImportError:
    sys.exit("geopandas not installed. Run: pip install geopandas pyogrio")

_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_SRC = Path("/home/kali/Downloads/Donnees format SIG_SHP")
_DEFAULT_OUT = _REPO_ROOT / "data" / "geo" / "cerd"

WGS84 = "EPSG:4326"

LAYERS = [
    {
        "id": "cerd_equipements_scolaires",
        "src": "Equipements socio-eco/Equipements_scolaires.shp",
        "keep_cols": ["Categorie", "Sous_catég", "Nom", "Code_Prima", "Code_CEM", "Code_Lycee"],
        "rename": {"Sous_catég": "sous_categorie", "Categorie": "categorie", "Nom": "nom",
                   "Code_Prima": "code_primaire", "Code_CEM": "code_cem", "Code_Lycee": "code_lycee"},
        "simplify_m": None,
        "description_fr": "31 établissements scolaires de Djibouti-ville (CERD, 2015 env.)",
    },
    {
        "id": "cerd_equipements_sociaux",
        "src": "Equipements socio-eco/Equipements_socio_economiques.shp",
        "keep_cols": ["OBJECTID", "Categorie", "Sous_catég", "Nom"],
        "rename": {"Sous_catég": "sous_categorie", "Categorie": "categorie", "Nom": "nom", "OBJECTID": "objectid"},
        "simplify_m": None,
        "description_fr": "81 équipements socio-économiques (marchés, hôpitaux, mosquées, sports, etc.)",
    },
    {
        "id": "cerd_secteurs_adressage",
        "src": "Adressage/Secteur_adressage.shp",
        "keep_cols": ["OBJECTID", "Nom"],
        "rename": {"OBJECTID": "objectid", "Nom": "nom"},
        "simplify_m": None,
        "description_fr": "14 secteurs d'adressage de Djibouti-ville",
    },
    {
        "id": "cerd_communes",
        "src": "Limite_administrative/Decoupage_communal.shp",
        "keep_cols": ["Nom_commun"],
        "rename": {"Nom_commun": "commune"},
        "simplify_m": None,
        "description_fr": "2 communes administratives de Djibouti-ville",
    },
    {
        "id": "cerd_ilots",
        "src": "Batiments_ilots/ilots.shp",
        "keep_cols": ["Commune", "Arrondisse", "Quartier", "ZC", "ZD", "NO_ilot"],
        "rename": {"Arrondisse": "arrondissement", "Commune": "commune", "Quartier": "quartier",
                   "ZC": "zone_cadastrale", "ZD": "zone_domaniale", "NO_ilot": "num_ilot"},
        "simplify_m": 2.0,
        "description_fr": "4 010 îlots urbains de Djibouti-ville (simplifiés à 2 m)",
    },
    {
        "id": "cerd_lignes_bus",
        "src": "Voirie-mobilite/Ligne_Bus.shp",
        "keep_cols": ["Ligne", "Terminus"],
        "rename": {"Ligne": "ligne", "Terminus": "terminus"},
        "simplify_m": None,
        "description_fr": "5 lignes de bus de Djibouti-ville",
    },
    {
        "id": "cerd_terminus_bus",
        "src": "Voirie-mobilite/Terminus_bus.shp",
        "keep_cols": ["Nom"],
        "rename": {"Nom": "nom"},
        "simplify_m": None,
        "description_fr": "6 terminus de bus de Djibouti-ville",
    },
    {
        "id": "cerd_voirie",
        "src": "Voirie-mobilite/Reseau_routier_hierarchie.shp",
        "keep_cols": ["Hierachie", "Largeur", "Revetement"],
        "rename": {"Hierachie": "hierarchie", "Largeur": "largeur_m", "Revetement": "revetement"},
        "simplify_m": 1.0,
        "description_fr": "1 447 tronçons du réseau routier de Djibouti-ville (hiérarchie, simplifiés à 1 m)",
    },
    {
        "id": "cerd_ouvrages",
        "src": "Voirie-mobilite/Ouvrages_franchissement.shp",
        "keep_cols": ["Etat"],
        "rename": {"Etat": "etat"},
        "simplify_m": None,
        "description_fr": "22 ouvrages de franchissement (ponts, dalots)",
    },
    {
        "id": "cerd_typologies_urbaines",
        "src": "Typologie urbaine/Typologie_urbaine.shp",
        "keep_cols": ["Type_quart", "Nom", "Observatio"],
        "rename": {"Type_quart": "type_quartier", "Nom": "nom", "Observatio": "observation"},
        "simplify_m": None,
        "description_fr": "27 zones de typologies urbaines de Djibouti-ville",
    },
]


def convert_layer(layer: dict, src_base: Path, out_dir: Path, dry_run: bool) -> dict:
    src_path = src_base / layer["src"]
    if not src_path.exists():
        return {"id": layer["id"], "status": "SKIP", "reason": f"src not found: {src_path}"}

    gdf = gpd.read_file(src_path)
    gdf = gdf.to_crs(WGS84)

    if layer.get("simplify_m"):
        # Simplify in source CRS (meters) then reproject
        gdf_utm = gdf.to_crs("EPSG:32638")
        gdf_utm["geometry"] = gdf_utm["geometry"].simplify(layer["simplify_m"], preserve_topology=True)
        gdf = gdf_utm.to_crs(WGS84)

    keep = [c for c in layer["keep_cols"] if c in gdf.columns]
    gdf = gdf[keep + ["geometry"]].copy()
    gdf = gdf.rename(columns=layer["rename"])

    # Clean NaN → None for JSON
    for col in gdf.columns:
        if col != "geometry":
            gdf[col] = gdf[col].where(gdf[col].notna(), other=None)

    out_path = out_dir / f"{layer['id']}.geojson"
    n = len(gdf)
    bbox = list(gdf.total_bounds)  # [minx, miny, maxx, maxy]

    if dry_run:
        return {"id": layer["id"], "status": "DRY-RUN", "n": n, "out": str(out_path)}

    out_dir.mkdir(parents=True, exist_ok=True)
    gdf.to_file(out_path, driver="GeoJSON")

    size_kb = out_path.stat().st_size // 1024
    return {"id": layer["id"], "status": "OK", "n": n, "size_kb": size_kb, "out": str(out_path), "bbox": [round(x, 5) for x in bbox]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", default=str(_DEFAULT_SRC), help="Source directory with SHP sub-folders")
    parser.add_argument("--out", default=str(_DEFAULT_OUT), help="Output directory for GeoJSON files")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    src_base = Path(args.src)
    out_dir = Path(args.out)

    if not src_base.exists():
        sys.exit(f"Source directory not found: {src_base}")

    print(f"Source : {src_base}")
    print(f"Output : {out_dir}")
    print(f"Dry-run: {args.dry_run}\n")

    results = []
    for layer in LAYERS:
        r = convert_layer(layer, src_base, out_dir, args.dry_run)
        status_icon = "✅" if r["status"] in ("OK", "DRY-RUN") else "⚠️"
        print(f"{status_icon} {r['id']}: {r}")
        results.append(r)

    ok = sum(1 for r in results if r["status"] in ("OK", "DRY-RUN"))
    print(f"\n{ok}/{len(results)} layers converted.")


if __name__ == "__main__":
    main()
