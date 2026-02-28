"""ADSB message type used when loading parquet data."""

from datetime import datetime


class AdsbMessage:
    """
    A single ADSB message from parquet (beast format).

    Attributes:
        t_stamp: Message timestamp as datetime.
        adsbMsg: Hex payload string (after beast header).
        r_ID: Receiver id.
        extractedParquetFile: Source parquet filename.
        full_raw_bytes: Full beast message as hex string (used for position decode).
    """

    def __init__(
        self,
        t_stamp: int | float | datetime,
        adsbMSG: str,
        r_id: str,
        extractedParquetFile: str,
        full_raw_bytes: str,
    ):
        if isinstance(t_stamp, datetime):
            self.t_stamp = t_stamp
        elif hasattr(t_stamp, "to_pydatetime"):
            self.t_stamp = t_stamp.to_pydatetime()  # pandas Timestamp
        elif isinstance(t_stamp, (int, float)):
            self.t_stamp = datetime.fromtimestamp(float(t_stamp) / 1000.0)
        else:
            self.t_stamp = t_stamp
        self.adsbMsg = adsbMSG
        self.r_ID = r_id
        self.extractedParquetFile = extractedParquetFile
        self.full_raw_bytes = full_raw_bytes
