"""
Load ADSB messages from parquet files and decode positions (CPR even/odd).
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyModeS as pms

from adsbparser.config import ParquetColNames
from adsbparser.message import AdsbMessage


def beast_raw_to_hex(raw: bytes | str) -> str:
    """Convert beast raw bytes (or latin-1 string) to full hex string."""
    if isinstance(raw, bytes):
        return "".join(f"{b:02x}" for b in raw)
    if isinstance(raw, str):
        try:
            raw = raw.encode("latin-1", errors="replace")
        except Exception as e:
            print(f"Error encoding string to bytes: {e}")
            raw = b""
        return "".join(f"{b:02x}" for b in raw)
    print("Error: raw is neither bytes nor str.")
    return ""


def beast_payload_hex(raw: bytes | str) -> str:
    """Extract payload hex from beast message (after first 8 bytes)."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")[16:]
    elif isinstance(raw, str):
        try:
            raw = raw.encode("latin-1", errors="replace")
        except Exception as e:
            print(f"Error encoding string to bytes: {e}")
            raw = b""
        raw = raw[8:] if len(raw) >= 8 else b""
        raw = "".join(f"{b:02x}" for b in raw)
    else:
        raw = ""
    return raw if isinstance(raw, str) else ""


def is_valid_parquet_file(file_path: Path) -> bool:
    """Return False if file is not .parquet or too small."""
    if file_path.suffix != ".parquet":
        print("Error! Not a valid Parquet File!")
        return False
    if file_path.stat().st_size < 16:
        print(f"Skipping invalid file: {file_path}")
        return False
    return True


def read_parquet_table(file_path: Path) -> pa.Table | None:
    """Read a parquet file into a PyArrow table. Returns None on error."""
    try:
        return pq.read_table(file_path.as_posix())
    except Exception as e:
        print(f"Error reading {file_path.as_posix()}: {e}")
        return None


def decode_beast_column(column: pa.ChunkedArray) -> List[str]:
    """Decode beast column to list of strings (handles Unicode errors)."""
    out = []
    for val in column:
        try:
            out.append(val.as_py())
        except UnicodeDecodeError:
            raw = val.as_buffer().to_pybytes()
            out.append(raw.decode("latin-1", errors="replace"))
    return out


def parquet_table_to_dataframe(table: pa.Table) -> pd.DataFrame:
    """Build a DataFrame from a parquet table; beast column is decoded."""
    data = {}
    for name, column in zip(table.schema.names, table.columns):
        if name == ParquetColNames.BEAST_COL_NAME:
            data[name] = decode_beast_column(column)
        else:
            data[name] = column.to_pylist()
    return pd.DataFrame(data)


def sort_messages_by_timestamp(plane_data: Dict[str, List[AdsbMessage]]) -> None:
    """Sort each ICAO's message list by t_stamp in place."""
    for key in plane_data:
        plane_data[key] = sorted(plane_data[key], key=lambda m: m.t_stamp)


def _message_28_hex(msg: AdsbMessage) -> str:
    """Extract 28-hex (112-bit) ADS-B payload for pyModeS."""
    raw = getattr(msg, "full_raw_bytes", "") or ""
    if isinstance(raw, bytes):
        raw = raw.decode("latin-1", errors="replace")
    hex_str = raw if isinstance(raw, str) else ""
    return hex_str[-28:] if len(hex_str) >= 28 else ""


def decode_positions_from_messages(
    plane_data: Dict[str, List[AdsbMessage]],
) -> List[Tuple[float, float]]:
    """
    Decode (lat, lon) from all ICAO message lists using CPR even/odd pairs.

    Args:
        plane_data: ICAO -> list of AdsbMessage (from load_adsb_messages_by_icao).

    Returns:
        List of (lat, lon) for all decoded positions.
    """
    sort_messages_by_timestamp(plane_data)
    all_positions: List[Tuple[float, float]] = []

    for icao, packets in plane_data.items():
        if not packets:
            continue
        msg_even, msg_odd = None, None
        t_even, t_odd = None, None

        for m in packets:
            try:
                msg_28 = _message_28_hex(m)
                if len(msg_28) != 28:
                    continue
                tc = pms.adsb.typecode(msg_28)
                if tc < 9 or tc == 19 or tc > 22:
                    continue
                ts = m.t_stamp
                if hasattr(ts, "timestamp"):
                    ts = int(ts.timestamp())
                elif hasattr(ts, "value"):
                    ts = int(ts) // 1000 if int(ts) > 1e12 else int(ts)
                else:
                    ts = int(ts) // 1000 if int(ts) > 1e12 else int(ts)

                if pms.adsb.oe_flag(msg_28) == 0:
                    msg_even, t_even = msg_28, ts
                else:
                    msg_odd, t_odd = msg_28, ts

                if msg_even and msg_odd and t_even is not None and t_odd is not None:
                    try:
                        lat, lon = pms.adsb.position(msg_even, msg_odd, t_even, t_odd)
                        if lat is not None and lon is not None:
                            all_positions.append((float(lat), float(lon)))
                    except (RuntimeError, ValueError):
                        pass
                    msg_even = msg_odd = None
                    t_even = t_odd = None
            except (IndexError, TypeError, KeyError):
                continue

    return all_positions


def load_adsb_messages_by_icao(
    file_path: Path,
    plane_data: Dict[str, List[AdsbMessage]],
) -> bool:
    """
    Load one parquet file and merge ADSB messages into plane_data by ICAO.

    Args:
        file_path: Path to a .parquet file.
        plane_data: Dict to update: ICAO (lowercase) -> list of AdsbMessage.

    Returns:
        True if the file was loaded successfully, False otherwise.
    """
    if not is_valid_parquet_file(file_path):
        return False
    table = read_parquet_table(file_path)
    if table is None:
        return False
    df = parquet_table_to_dataframe(table)
    if df.empty:
        return False

    filename = os.path.basename(file_path)
    for beast_bytes, t_stamp, receiver_id in zip(
        df[ParquetColNames.BEAST_COL_NAME],
        df[ParquetColNames.isoTstamp_COL_NAME],
        df[ParquetColNames.receiverID_COL_NAME],
    ):
        payload_hex = beast_payload_hex(beast_bytes)
        full_hex = beast_raw_to_hex(beast_bytes)
        icao = pms.adsb.icao(full_hex[16:])
        if icao is None or icao == "000000":
            continue
        icao = icao.lower()
        msg = AdsbMessage(t_stamp, payload_hex, receiver_id, filename, full_hex)
        if icao not in plane_data:
            plane_data[icao] = []
        plane_data[icao].append(msg)
    return True
