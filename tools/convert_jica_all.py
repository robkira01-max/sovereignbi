"""Convert ALL remaining JICA shapefiles (geology, topography, hydrography, vegetation, soils, hazards...) into
themed WGS84 GeoJSON.gz layers registered as DRAFT in data/geo/catalog.yaml (source JICA, licence unconfirmed).

Rules: sources are read from COPIES; layer names are PROVISIONAL (JICA has not yet supplied the legends/naming):
class codes are the original file names, nothing is invented. Layers whose .prj is missing are accepted only when
their bounds fall inside the UTM 38N envelope of Djibouti, and are flagged in the catalogue.

Usage: python3 -P tools/convert_jica_all.py <dir "RDD avec toutes thèmes"> <dir cartarcgis> [--dry-run]
"""
from __future__ import annotations

import argparse, gzip, json, os, shutil, sys, tempfile
from datetime import date
from pathlib import Path

os.environ["SHAPE_RESTORE_SHX"] = "NO"

import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "geo" / "jica"
CATALOG = ROOT / "data" / "geo" / "catalog.yaml"
SOURCE = "JICA (source indiquée par le propriétaire, 2026-11-19) — jeu « RDD toutes thèmes », données ~2007-2008"
LICENSE = "Licence NON confirmée — à obtenir par écrit auprès de la JICA / du détenteur avant tout usage"
DROP = {"geometry", "PARTS_", "POINTS_", "LENGTH_", "AREA_", "ID_", "Shape_Leng", "Shape_Area", "RECNO", "Id", "FID_arta", "FID_Nm_sol"}
UTM38_X, UTM38_Y = (100_000, 400_000), (1_150_000, 1_450_000)

R, A = "rdd", "arc"
G = "RDD Géologie/"; T = "RDD TOPO/"; V = "RDD Vegetation_map/"; S = "RDD SOLS/"
AG = "agropastoral/agropastorale/"; G2 = "200geo/"; PC = "present-carte/"

