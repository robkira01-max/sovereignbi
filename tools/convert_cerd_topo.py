"""Convert the CERD 1/2,500 photogrammetric topographic layers (2014, ITRF2005) to
WGS84 GeoJSON served on demand (gzip) by /api/v1/geo/dj/{level}.

Input : directory with road_pol / build / hydro / hydro_lin / rail_lin / built_pol shapefiles
Output: data/geo/cerd_{batiments,routes,hydro,rail,sites}.geojson.gz  (+ summary on stdout)

Usage:  python3 -P tools/convert_cerd_topo.py <shapefile_dir> [--min-area 12]
(geopandas required; run from outside the data directory.)
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SHAPE_ENCODING", "latin-1")
os.environ.setdefault("SHAPE_RESTORE_SHX", "YES")

import geopandas as gpd  # noqa: E402

OUT = Path(__file__).parent.parent / "data" / "geo"

# The source DBF lost accents ("Mosqu?e"): restore the known labels.
FIX = {
    "Mosqu?e": "Mosquée",
    "Bâtiment ordinare (contour)": "Bâtiment ordinaire",
    "Bâtiment en dur, Plus de 2 étages (contour)": "Bâtiment en dur, plus de 2 étages",
    "Bâtiment en ruine (seulement fondations)": "Bâtiment en ruine",
    "Poste de police / Gendarmérie": "Poste de police / Gendarmerie",
    "Carrière?> 25mx25m": "Carrière",
    "Cimetière?> 25mx25m": "Cimetière",
    "Parking?> 25mx25m": "Parking",
    "Parc?> 25mx25m": "Parc",
    "Zone franche, parc de maériels, décharge > 25mx25m": "Zone franche, parc de matériel, décharge",
    "Terrain de sport / stade": "Terrain de sport / stade",
    "Antenne de relais (télévision, radio, télécommunication)": "Antenne de relais",
    "Station de pompage eaux usées et d'eau potable": "Station de pompage",
    "Centre de traitement des eaux usées et d'eau potable": "Station de traitement des eaux",
    "Voie amenagée ?(Pas de distinction des types de revêtement)": "Voie aménagée",
    "Route non revêtue (contour)  (largeur > 2m, Longueur>26m)": "Route non revêtue",
    "Piste (contour)  (largeur > 2m, Longueur>27m)": "Piste",
    "Route revêtue (contour)  (largeur > 2m, Longueur>25m)": "Route revêtue",
    "Pont de route revêtue de largeur > 2m, et  Passage supérieur": "Pont (route revêtue)",
    "Pont de route non revêtue de largeur > 2m, et  Passage supérieur": "Pont (route non revêtue)",
    "Route en construction (Pas de distinction des types de revêtement)": "Route en construction",
    "Lac, Etang, Mare": "Lac, étang, mare",
    "Oued (largeur>2m),  (contour), Longueur>25m": "Oued",
    "Réservoir (pétrole), diamètre>10m": "Réservoir (pétrole)",
    "Réservoir (divers), diamètre>10m": "Réservoir (divers)",
    "Réservoir (eau), diamètre>10m": "Réservoir (eau)",
    "Réservoir (gaz), diamètre>3m": "Réservoir (gaz)",
    "Canal (largeur>2m),  (contour), Longueur>25m": "Canal",
}

# F_CODE of buildings (when F_CODE is 0/3402 the F_NAME decides) -> category key
BUILDING_CAT = {
    3524: "education", 3525: "education",
    3520: "religion", 3523: "religion",
    3532: "sante", 3531: "sante",
    3503: "administration", 3519: "administration", 3507: "administration", 3504: "administration",
    3509: "administration", 3515: "administration", 3505: "administration", 3516: "administration",
    3518: "administration",
    3539: "commerce", 3540: "commerce", 3541: "commerce", 3534: "commerce", 3560: "commerce", 3542: "commerce",
    3545: "industrie", 3548: "industrie", 3549: "industrie", 3536: "industrie", 3570: "industrie",
    3550: "reseaux", 3556: "reseaux", 3552: "reseaux", 4232: "reseaux", 4236: "reseaux",
    3526: "culture", 3527: "culture",
    3535: "ruine",
}


def clean(label: str) -> str:
    return FIX.get(label, label).strip()


def building_cat(code: int, label: str) -> str:
    if code in BUILDING_CAT:
        return BUILDING_CAT[code]
    return "habitat_dur" if "Plus de 2" in label else "habitat"


def round_coords(o, nd=5):
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, (list, tuple)):
        return [round_coords(x, nd) for x in o]
    if isinstance(o, dict):
        return {k: round_coords(v, nd) for k, v in o.items()}
    return o


def write_gz(gdf: gpd.GeoDataFrame, name: str, props: list[str]) -> dict:
    feats = []
    for row in gdf.itertuples(index=False):
        d = row._asdict()
        feats.append({
            "type": "Feature",
            "properties": {k: d[k] for k in props if d.get(k) not in (None, "")},
            "geometry": round_coords(d["geometry"].__geo_interface__),
        })
    payload = json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":"), ensure_ascii=False).encode()
    out = OUT / f"{name}.geojson.gz"
    out.write_bytes(gzip.compress(payload, 9, mtime=0))
    b = gdf.total_bounds
    return {"name": name, "features": len(feats), "raw_mb": round(len(payload) / 1e6, 1), "gz_mb": round(out.stat().st_size / 1e6, 2),
            "bbox": [round(float(v), 3) for v in b]}


def load(d: Path, name: str) -> gpd.GeoDataFrame:
    g = gpd.read_file(d / f"{name}.shp")
    g["_area"] = g.geometry.area if g.geom_type.iloc[0] in ("Polygon", "MultiPolygon") else 0.0
    g["_len"] = g.geometry.length
    g["geometry"] = g.geometry  # keep CRS for metric ops, reproject after filtering
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("shp_dir")
    ap.add_argument("--min-area", type=float, default=12.0, help="drop building footprints below this area (m2)")
    a = ap.parse_args()
    d = Path(a.shp_dir)
    res = []

    g = load(d, "build")
    g = g[g["_area"] >= a.min_area].copy()
    g["type"] = g["F_NAME"].map(clean)
    g["cat"] = [building_cat(int(c), str(n)) for c, n in zip(g["F_CODE"], g["F_NAME"])]
    g["geometry"] = g.to_crs(4326).geometry.simplify(0.000008)
    g = g.set_geometry("geometry").set_crs(4326, allow_override=True)
    res.append(write_gz(g, "cerd_batiments", ["cat", "type"]))

    r = load(d, "road_pol")
    r["type"] = r["F_NAME"].map(clean)
    r["revetue"] = r["F_CODE"].map(lambda c: "oui" if int(c) in (2101, 2203) and True else "non")
    r["revetue"] = [("oui" if "revêtue" in str(n) and "non revêtue" not in str(n) else "non") for n in r["F_NAME"]]
    r["geometry"] = r.to_crs(4326).geometry.simplify(0.000006)
    r = r.set_geometry("geometry").set_crs(4326, allow_override=True)
    res.append(write_gz(r, "cerd_routes", ["type", "revetue"]))

    h = load(d, "hydro")
    # « Ligne côtière » (F_CODE 5100) = polygone de mer découpé par feuilles de carte (bords en escalier) :
    # la mer est rendue comme fond uniforme par le client, on ne l'exporte pas.
    h = h[h["F_CODE"].astype(int) != 5100].copy()
    h["type"] = h["F_NAME"].map(clean)
    h["geometry"] = h.to_crs(4326).geometry.simplify(0.000008)
    h = h.set_geometry("geometry").set_crs(4326, allow_override=True)
    hl = load(d, "hydro_lin")
    hl["type"] = hl["F_NAME"].map(lambda s: "Oued (cours étroit)" if "Oued" in str(s) else "Cours d'eau, canal étroit")
    hl["geometry"] = hl.to_crs(4326).geometry.simplify(0.000008)
    hl = hl.set_geometry("geometry").set_crs(4326, allow_override=True)
    both = gpd.GeoDataFrame(
        {"type": list(h["type"]) + list(hl["type"])},
        geometry=list(h.geometry) + list(hl.geometry), crs=4326)
    res.append(write_gz(both, "cerd_hydro", ["type"]))

    rl = load(d, "rail_lin")
    rl["type"] = rl["F_NAME"].map(clean)
    rl["geometry"] = rl.to_crs(4326).geometry.simplify(0.000008)
    rl = rl.set_geometry("geometry").set_crs(4326, allow_override=True)
    res.append(write_gz(rl, "cerd_rail", ["type"]))

    s = load(d, "built_pol")
    s["type"] = s["F_NAME"].map(clean)
    s["geometry"] = s.to_crs(4326).geometry.simplify(0.000008)
    s = s.set_geometry("geometry").set_crs(4326, allow_override=True)
    res.append(write_gz(s, "cerd_sites", ["type"]))

    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
