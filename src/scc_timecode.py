# -*- coding: utf-8 -*-
"""
SCC Timecode Module

Timecode parsing, arithmetic, and validation for SCC files.
Handles frame rate detection and cadence calculations for 23.98, 25, and 29.97 DF/NDF.
"""

from collections import namedtuple
from scc_decoder import TIMESTAMP_PATTERN

Timestamp = namedtuple("Timestamp", ["hours", "minutes", "seconds", "frames"])


def parse_timestamp_str(ts_str):
    """Parse timestamp string into Timestamp namedtuple."""
    parts = ts_str.replace(";", ":").split(":")
    return Timestamp(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))


def add_frames(hh, mm, ss, ff, packet_offset, frame_rate_str):
    """Add packet offset to timestamp, accounting for frame rate cadence."""
    if frame_rate_str not in ("23.98", "25", "29.97 DF", "29.97 NDF"):
        raise ValueError("Invalid frame rate: {0}".format(frame_rate_str))
    video_fps = 24 if frame_rate_str == "23.98" else 25 if frame_rate_str == "25" else 30
    is_df = frame_rate_str == "29.97 DF"

    if frame_rate_str == "23.98":
        # 5 packets -> 4 frames: packets 0,1,2,3,4 -> frames 0,1,2,3,3
        frame_offset = (packet_offset // 5) * 4 + min(packet_offset % 5, 3)
    elif frame_rate_str == "25":
        # 6 packets -> 5 frames: packets 0,1,2,3,4,5 -> frames 0,1,2,3,4,4
        frame_offset = (packet_offset // 6) * 5 + min(packet_offset % 6, 4)
    else:
        frame_offset = packet_offset

    ff += frame_offset
    while ff >= video_fps:
        ff -= video_fps
        ss += 1

    while ss >= 60:
        ss -= 60
        mm += 1
        if is_df and mm % 10 != 0 and ff < 2:
            ff = 2

    while mm >= 60:
        mm -= 60
        hh += 1

    sep = ";" if is_df else ":"
    return "{0:02d}:{1:02d}:{2:02d}{3}{4:02d}".format(hh, mm, ss, sep, ff), frame_offset


def detect_frame_rate(file_text):
    """Detect frame rate from SCC file by analyzing timestamps."""
    max_frame = 0
    has_drop_frame = False
    count = 0

    for match in TIMESTAMP_PATTERN.finditer(file_text):
        if count >= 50:
            break
        count += 1
        ts = match.group(0)
        if ";" in ts:
            has_drop_frame = True
        frame = int(ts[-2:])
        if frame > 29:
            return "INVALID", count
        if frame > max_frame:
            max_frame = frame

    if has_drop_frame:
        rate = "29.97 DF"
    elif max_frame <= 23:
        rate = "23.98"
    elif max_frame == 24:
        rate = "25"
    else:
        rate = "29.97 NDF"

    return rate, count


def validate_timestamp(ts_str):
    """Validate timestamp string. Returns True if valid, False otherwise."""
    try:
        ts = parse_timestamp_str(ts_str)
        return ts.hours <= 23 and ts.minutes <= 59 and ts.seconds <= 59 and ts.frames <= 29
    except (ValueError, IndexError, AttributeError, TypeError):
        return False


def compare_timestamps(ts1_str, ts2_str):
    """Compare two timestamps. Returns -1 if ts1 < ts2, 0 if equal, 1 if ts1 > ts2."""
    try:
        ts1 = parse_timestamp_str(ts1_str)
        ts2 = parse_timestamp_str(ts2_str)

        if ts1.hours != ts2.hours:
            return -1 if ts1.hours < ts2.hours else 1
        if ts1.minutes != ts2.minutes:
            return -1 if ts1.minutes < ts2.minutes else 1
        if ts1.seconds != ts2.seconds:
            return -1 if ts1.seconds < ts2.seconds else 1
        if ts1.frames != ts2.frames:
            return -1 if ts1.frames < ts2.frames else 1
        return 0
    except (ValueError, IndexError, AttributeError, TypeError):
        return 0
