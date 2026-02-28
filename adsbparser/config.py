"""Configuration for ADSB parsing and map plotting."""


class ParquetColNames:
    """Column names used in ADSB parquet files."""
    BEAST_COL_NAME = "beastMSG"
    isoTstamp_COL_NAME = "isoTimestamp"
    receiverID_COL_NAME = "r_id"


class DataVisualizer:
    """Map display settings for plotting ADSB positions."""
    centerMap = [36.2667, -95.7841]   # Default center: 36.2667 N, 95.7841 W
    mapZoom = 9                        # Zoom level for ~30-mile view
    mapRadiusMiles = 30                 # Filter and view radius (miles)
