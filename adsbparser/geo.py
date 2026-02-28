"""Geographic position and distance utilities (flat-Earth approximation)."""

import math


class PositionData:
    """Lat/lon position in degrees."""

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon

    def get_distance_to(self, other: "PositionData") -> float:
        """Return distance in miles to another position (flat-Earth)."""
        return calculate_distance_between_points(self, other)


# Flat-Earth constants: ~60 nm per degree lat, 1 nm = 6076.115 ft
FEET_PER_DEGREE_LAT = 60.0 * 6076.115
FEET_PER_MILE = 5280.0


def calculate_distance_between_points(p1: PositionData, p2: PositionData) -> float:
    """
    Distance between two positions in miles (flat-Earth approximation).

    Args:
        p1: First point (lat, lon in degrees).
        p2: Second point (lat, lon in degrees).

    Returns:
        Distance in miles.
    """
    if not (isinstance(p1, PositionData) and isinstance(p2, PositionData)):
        return 9999999.0
    lat1_rad = math.radians(p1.lat)
    delta_lat_deg = p2.lat - p1.lat
    delta_lon_deg = p2.lon - p1.lon
    delta_y_feet = delta_lat_deg * FEET_PER_DEGREE_LAT
    delta_x_feet = delta_lon_deg * FEET_PER_DEGREE_LAT * math.cos(lat1_rad)
    distance_feet = math.sqrt(delta_x_feet**2 + delta_y_feet**2)
    return distance_feet / FEET_PER_MILE
