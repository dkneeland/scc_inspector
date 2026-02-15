# -*- coding: utf-8 -*-
"""Test CC buffer overflow detection"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scc_decoder import iter_hex_words
from scc_timecode import parse_timestamp_str, add_frames


def test_overflow_debug():
    """Debug packet timecodes for overflow detection"""
    line_text = "00:00:33:19\t9420 9452 4920 f468 e96e 6b20 f468 e520 e368 61f2 f420 7368 ef75 ec64 9470 97a1 67e9 76e5 2070 f2ef 7073 20f4 ef20 e576 e5f2 7964 6179 2068 e5f2 efe5 7380"
    next_ts = "00:00:34:05"
    frame_rate = "23.98"

    ts = parse_timestamp_str("00:00:33:19")

    print("Base timestamp: 00:00:33:19")
    print("Next timestamp: 00:00:34:05")
    print("Frame rate: {0}".format(frame_rate))
    print("\nPacket breakdown:")
    print("-" * 60)

    packet_idx = 0
    for word in iter_hex_words(line_text):
        if word.is_paired and word.start > word.pair_start:
            continue

        pkt_time, _ = add_frames(ts.hours, ts.minutes, ts.seconds, ts.frames, packet_idx, frame_rate)

        overflow = "OVERFLOW" if pkt_time >= next_ts else "OK"
        print("Packet {0:2d}: {1} -> {2} [{3}]".format(packet_idx + 1, word.text, pkt_time, overflow))
        packet_idx += 1

    print("-" * 60)


if __name__ == "__main__":
    test_overflow_debug()