# id, FR name, EN name, FR description, [(root, relative path, assume_utm38)], name column
GROUPS = [
    ("jica_geologie_formations", "Géologie — formations (noms de fichiers JICA)", "Geology — formations (JICA file names)",
     "Formations géologiques ; le code de classe est le nom du fichier d'origine (légende JICA attendue).",
     [(R, G + f"{n}.SHP", False) for n in ("ADOLEI", "BANQUISEL", "BDALHA", "BRECENT", "BSOMALI", "BSTRATOID", "MABLA", "RHYOSTRAT", "SEDIMENT", "SOCLE")], "source_file"),
    ("jica_failles", "Failles", "Faults", "Failles (lignes).", [(A, PC + "geologie/failles.shp", False)], "source_file"),
    ("jica_failles_favorables", "Zones de failles favorables", "Favourable fault zones", "Polygones « FAILLEFAVORABLE » (sens exact à confirmer par la JICA).", [(A, G2 + "FAILLEFAVORABLE.SHP", False)], "source_file"),
    ("jica_fracturation", "Fracturation (golfe, Dalha)", "Fracturing (gulf, Dalha)", "Linéaments de fracturation (3 fichiers sources).",
     [(A, G2 + "FRAC200GOLF.SHP", False), (A, G2 + "FRAC50GOLFE.SHP", False), (A, G2 + "FRACDALHA.SHP", False)], "source_file"),
    ("jica_altimetrie", "Altimétrie (lignes)", "Altimetry (lines)", "5 469 lignes d'altimétrie (courbes de niveau probables : à confirmer).", [(R, T + "ALTIMETRIE.SHP", False)], "source_file"),
    ("jica_points_cotes", "Points cotés", "Spot heights", "493 points cotés.", [(R, T + "POINTCOTES.SHP", False)], "source_file"),
    ("jica_hydrographie", "Réseau hydrographique (oueds)", "Hydrographic network (wadis)", "Hydro, oueds principaux et majeurs (3 fichiers sources).",
     [(A, G2 + "HYDRO.SHP", False), (A, G2 + "OUEDPRINCIPAUX.SHP", False), (A, G2 + "OUEDMAJEUR.SHP", False)], "source_file"),
    ("jica_plans_eau", "Lacs, sebkhas, nappes saumâtres", "Lakes, salt flats, brackish aquifers", "Lacs, sebkhas et nappes saumâtres (3 fichiers sources).",
     [(R, T + "LAKE.SHP", False), (A, G2 + "SEBKHA.SHP", False), (A, G2 + "NAPPSAUMATRE.SHP", False)], "source_file"),
    ("jica_reseau_routier", "Routes, pistes et chemin de fer", "Roads, tracks and railway", "Routes, pistes (1 et 2) et chemin de fer.",
     [(R, T + "ROUTES1.SHP", False), (R, T + "ROUTES2.SHP", False), (R, T + "PISTES1.SHP", False), (R, T + "PISTES2.SHP", False), (A, G2 + "CHEMINFER.SHP", False)], "source_file"),
    ("jica_localites", "Villages, villes et localités", "Villages, towns and localities", "Villages, villes, chefs-lieux, postes administratifs et localités.",
     [(R, T + "VILLAGE.SHP", False), (A, G2 + "VILLE.SHP", False), (A, G2 + "CHEFLIEUNOUVEAU.SHP", False), (A, G2 + "POSTADMINST.SHP", False), (A, G2 + "localite/localite.shp", False)], "NAME1_"),
    ("jica_vegetation_regions", "Végétation par région", "Vegetation by region", "Cartes de végétation régionales (projection absente : UTM 38N supposée, voir avertissement).",
     [(R, V + f, True) for f in ("ALISABIEH_VEG.shp", "ARTA_VEG.shp", "DIKHIL.shp", "DJIBOUTI_VEG.shp", "OBOCK_VEG.shp", "TADJOURAH_VEG.shp")], "source_file"),
    ("jica_agropastoral", "Unités agropastorales", "Agropastoral units", "Unités agropastorales ; code de classe = nom du fichier (légende JICA attendue). 6 fichiers illisibles ignorés.",
     [(A, AG + f, False) for f in ("@.shp", "C1.shp", "C2.shp", "C3.shp", "C4.shp", "C5.shp", "Eau libre.shp", "H3+P3.shp", "L1.shp", "Oueds.shp", "P3 Steppe arborée.shp", "P3.shp",
                                    "P4 formation anthropique.shp", "l9 mongrove .shp", "inconnu 3.shp", "inconnu2.shp") + tuple(f"Inconnu {i}.shp" for i in (1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13))], "source_file"),
    ("jica_agropastoral_composite", "Agropastoral — points composites", "Agropastoral — composite points", "513 points « composite ».", [(A, AG + "composite.shp", False)], "nom"),
    ("jica_forets", "Forêts", "Forests", "9 polygones de forêts.", [(A, G2 + "FORETS.SHP", False)], "source_file"),
    ("jica_sols_regions", "Sols — Arta et Ali Sabieh (fichier national corrompu)", "Soils — Arta and Ali Sabieh (national file corrupt)", "Unités de sols d'Arta (descriptions) et d'Ali Sabieh (sans attributs, projection supposée UTM 38N).",
     [(R, S + "Nm_sols_ARTA.shp", False), (R, S + "Nm_sols_Ali-sabieh.shp", True)], "Descriptio"),
    ("jica_pluie_mai", "Pluie moyenne — mai", "Mean rainfall — May", "9 polygones de pluie moyenne (champ Pluiemoyen) ; période exacte à confirmer.", [(A, G2 + "pluiemoy_mai.shp", False)], "Pluiemoyen"),
    ("jica_zones_hydrogeo", "Zones prioritaires, résistivité, recharge", "Priority, resistivity and recharge zones", "Zones prioritaires, résistivité < 20, zones sans géophysique, recharge (sens exact à confirmer).",
     [(A, G2 + f, False) for f in ("ZONPRIORITE1.SHP", "ZONPRIORITE2_OA.SHP", "ZONPRIORITé2_RT.SHP", "ZON_SANS_GEOPHYS.SHP", "RESISTIVITE_INF_20.SHP", "zon_rech_oueah.shp", "zonwea.shp")], "source_file"),
    ("jica_formation_points_eau", "Formations de points d'eau", "Water-point formations", "76 points (champ typepoint).", [(A, G2 + "formationpoint_eau.shp", False)], "typepoint"),
    ("jica_alerte_crue", "Stations d'alerte de crue", "Flood-alert stations", "Stations de base, pluviomètres possibles, répéteur, débit/pluie.",
     [(A, PC + f"alerte-crue/{f}.shp", False) for f in ("BaseStation", "PossibleRainfallGage", "PossibleRepeaterStation", "StreamFlowRainfallGage")], "source_file"),
    ("jica_sismicite", "Sismicité (épicentres)", "Seismicity (epicentres)", "2 462 événements (champs NOM, MAGCOR) ; projection supposée UTM 38N.", [(A, G2 + "XYsismo_mar_25.shp", True)], "NOM"),
    ("jica_bathymetrie", "Bathymétrie", "Bathymetry", "Isobathes (champ bathy).", [(A, PC + "bathymetrie/bathy-apres-200000IGN.shp", False)], "bathy"),
    ("jica_iles", "Îles", "Islands", "Îles (3 jeux sources).", [(A, "iles/ILESILES200.SHP", False), (A, "iles/Ile de Doumera.shp", False), (A, "iles/iles 7 freres.shp", False)], "source_file"),
    ("jica_cote_frontieres", "Côte et frontières", "Coast and borders", "Trait de côte et frontières.", [(A, G2 + "COTE.SHP", False), (A, G2 + "FRONTIERE.SHP", False)], "source_file"),
]


