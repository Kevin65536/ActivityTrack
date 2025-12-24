"""Screen time bucketing helpers.

This module is intentionally free of any Win32 / UI dependencies so it can be
unit-tested easily.
"""

from __future__ import annotations

import datetime
from typing import Iterable, Iterator


def split_interval_by_local_hour(start_ts: float, end_ts: float) -> list[tuple[datetime.date, int, float]]:
    """Split a time interval into local-hour buckets.

    Args:
        start_ts: Start timestamp (seconds since epoch).
        end_ts: End timestamp (seconds since epoch). Must be >= start_ts.

    Returns:
        List of (date, hour, seconds) segments, where each segment lies wholly
        within a single local clock hour.

    Notes:
        - Uses local time via datetime.fromtimestamp().
        - Guards against pathological DST/clock issues that could cause non-
          increasing boundaries.
    """
    if end_ts <= start_ts:
        return []

    segments: list[tuple[datetime.date, int, float]] = []
    cursor = float(start_ts)
    end_ts = float(end_ts)

    while cursor < end_ts:
        dt = datetime.datetime.fromtimestamp(cursor)
        hour_start = dt.replace(minute=0, second=0, microsecond=0)
        next_hour = hour_start + datetime.timedelta(hours=1)
        next_boundary = next_hour.timestamp()

        # Safety: avoid infinite loops if boundary is not advancing (DST weirdness)
        if next_boundary <= cursor:
            next_boundary = cursor + 3600.0

        slice_end = min(end_ts, next_boundary)
        seconds = slice_end - cursor
        if seconds > 0:
            segments.append((dt.date(), dt.hour, seconds))

        cursor = slice_end

    return segments
