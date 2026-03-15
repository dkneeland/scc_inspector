# -*- coding: utf-8 -*-
"""
SCC Timecode Module

Timecode parsing, arithmetic, and validation for SCC files.
Uses frame rate configuration from scc-core/data/frame_rates.json.
"""

from collections import namedtuple
from scc_decoder import TIMESTAMP_PATTERN
from scc_data import FRAME_RATES, DROP_FRAME_RULES, DETECTION_RULES, get_frame_rate_config

Timestamp = namedtuple("Timestamp", ["hours", "minutes", "seconds", "frames"])


def parse_timestamp_str(ts_str):
    """Parse timestamp string into Timestamp namedtuple."""
    parts = ts_str.replace(";", ":").split(":")
    return Timestamp(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))


def add_frames(hh, mm, ss, ff, packet_offset, frame_rate_str):
    """Add packet offset to timestamp, accounting for frame rate cadence.

    Uses frame rate configuration loaded from frame_rates.json.
    """
    config = get_frame_rate_config(frame_rate_str)
    video_fps = config['videoFps']
    is_df = config['isDropFrame']
    cadence = config.get('cadence')

    if cadence:
        packets_per_cycle = cadence['packets']
        frames_per_cycle = cadence['frames']
        frame_offset = (packet_offset // packets_per_cycle) * frames_per_cycle + min(packet_offset % packets_per_cycle, frames_per_cycle - 1)
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
    """Detect frame rate from SCC file by analyzing timestamps.

    Uses detection rules from frame_rates.json.
    """
    max_frame = 0
    has_drop_frame = False
    count = 0
    sample_limit = DETECTION_RULES['sampleLimit']
    drop_frame_sep = DETECTION_RULES['dropFrameSeparator']
    invalid_threshold = DETECTION_RULES['invalidFrameThreshold']

    for match in TIMESTAMP_PATTERN.finditer(file_text):
        if count >= sample_limit:
            break
        count += 1
        ts = match.group(0)
        if drop_frame_sep in ts:
            has_drop_frame = True
        frame = int(ts[-2:])
        if frame > invalid_threshold:
            return "INVALID", count
        if frame > max_frame:
            max_frame = frame

    if has_drop_frame:
        rate = "29.97 DF"
    else:
        if max_frame <= 23:
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


def packet_difference(ts1_str, ts2_str, frame_rate_str):
    """Calculate packet difference between two timestamps (ts1 - ts2) using add_frames logic."""
    try:
        if compare_timestamps(ts1_str, ts2_str) < 0:
            return 0

        ts2 = parse_timestamp_str(ts2_str)

        low, high = 0, 10000
        while low < high:
            mid = (low + high + 1) // 2
            result_ts, _ = add_frames(ts2.hours, ts2.minutes, ts2.seconds, ts2.frames, mid, frame_rate_str)
            if compare_timestamps(result_ts, ts1_str) >= 0:
                high = mid - 1
            else:
                low = mid

        return low + 1
    except (ValueError, IndexError, AttributeError, TypeError):
        return 0
