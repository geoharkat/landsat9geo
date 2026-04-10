"""
Command-line interface for landsat9geo.
"""

import argparse
import sys
from pathlib import Path

from .processor import LandsatGeologyPipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="landsat9geo",
        description="Prepare Landsat 9 L2SP data for geological mapping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples
--------
  # From a .tar archive with AOI clip
  landsat9geo --tar LC09_L2SP_193036_20230713.tar --shp aoi.shp

  # From an extracted directory, with PAN and DEM
  landsat9geo --dir ./LC09_extracted --pan B8.TIF --dem srtm.tif -o results/
""",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--tar", type=str, help="Path to L2SP .tar archive")
    src.add_argument("--dir", type=str, help="Path to extracted L2SP directory")
    parser.add_argument("--shp", type=str, default=None, help="Shapefile / GeoPackage for AOI clip")
    parser.add_argument("--pan", type=str, default=None, help="Panchromatic band (15 m) for Brovey pansharpening")
    parser.add_argument("--dem", type=str, default=None, help="DEM for slope/aspect/hillshade")
    parser.add_argument("-o", "--output", type=str, default="geology_output", help="Output directory")

    args = parser.parse_args()

    pipeline = LandsatGeologyPipeline(
        tar_path=args.tar,
        directory=args.dir,
        shp_path=args.shp,
        pan_path=args.pan,
        dem_path=args.dem,
        output_dir=args.output,
    )

    outputs = pipeline.run()

    print("\n" + "=" * 60)
    print("  OUTPUT FILES")
    print("=" * 60)
    for key, path in outputs.items():
        print(f"  {key:20s}  {path}")
    print()


if __name__ == "__main__":
    main()