def find(root: Path, rel: str) -> Path | None:
    p = root
    for part in rel.split("/"):
        hit = next((c for c in p.iterdir() if c.name.lower() == part.lower()), None) if p.is_dir() else None
        if hit is None:
            return None
        p = hit
    return p


def read(path: Path, assume: bool) -> gpd.GeoDataFrame:
    with tempfile.TemporaryDirectory() as tmp:
        for side in path.parent.iterdir():
            if side.is_file() and side.stem.lower() == path.stem.lower():
                shutil.copy2(side, Path(tmp) / side.name)
        gdf = None
        for enc in ("cp1252", "latin-1"):
            try:
                gdf = gpd.read_file(Path(tmp) / path.name, encoding=enc); break
            except UnicodeDecodeError:
                continue
    if gdf is None:
        raise ValueError("encodage illisible")
    if len(gdf) == 0:
        raise ValueError("couche vide")
    epsg = gdf.crs.to_epsg() if gdf.crs else None
    if gdf.crs is None:
        if not assume:
            raise ValueError("projection absente (non déclarée supposée)")
        x0, y0, x1, y1 = gdf.total_bounds
        if not (UTM38_X[0] < x0 and x1 < UTM38_X[1] and UTM38_Y[0] < y0 and y1 < UTM38_Y[1]):
            raise ValueError("projection absente et emprise hors UTM 38N")
        gdf = gdf.set_crs(32638)
    elif epsg not in (32638, 4326):
        raise ValueError(f"CRS inattendu {gdf.crs}")
    return gdf


