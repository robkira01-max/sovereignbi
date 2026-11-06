"""
Download a Djibouti PMTiles basemap (offline use).

Usage:
    python tools/download_pmtiles.py [--dry-run]

The downloaded file is saved to data/tiles/djibouti.pmtiles and served
by FastAPI at /tiles/djibouti.pmtiles — which MapLibreMap.tsx uses as
the basemap for offline choropleth dashboards.

Sources tried in order:
1. Protomaps CDN daily builds — planet-level PMTiles extracted to bbox.
2. Local extract from a full planet file (if PMTILES_PLANET_PATH is set).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

# Djibouti bounding box (lon_min, lat_min, lon_max, lat_max)
BBOX = (41.7, 10.9, 43.6, 12.8)

# Protomaps daily build — planet-level pmtiles (HTTP range requests supported)
# We extract only the Djibouti bbox to keep the file small (~10-30 MB).
PLANET_URL = "https://build.protomaps.com/planet.pmtiles"

OUTPUT_DIR  = Path(__file__).parent.parent / "data" / "tiles"
OUTPUT_FILE = OUTPUT_DIR / "djibouti.pmtiles"


def _check_pmtiles_cli() -> bool:
    """Return True if the `pmtiles` CLI is available."""
    result = subprocess.run(["pmtiles", "--version"], capture_output=True)
    return result.returncode == 0


def _install_pmtiles_cli() -> None:
    """Install pmtiles via go or npm (best-effort)."""
    # Try npm first (already in PATH for this project)
    result = subprocess.run(
        ["npm", "install", "-g", "pmtiles"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ pmtiles CLI installed via npm")
        return
    # Fallback: go install (if go is available)
    result = subprocess.run(
        ["go", "install", "github.com/protomaps/go-pmtiles/cmd/pmtiles@latest"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ pmtiles CLI installed via go")
        return
    print("⚠️  Could not install pmtiles CLI automatically.")
    print("   Install manually: npm install -g pmtiles")
    print("   Then re-run this script.")
    sys.exit(1)


def download_bbox(dry_run: bool = False) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check if planet env override is set
    planet_path = os.environ.get("PMTILES_PLANET_PATH")
    source = planet_path if planet_path else PLANET_URL

    lon_min, lat_min, lon_max, lat_max = BBOX
    bbox_str = f"{lon_min},{lat_min},{lon_max},{lat_max}"

    print(f"Source  : {source}")
    print(f"BBox    : {bbox_str}")
    print(f"Output  : {OUTPUT_FILE}")

    if dry_run:
        print("Dry-run — aucun téléchargement effectué.")
        return

    if not _check_pmtiles_cli():
        print("pmtiles CLI manquant — installation...")
        _install_pmtiles_cli()

    if not _check_pmtiles_cli():
        print("❌ pmtiles CLI toujours manquant après tentative d'installation.")
        sys.exit(1)

    cmd = [
        "pmtiles", "extract",
        source,
        str(OUTPUT_FILE),
        "--bbox", bbox_str,
        "--maxzoom", "14",
    ]
    print(f"Commande: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("❌ Échec du téléchargement.")
        sys.exit(1)

    size_mb = OUTPUT_FILE.stat().st_size / 1_048_576
    print(f"✅ PMTiles téléchargé : {OUTPUT_FILE} ({size_mb:.1f} MB)")
    print("   Lancez `make run` puis naviguez vers un dashboard de type 'map'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Afficher les paramètres sans télécharger")
    args = parser.parse_args()
    download_bbox(dry_run=args.dry_run)
