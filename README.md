# adsb_parser

Parse ADSB data stored as Beast-format messages in Parquet files, decode positions (lat/lon) from CPR even/odd pairs, and plot them on a map.

## What it does

- **Loads** ADSB messages from `.parquet` files (Beast-style raw messages with timestamps and receiver id).
- **Decodes** positions using pyModeS: pairs even/odd CPR position messages (type codes 9–18 or 20–22) to get latitude and longitude.
- **Filters** positions to those within 30 miles of a configured center (default 36.2667°N, 95.7841°W).
- **Plots** all positions on a single map, either:
  - **On screen** (matplotlib, with optional OpenStreetMap tiles that refresh when you zoom), or
  - **To file**: interactive HTML (Folium) or static image (matplotlib PNG, etc.).

## Setup

### Option 1: Micromamba (recommended)

From the repo root:

```bash
# Create and activate the environment
micromamba create -f environment.yml -n adsbparser
micromamba activate adsbparser
```

### Option 2: Conda

```bash
conda env create -f environment.yml
conda activate adsbparser
```

### Option 3: Pip

Install dependencies manually (Python 3.9+): `pandas`, `pyarrow`, `pyModeS`, `folium`, `matplotlib`, `contextily`, and optionally `geopy`, `numpy`, `fastparquet`.

## Data

Place your ADSB Parquet files in a directory (e.g. `data/`). Each file should contain columns:

- `beastMSG` – raw Beast-format message bytes
- `isoTimestamp` – message time (ms since epoch or datetime)
- `r_id` – receiver identifier

The script reads all `*.parquet` files in the given directory and merges messages by ICAO before decoding positions.

## Running the plot script

Run from the **repository root** so the `adsbparser` package is importable. If the environment is not activated, use `micromamba run -n adsbparser` (or `conda run -n adsbparser`).

### Display on screen (default)

Opens a matplotlib window with positions; if you don’t pass `--no-map`, OpenStreetMap tiles are shown and update when you zoom:

```bash
# From repo root, with env activated
python run_scripts/plot_adsb_tracks.py

# Or with micromamba without activating
micromamba run -n adsbparser python run_scripts/plot_adsb_tracks.py
```

Use a custom data directory:

```bash
python run_scripts/plot_adsb_tracks.py --data-dir /path/to/parquet/files
```

### Save to file

- **Interactive HTML map (Folium):**
  ```bash
  python run_scripts/plot_adsb_tracks.py --data-dir data --out map.html
  ```

- **Static image (matplotlib):**
  ```bash
  python run_scripts/plot_adsb_tracks.py --data-dir data --mpl --out tracks.png
  ```

### Options

| Option        | Description |
|---------------|-------------|
| `--data-dir`  | Directory containing `*.parquet` files (default: `data`). |
| `--out`       | Output file path. If omitted, the plot is shown on screen. |
| `--mpl`       | Use matplotlib for the output (e.g. `.png`). Without this, `.html` is written with Folium. |
| `--no-map`    | On-screen only: disable map tiles (plain lat/lon axes). |

Map center and radius are set in `adsbparser/config.py` (`DataVisualizer.centerMap`, `mapRadiusMiles`, `mapZoom`).