def prepare(gdf: gpd.GeoDataFrame, stem: str, tol: float) -> gpd.GeoDataFrame:
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    b = gdf.geometry.bounds
    finite = b.apply(lambda col: col.map(lambda v: v == v and abs(v) != float("inf"))).all(axis=1)
    if (~finite).any():
        print(f"  ! {stem}: {int((~finite).sum())} géométrie(s) à coordonnées non finies écartée(s)")
        gdf = gdf[finite].copy()
    if gdf.crs.to_epsg() == 32638 and tol and not gdf.geom_type.isin(["Point", "MultiPoint"]).all():
        gdf["geometry"] = gdf.geometry.simplify(tol, preserve_topology=True)
        if gdf.geom_type.isin(["Polygon", "MultiPolygon"]).any():
            gdf["geometry"] = gdf.geometry.buffer(0)
        gdf = gdf[~gdf.geometry.is_empty]
    gdf = gdf.to_crs(4326)
    b = gdf.geometry.bounds
    ok = b.apply(lambda col: col.map(lambda v: v == v and abs(v) != float("inf"))).all(axis=1) & (b.minx > 30) & (b.maxx < 55) & (b.miny > 0) & (b.maxy < 25)
    if (~ok).any():
        print(f"  ! {stem}: {int((~ok).sum())} entité(s) hors zone/non finie(s) après reprojection écartée(s)")
        gdf = gdf[ok].copy()
    keep = ["geometry"] + [c for c in gdf.columns if c not in DROP]
    out = gdf[keep].copy()
    for c in out.columns:
        if c != "geometry" and out[c].dtype == "O":
            out[c] = out[c].map(lambda v: v.strip() if isinstance(v, str) and v.strip() else None)
    out["source_file"] = stem
    return out


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("rdd"); ap.add_argument("arc"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(); roots = {R: Path(a.rdd), A: Path(a.arc)}
    entries, skipped = [], []
    for lid, nfr, nen, dfr, items, namecol in GROUPS:
        parts, assumed = [], []
        for root, rel, assume in items:
            p = find(roots[root], rel)
            if p is None:
                skipped.append((lid, rel, "introuvable")); continue
            try:
                g = read(p, assume)
            except Exception as e:  # noqa: BLE001
                skipped.append((lid, rel, str(e)[:60])); continue
            parts.append(prepare(g, p.stem, 10.0 if g.geom_type.str.contains("Line").any() else 5.0))
            if assume:
                assumed.append(p.name)
        if not parts:
            skipped.append((lid, "*", "aucune source lisible")); continue
        allg = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=4326)
        fc = json.loads(allg.to_json(drop_id=True))
        for f in fc["features"]:
            f["properties"] = {k: (None if isinstance(v, float) and v != v else v) for k, v in f["properties"].items()}
        n = len(fc["features"]); gt = allg.geom_type.mode()[0].replace("Multi", "")
        if not a.dry_run:
            OUT.mkdir(parents=True, exist_ok=True)
            with gzip.open(OUT / f"{lid}.geojson.gz", "wt", encoding="utf-8", compresslevel=9) as fh:
                fh.write(json.dumps(fc, ensure_ascii=False, separators=(",", ":")))
        warns = [{"fr": "Licence JICA non confirmée : usage interne, ne pas diffuser avant accord écrit. Données ~2007-2008.", "en": "JICA licence not confirmed: internal use only, do not distribute before written agreement. Data ~2007-2008."},
                 {"fr": "Nom et classes provisoires : en attente des légendes de la JICA.", "en": "Provisional name and classes: JICA legends pending."}]
        if assumed:
            warns.append({"fr": f"Projection absente dans {', '.join(assumed)} : UTM 38N supposée (emprise cohérente) — à confirmer.", "en": f"Missing projection in {', '.join(assumed)}: UTM 38N assumed (bounds consistent) — to be confirmed."})
        entries.append({"id": lid, "name_fr": nfr, "name_en": nen, "description_fr": dfr, "description_en": dfr, "format": "geojson", "geometry_type": gt,
                        "source": SOURCE, "license": LICENSE, "license_url": "", "date_acquired": date.today().isoformat(), "coverage": "Djibouti — national",
                        "feature_count": n, "status": "draft", "enabled": True, "api_endpoint": f"/api/v1/geo/dj/{lid}", "file_path": f"data/geo/jica/{lid}.geojson.gz",
                        "name_column": namecol, "warnings": warns})
        size = 0 if a.dry_run else (OUT / f"{lid}.geojson.gz").stat().st_size // 1024
        print(f"{lid:30} {n:6} {gt:11} {size:5} Ko  ({len(parts)}/{len(items)} fichiers)")
    for s in skipped:
        print("IGNORÉ", *s)
    if a.dry_run:
        return
    cat = yaml.safe_load(CATALOG.read_text(encoding="utf-8")); ids = {e["id"] for e in entries}
    cat["layers"] = [l for l in cat["layers"] if l["id"] not in ids] + entries
    CATALOG.write_text(yaml.safe_dump(cat, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    print(f"{len(entries)} couches enregistrées")


if __name__ == "__main__":
    main()
