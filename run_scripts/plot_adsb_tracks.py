"""
Plot all decoded ADSB lat/lon from parquet files in a data directory on a single map.

Usage:
  # Display on screen (matplotlib)
  python run_scripts/plot_adsb_tracks.py --data-dir data

  # Save to HTML (folium) or image (matplotlib)
  python run_scripts/plot_adsb_tracks.py --data-dir data --out map.html
  python run_scripts/plot_adsb_tracks.py --data-dir data --out tracks.png
"""

import argparse
import sys
from pathlib import Path

# Ensure package is importable when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adsbparser.config import DataVisualizer
from adsbparser.parquet_parser import (
    load_adsb_messages_by_icao,
    decode_positions_from_messages,
)
from adsbparser.plot_tracks import (
    filter_positions_near,
    plot_folium_map,
    plot_matplotlib_map,
)


def main():
    ap = argparse.ArgumentParser(description="Parse all parquet in a directory and plot all lat/lons on one map")
    ap.add_argument("--data-dir", type=Path, default=Path("data"), help="Directory containing *.parquet files")
    ap.add_argument("--out", type=str, default=None, help="Save to file (if omitted, display on screen)")
    ap.add_argument("--mpl", action="store_true", help="Use matplotlib when saving (default: folium for .html)")
    ap.add_argument("--no-map", action="store_true", help="On-screen plot only: disable map tiles (plain axes)")
    args = ap.parse_args()

    data_dir = args.data_dir.resolve()
    if not data_dir.is_dir():
        print(f"Data directory not found: {data_dir}")
        sys.exit(1)

    plane_data = {}
    for f in sorted(data_dir.glob("*.parquet")):
        load_adsb_messages_by_icao(f, plane_data)

    total_msgs = sum(len(msgs) for msgs in plane_data.values())
    print(f"Parsed {len(plane_data)} ICAO(s), {total_msgs} messages from {len(list(data_dir.glob('*.parquet')))} file(s)")

    positions = decode_positions_from_messages(plane_data)
    print(f"Decoded {len(positions)} positions")

    center = DataVisualizer.centerMap  # [lat, lon]
    radius_miles = DataVisualizer.mapRadiusMiles
    positions = filter_positions_near(positions, center[0], center[1], radius_miles)
    print(f"Within {radius_miles} mi of ({center[0]}, {center[1]}): {len(positions)} positions")

    if not positions:
        print("No positions to plot within radius (or no CPR even/odd pairs in the data)")
        sys.exit(0)

    if args.out:
        if args.mpl or not args.out.lower().endswith(".html"):
            plot_matplotlib_map(
                positions,
                output_path=args.out,
                title="ADSB positions (all parquet)",
                as_points=True,
                show=False,
                map_center=tuple(center),
                map_radius_miles=radius_miles,
            )
        else:
            plot_folium_map(
                positions,
                output_path=args.out,
                center=center,
                zoom_start=DataVisualizer.mapZoom,
                as_points=True,
            )
        print(f"Plot saved to {args.out}")
    else:
        plot_matplotlib_map(
            positions,
            output_path=None,
            title="ADSB positions (all parquet)",
            as_points=True,
            show=True,
            add_basemap=not args.no_map,
            map_center=tuple(center),
            map_radius_miles=radius_miles,
        )


if __name__ == "__main__":
    main()
