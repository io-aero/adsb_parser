"""
Plot ADSB lat/lon positions on Folium (HTML) or Matplotlib (with optional map tiles).
"""

import math
import time
from pathlib import Path
from typing import List, Sequence, Tuple

from adsbparser.config import DataVisualizer
from adsbparser.geo import PositionData, calculate_distance_between_points

try:
    import folium
    from folium import PolyLine
    _HAS_FOLIUM = True
except ImportError:
    _HAS_FOLIUM = False

try:
    import matplotlib.pyplot as plt
    _HAS_MATPLOTLIB = True
except ImportError:
    _HAS_MATPLOTLIB = False

try:
    import contextily as ctx
    _HAS_CONTEXTILY = True
except ImportError:
    _HAS_CONTEXTILY = False


def _lats_lons(positions: Sequence[Tuple[float, float]]) -> Tuple[List[float], List[float]]:
    """Split list of (lat, lon) into (lats, lons)."""
    lats = [float(p[0]) for p in positions]
    lons = [float(p[1]) for p in positions]
    return (lats, lons)


def filter_positions_near(
    positions: Sequence[Tuple[float, float]],
    center_lat: float,
    center_lon: float,
    radius_miles: float,
) -> List[Tuple[float, float]]:
    """
    Keep only positions within radius_miles of (center_lat, center_lon).

    Args:
        positions: List of (lat, lon).
        center_lat: Center latitude (degrees).
        center_lon: Center longitude (degrees).
        radius_miles: Max distance in miles.

    Returns:
        Filtered list of (lat, lon).
    """
    center = PositionData(center_lat, center_lon)
    out = []
    for lat, lon in positions:
        if calculate_distance_between_points(PositionData(lat, lon), center) <= radius_miles:
            out.append((lat, lon))
    return out


def _extent_for_radius_miles(
    center_lat: float, center_lon: float, radius_miles: float
) -> Tuple[float, float, float, float]:
    """Return (lon_min, lon_max, lat_min, lat_max) for a box of radius_miles around center."""
    feet_per_deg_lat = 60.0 * 6076.115
    miles_per_deg_lat = feet_per_deg_lat / 5280.0
    delta_lat = radius_miles / miles_per_deg_lat
    lat_rad = math.radians(center_lat)
    delta_lon = radius_miles / (miles_per_deg_lat * math.cos(lat_rad))
    return (
        center_lon - delta_lon,
        center_lon + delta_lon,
        center_lat - delta_lat,
        center_lat + delta_lat,
    )


def plot_folium_map(
    positions: Sequence[Tuple[float, float]],
    output_path: str | Path | None = None,
    center: Tuple[float, float] | None = None,
    zoom_start: int | None = None,
    line_color: str = "#1976d2",
    line_weight: int = 3,
    as_points: bool = False,
):
    """
    Plot positions on an interactive Folium map (HTML).

    Args:
        positions: List of (lat, lon).
        output_path: If set, save map to this path.
        center: [lat, lon] map center; default from config.
        zoom_start: Initial zoom; default from config.
        line_color: Polyline or marker color.
        line_weight: Polyline width (pixels).
        as_points: If True, draw circle markers; else one polyline.

    Returns:
        folium.Map instance.
    """
    if not _HAS_FOLIUM:
        raise RuntimeError("folium is required. Install with: conda install folium")
    center = center or DataVisualizer.centerMap
    zoom_start = zoom_start if zoom_start is not None else DataVisualizer.mapZoom
    output_path = Path(output_path) if output_path else None
    m = folium.Map(location=center, zoom_start=zoom_start)
    lats, lons = _lats_lons(positions)
    if not lats or not lons:
        return m
    if as_points:
        for lat, lon in zip(lats, lons):
            folium.CircleMarker(
                location=[lat, lon],
                radius=3,
                color=line_color,
                fill=True,
                fillOpacity=0.6,
            ).add_to(m)
    else:
        PolyLine(
            list(zip(lats, lons)),
            color=line_color,
            weight=line_weight,
            popup="Track",
        ).add_to(m)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(output_path))
    return m


def plot_matplotlib_map(
    positions: Sequence[Tuple[float, float]],
    output_path: str | Path | None = None,
    title: str = "ADSB tracks",
    show: bool = True,
    as_points: bool = False,
    add_basemap: bool = False,
    map_center: Tuple[float, float] | None = None,
    map_radius_miles: float | None = None,
):
    """
    Plot positions with Matplotlib (optional OpenStreetMap basemap via contextily).

    Args:
        positions: List of (lat, lon).
        output_path: If set, save figure to this path.
        title: Plot title.
        show: If True, call plt.show().
        as_points: If True, scatter plot; else line.
        add_basemap: If True, draw map tiles behind the plot.
        map_center: (lat, lon) for map extent; default from config.
        map_radius_miles: View radius in miles; default from config.

    Returns:
        matplotlib Figure.
    """
    if not _HAS_MATPLOTLIB:
        raise RuntimeError("matplotlib is required. Install with: conda install matplotlib")
    fig, ax = plt.subplots()
    lats, lons = _lats_lons(positions)
    if lats and lons:
        if as_points:
            ax.scatter(lons, lats, s=4, alpha=0.7, label="Positions", zorder=2)
        else:
            ax.plot(lons, lats, "-", label="Track", zorder=2)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title)
    ax.legend()
    ax.set_aspect("equal")

    if add_basemap and _HAS_CONTEXTILY:
        try:
            center = map_center or DataVisualizer.centerMap
            radius = map_radius_miles if map_radius_miles is not None else getattr(
                DataVisualizer, "mapRadiusMiles", 30
            )
            lon_min, lon_max, lat_min, lat_max = _extent_for_radius_miles(
                center[0], center[1], radius
            )
            ax.set_xlim(lon_min, lon_max)
            ax.set_ylim(lat_min, lat_max)
            ctx.add_basemap(ax, crs="EPSG:4326", zorder=0)

            _last_refresh = [0.0]

            def _refresh_basemap(_event=None):
                now = time.time()
                if now - _last_refresh[0] < 0.25:
                    return
                _last_refresh[0] = now
                try:
                    for im in list(ax.images):
                        im.remove()
                    ctx.add_basemap(ax, crs="EPSG:4326", zorder=0)
                    fig.canvas.draw_idle()
                except Exception:
                    pass

            ax.callbacks.connect("ylim_changed", _refresh_basemap)
        except Exception as e:
            if show:
                print(f"Note: basemap not shown ({e}). Install contextily for map tiles: conda install contextily")
    else:
        ax.grid(True)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig
