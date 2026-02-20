# -*- coding: utf-8 -*-
# ruff: noqa: F405
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from Npp import *  # noqa: F403
from scc_decoder import (
    iter_hex_words,
    parse_scc_code,
    decode_single_code,
    TIMESTAMP_PATTERN,
    is_eoc,
    is_rcl,
    is_enm,
    is_edm,
)
from scc_tooltip import format_tooltip
from scc_timecode import (
    parse_timestamp_str,
    add_frames,
    detect_frame_rate,
    validate_timestamp,
    compare_timestamps,
)
from scc_buffer_format import render_line_annotation

# Configuration
MAX_SCAN_DEPTH = 1000  # Max lines to scan backwards for buffer state (prevents UI freeze)


def decode_full_line(line_text):
    """Decode a full SCC line and return rendered caption segments (fast single-pass)."""
    return render_line_annotation(line_text)


def find_errors(line_text, line_num=None):
    """Find all errors in a line (invalid timestamps, parity errors, CC buffer overflow)."""
    errors = []

    ts_match = TIMESTAMP_PATTERN.search(line_text)
    if ts_match:
        if not validate_timestamp(ts_match.group(0)):
            errors.append((ts_match.start(), ts_match.end(), "invalid_timestamp"))
        
        # Check for CC buffer overflow only if we have frame rate
        if line_num is not None and detected_frame_rate:
            try:
                ts = parse_timestamp_str(ts_match.group(0))

                # Find next timestamp (SCC format: timestamp, blank, timestamp, blank...)
                next_ts_str = None
                next_line = line_num + 2
                if next_line < editor.getLineCount():
                    next_text = editor.getLine(next_line)
                    next_match = TIMESTAMP_PATTERN.search(next_text)
                    if next_match:
                        next_ts_str = next_match.group(0)

                if next_ts_str:
                    # Single pass: check parity, invalid hex, and overflow together
                    packet_idx = 0
                    overflow_found = False
                    for word in iter_hex_words(line_text):
                        if word.is_paired and word.start > word.pair_start:
                            continue

                        evt = parse_scc_code(word.text, word.is_paired)

                        # Check parity/invalid hex
                        if evt["type"] == "ERROR":
                            if evt["desc"] == "Parity Error":
                                errors.append((word.start, word.end, "parity_error"))
                            else:
                                errors.append((word.start, word.end, "invalid_hex"))
                            continue  # Skip overflow check for invalid packets

                        # Check overflow for valid packets only
                        pkt_time, _ = add_frames(
                            ts.hours,
                            ts.minutes,
                            ts.seconds,
                            ts.frames,
                            packet_idx,
                            detected_frame_rate,
                        )

                        if compare_timestamps(pkt_time, next_ts_str) >= 0:
                            errors.append((word.start, word.end, "cc_buffer_overflow"))
                            overflow_found = True

                        packet_idx += 1

                    # Also mark timestamp if any overflow
                    if overflow_found:
                        errors.append((ts_match.start(), ts_match.end(), "cc_buffer_overflow"))
                    return errors
            except (ValueError, TypeError):
                pass
    
    # Always check parity/invalid hex for all lines (with or without timestamp)
    for word in iter_hex_words(line_text):
        evt = parse_scc_code(word.text, word.is_paired)
        if evt["type"] == "ERROR":
            if evt["desc"] == "Parity Error":
                errors.append((word.start, word.end, "parity_error"))
            else:
                errors.append((word.start, word.end, "invalid_hex"))

    return errors


INDICATOR_ERROR = 0
INDICATOR_PAIR = 1
INDICATOR_PARITY = 2
STYLE_ANNOTATION = 20
STYLE_ANNOTATION_ITALIC = 21
STYLE_ANNOTATION_TIMING = 22
STYLE_ANNOTATION_NEWLINE = 23
STYLE_ANNOTATION_ERROR_SUMMARY = 25

detected_frame_rate = None


def setup_indicators():
    """Configure Notepad++ indicators and annotation styles."""
    editor.indicSetStyle(INDICATOR_ERROR, INDICATORSTYLE.SQUIGGLE)
    editor.indicSetFore(INDICATOR_ERROR, (255, 0, 0))
    editor.indicSetStyle(INDICATOR_PAIR, INDICATORSTYLE.ROUNDBOX)
    editor.indicSetFore(INDICATOR_PAIR, (100, 200, 100))
    editor.indicSetUnder(INDICATOR_PAIR, True)
    editor.indicSetStyle(INDICATOR_PARITY, INDICATORSTYLE.STRAIGHTBOX)
    editor.indicSetFore(INDICATOR_PARITY, (255, 0, 0))
    editor.indicSetUnder(INDICATOR_PARITY, False)

    editor.styleSetFore(STYLE_ANNOTATION, (220, 220, 220))
    editor.styleSetBack(STYLE_ANNOTATION, (30, 30, 30))

    editor.styleSetFore(STYLE_ANNOTATION_ITALIC, (220, 220, 220))
    editor.styleSetBack(STYLE_ANNOTATION_ITALIC, (30, 30, 30))
    editor.styleSetItalic(STYLE_ANNOTATION_ITALIC, True)

    editor.styleSetFore(STYLE_ANNOTATION_TIMING, editor.styleGetFore(33))
    editor.styleSetBack(STYLE_ANNOTATION_TIMING, editor.styleGetBack(0))

    editor.styleSetFore(STYLE_ANNOTATION_NEWLINE, (100, 100, 100))
    editor.styleSetBack(STYLE_ANNOTATION_NEWLINE, (30, 30, 30))

    editor.styleSetFore(STYLE_ANNOTATION_ERROR_SUMMARY, (255, 100, 100))
    editor.styleSetBack(STYLE_ANNOTATION_ERROR_SUMMARY, (60, 20, 20))
    editor.styleSetBold(STYLE_ANNOTATION_ERROR_SUMMARY, True)

    editor.annotationSetVisible(ANNOTATIONVISIBLE.STANDARD)


def highlight_single_line(line_num, line_text):
    """Apply error indicators and pair highlighting to a single line."""
    line_start_pos = editor.positionFromLine(line_num)
    length = len(line_text)

    for indicator in (INDICATOR_ERROR, INDICATOR_PAIR, INDICATOR_PARITY):
        editor.setIndicatorCurrent(indicator)
        editor.indicatorClearRange(line_start_pos, length)

    for start, end, error_type in find_errors(line_text, line_num):
        if error_type == "parity_error":
            editor.setIndicatorCurrent(INDICATOR_PARITY)
        else:
            editor.setIndicatorCurrent(INDICATOR_ERROR)
        editor.indicatorFillRange(line_start_pos + start, end - start)

    editor.setIndicatorCurrent(INDICATOR_PAIR)
    seen_pairs = set()
    for word in iter_hex_words(line_text):
        if word.is_paired and word.pair_start not in seen_pairs:
            editor.indicatorFillRange(line_start_pos + word.pair_start, word.pair_end - word.pair_start)
            seen_pairs.add(word.pair_start)


def build_time_map():
    """Single-pass state machine to map line numbers to start/end times.

    Returns: dict { line_num: (start_time, end_time) }
    """
    total_lines = editor.getLineCount()
    line_map = {}
    pending_lines = []
    active_lines = []

    for line_num in range(total_lines):
        line_text = editor.getLine(line_num)
        if not line_text.strip():
            continue

        ts_match = TIMESTAMP_PATTERN.search(line_text)
        if not ts_match:
            continue

        base_ts = ts_match.group(0)
        try:
            ts = parse_timestamp_str(base_ts)
        except (ValueError, TypeError):
            continue

        word_idx = 0
        has_added_pending = False

        for word in iter_hex_words(line_text):
            if word.is_paired and word.start > word.pair_start:
                continue

            evt = parse_scc_code(word.text, word.is_paired)
            if evt["type"] in ("TEXT", "PAC") and not has_added_pending:
                pending_lines.append(line_num)
                has_added_pending = True

            if is_eoc(word.text):
                start_time_str, _ = add_frames(
                    ts.hours,
                    ts.minutes,
                    ts.seconds,
                    ts.frames,
                    word_idx,
                    detected_frame_rate,
                )

                for a_line in active_lines:
                    if a_line in line_map:
                        line_map[a_line][1] = start_time_str

                for p_line in pending_lines:
                    if p_line not in line_map:
                        line_map[p_line] = [None, None]
                    line_map[p_line][0] = start_time_str

                active_lines = list(pending_lines)
                pending_lines = []
                has_added_pending = False

            elif is_edm(word.text):
                end_time_str, _ = add_frames(
                    ts.hours,
                    ts.minutes,
                    ts.seconds,
                    ts.frames,
                    word_idx,
                    detected_frame_rate,
                )

                for a_line in active_lines:
                    if a_line in line_map:
                        line_map[a_line][1] = end_time_str

                active_lines = []

            elif is_rcl(word.text) or is_enm(word.text):
                pending_lines = []
                has_added_pending = False

            word_idx += 1

    return line_map


def apply_annotation(line_num, segments, start_time=None, end_time=None):
    """Apply styled annotation to line showing decoded caption text."""
    if not segments:
        return

    final_segments = []
    if start_time and end_time:
        final_segments.append((" | {0} -> {1} | ".format(start_time, end_time), "timing"))

    for text, style_info in segments:
        if style_info == "newline":
            final_segments.append((text, "newline"))
        elif "\n" in text:
            parts = text.split("\n")
            for j, part in enumerate(parts):
                if j > 0:
                    final_segments.append(("\u23ce", "newline"))
                if part:
                    final_segments.append((part, style_info))
        else:
            final_segments.append((text, style_info))

    full_text_bytes = b""
    style_bytes = bytearray()

    for text, style_info in final_segments:
        chunk_bytes = text.encode("utf-8")
        full_text_bytes += chunk_bytes

        if style_info == "timing":
            style_id = STYLE_ANNOTATION_TIMING
        elif style_info == "error_summary":
            style_id = STYLE_ANNOTATION_ERROR_SUMMARY
        elif style_info == "newline":
            style_id = STYLE_ANNOTATION_NEWLINE
        elif style_info:
            style_id = STYLE_ANNOTATION_ITALIC
        else:
            style_id = STYLE_ANNOTATION

        for _ in range(len(chunk_bytes)):
            style_bytes.append(style_id)

    editor.annotationSetText(line_num, full_text_bytes)
    editor.annotationSetStyles(line_num, bytes(style_bytes))


def apply_all_indicators():
    """Apply indicators and annotations to all lines in the file."""
    setup_indicators()
    total_lines = editor.getLineCount()
    time_map = build_time_map()
    parity_count = 0
    overflow_count = 0
    error_timecodes = []

    for line_num in range(total_lines):
        text = editor.getLine(line_num)
        errors = find_errors(text, line_num)
        ts_match = TIMESTAMP_PATTERN.search(text)
        has_error = False
        for _, _, error_type in errors:
            if error_type == "parity_error":
                parity_count += 1
                has_error = True
            elif error_type == "cc_buffer_overflow":
                overflow_count += 1
                has_error = True
        if has_error and ts_match:
            error_timecodes.append(ts_match.group(0))
        highlight_single_line(line_num, text)
        if text.strip():
            segments = decode_full_line(text)
            if segments:
                times = time_map.get(line_num, (None, None))
                start_time, end_time = times[0], times[1]
                apply_annotation(line_num, segments, start_time, end_time)

    if parity_count or overflow_count:
        summary_parts = []
        if parity_count:
            summary_parts.append("{0} parity error{1}".format(parity_count, "s" if parity_count > 1 else ""))
        if overflow_count:
            summary_parts.append("{0} buffer overflow{1}".format(overflow_count, "s" if overflow_count > 1 else ""))
        summary = "ERRORS: " + ", ".join(summary_parts)
        if error_timecodes:
            summary += "\nErrors at: " + ", ".join(error_timecodes)
        summary_bytes = summary.encode("utf-8")
        style_bytes = bytearray([STYLE_ANNOTATION_ERROR_SUMMARY] * len(summary_bytes))
        editor.annotationSetText(0, summary_bytes)
        editor.annotationSetStyles(0, bytes(style_bytes))


def build_buffer_snapshot(line_text, target_word_idx, line_num=None):
    """Build caption buffer state at target word position.

    Returns: (buffer_text, highlight_start, highlight_end)
    """
    buf_text = ""
    row, col, color = None, None, None
    initial_state = None
    highlight_start = -1
    highlight_end = -1

    # Look backwards to build persistent buffer state
    if line_num is not None:
        lines_to_process = []
        search_limit = max(-1, line_num - MAX_SCAN_DEPTH)
        for search_line in range(line_num - 1, search_limit, -1):
            search_text = editor.getLine(search_line)
            found_enm = False

            for word in iter_hex_words(search_text):
                if word.is_paired and word.start > word.pair_start:
                    continue
                if is_enm(word.text):
                    found_enm = True
                    break

            lines_to_process.insert(0, search_text)
            if found_enm:
                break

        for line_text_prev in lines_to_process:
            for word in iter_hex_words(line_text_prev):
                if word.is_paired and word.start > word.pair_start:
                    continue

                evt = parse_scc_code(word.text, word.is_paired)
                if evt["type"] == "PAC":
                    if initial_state is None:
                        initial_state = (evt["row"], evt["col"], evt["color"][:3])
                    else:
                        buf_text += "{R%02d C%02d %s}" % (
                            evt["row"],
                            evt["col"],
                            evt["color"][:3],
                        )
                    row, col, color = evt["row"], evt["col"], evt["color"][:3]
                elif evt["type"] == "TEXT":
                    buf_text += evt["text"]
                elif evt["type"] == "MIDROW":
                    buf_text += "<i>"
                elif evt["type"] == "CONTROL":
                    if evt.get("is_backspace") and buf_text:
                        buf_text = buf_text[:-1]
                    elif is_enm(word.text) or is_rcl(word.text):
                        buf_text = ""
                        row, col, color = None, None, None
                        initial_state = None

    # Process current line
    for idx, word in enumerate(iter_hex_words(line_text)):
        if idx > target_word_idx:
            break
        if word.is_paired and word.start > word.pair_start:
            continue
        evt = parse_scc_code(word.text, word.is_paired)

        if evt["type"] == "PAC":
            if idx == target_word_idx:
                state_str = "{R%02d C%02d %s}" % (
                    evt["row"],
                    evt["col"],
                    evt["color"][:3],
                )
                if initial_state is None:
                    return state_str, 0, len(state_str)
                else:
                    row_i, col_i, color_i = initial_state
                    prefix = "{R%02d C%02d %s}" % (row_i, col_i, color_i)
                    return (
                        prefix + buf_text + state_str,
                        len(prefix) + len(buf_text),
                        len(prefix) + len(buf_text) + len(state_str),
                    )
            if initial_state is None:
                initial_state = (evt["row"], evt["col"], evt["color"][:3])
            else:
                buf_text += "{R%02d C%02d %s}" % (
                    evt["row"],
                    evt["col"],
                    evt["color"][:3],
                )
            row, col, color = evt["row"], evt["col"], evt["color"][:3]
        elif evt["type"] == "TEXT":
            if idx == target_word_idx:
                highlight_start = len(buf_text)
            buf_text += evt["text"]
            if idx == target_word_idx:
                highlight_end = len(buf_text)
        elif evt["type"] == "MIDROW":
            color = evt["color"][:3]
            if idx == target_word_idx:
                highlight_start = len(buf_text)
                buf_text += "<i>"
                highlight_end = len(buf_text)
            else:
                buf_text += "<i>"
        elif evt["type"] == "INDENT":
            spaces = " " * evt["spaces"]
            if idx == target_word_idx:
                highlight_start = len(buf_text)
            buf_text += spaces
            if idx == target_word_idx:
                highlight_end = len(buf_text)
        elif evt["type"] == "CONTROL":
            if evt.get("is_backspace") and buf_text:
                buf_text = buf_text[:-1]
            elif is_enm(word.text) or is_rcl(word.text):
                buf_text = ""
                row, col, color = None, None, None
                initial_state = None

    # Return buffer state even without PAC for annotation purposes
    if buf_text and initial_state is None:
        # Text without positioning - return as-is for annotation
        if highlight_start >= 0:
            return buf_text, highlight_start, highlight_end
        return buf_text, -1, -1

    if initial_state is None:
        return "", -1, -1

    row, col, color = initial_state
    result = "{R%02d C%02d %s}%s" % (row, col, color, buf_text)
    if highlight_start >= 0:
        prefix_len = len("{R%02d C%02d %s}" % (row, col, color))
        return result, prefix_len + highlight_start, prefix_len + highlight_end
    return result, -1, -1


def check_for_errors(line_text, col, line_start_pos, line_num):
    """Check if cursor is over an error and show error tooltip if so."""
    errors = find_errors(line_text, line_num)
    for start, end, error_type in errors:
        if start <= col < end:
            if error_type == "parity_error":
                editor.callTipShow(line_start_pos + start, "PARITY ERROR: Odd parity check failed")
            elif error_type == "cc_buffer_overflow":
                editor.callTipShow(
                    line_start_pos + start,
                    "CC BUFFER OVERFLOW: Packets extend past next timestamp",
                )
            elif error_type == "invalid_timestamp":
                editor.callTipShow(line_start_pos + start, "Invalid timestamp")
            else:
                editor.callTipShow(line_start_pos + start, "Invalid code")
            return True
    return False


def find_word_at_position(line_text, col):
    """Find the hex word at the given column position."""
    word_idx = 0
    for word in iter_hex_words(line_text):
        if word.is_paired and word.start > word.pair_start:
            continue
        if word.pair_start <= col < word.pair_end:
            return word, word_idx
        word_idx += 1
    return None, -1


def format_event_description(evt, word_text):
    """Format the event description line for tooltip."""
    lbl = evt.get("label", "").strip()
    suffix = " (%s)" % lbl if lbl else ""
    if evt["type"] == "TEXT":
        return 'TEXT: "%s" (%s)' % (evt["text"], word_text)
    elif evt["type"] == "PAC":
        ul = " Und" if evt["underline"] else ""
        return "PAC : Row %d, Col %d, %s%s (%s)%s" % (
            evt["row"],
            evt["col"],
            evt["color"],
            ul,
            word_text,
            suffix,
        )
    elif evt["type"] == "MIDROW":
        ul = " Und" if evt["underline"] else ""
        return "CMD : Mid-Row: %s%s%s" % (evt["color"][:3], ul, suffix)
    elif evt["type"] == "CONTROL":
        return "CMD : %s (%s)%s" % (
            evt["name"].split("(")[0].strip(),
            word_text,
            suffix,
        )
    elif evt["type"] == "INDENT":
        n = evt["spaces"]
        return "CMD : Indent %d %s (%s)%s" % (
            n,
            "space" if n == 1 else "spaces",
            word_text,
            suffix,
        )
    else:
        return decode_single_code(word_text, False)


def format_timestamp_description(hh, mm, ss, ff, word_idx, base_time):
    """Format the timestamp description line for tooltip."""
    if detected_frame_rate:
        pkt_time, _ = add_frames(hh, mm, ss, ff, word_idx, detected_frame_rate)
        pkt_word = "packet" if word_idx == 1 else "packets"
        return "TIME: %s (+%d %s)" % (pkt_time, word_idx, pkt_word)
    return "TIME: %s (+%d)" % (base_time, word_idx)


def on_dwell_start(args):
    """Handle mouse hover to show tooltip with event info and buffer state."""
    # Step 1: Validate file type
    filename = notepad.getCurrentFilename()
    if not filename or not filename.lower().endswith(".scc"):
        return
    pos = args["position"]
    if pos == -1:
        return

    # Step 2: Get line and position info
    line_num = editor.lineFromPosition(pos)
    line_text = editor.getLine(line_num)
    line_start_pos = editor.positionFromLine(line_num)
    col = pos - line_start_pos

    # Step 3: Check for errors first
    if check_for_errors(line_text, col, line_start_pos, line_num):
        return

    # Step 4: Parse timestamp
    ts_match = TIMESTAMP_PATTERN.search(line_text)
    if not ts_match:
        return
    anchor_pos = line_start_pos + ts_match.start()
    base_time = ts_match.group(0)
    try:
        ts = parse_timestamp_str(base_time)
    except (ValueError, TypeError):
        return

    # Step 5: Find word under cursor
    word, word_idx = find_word_at_position(line_text, col)
    if word is None:
        return

    # Step 6: Decode event
    evt = parse_scc_code(word.text, word.is_paired)

    # Step 7: Format tooltip components
    event_desc = format_event_description(evt, word.text)
    timestamp_desc = format_timestamp_description(ts.hours, ts.minutes, ts.seconds, ts.frames, word_idx, base_time)
    buffer_text, hl_start, hl_end = build_buffer_snapshot(line_text, word_idx, line_num)

    # Step 8: Generate and show tooltip
    tooltip = format_tooltip(
        event_desc,
        timestamp_desc,
        buffer_text,
        hl_start,
        hl_end,
        evt["type"] in ("CONTROL", "NULL"),
    )
    editor.callTipShow(anchor_pos, tooltip.encode("utf-8"))


def on_buffer_activated(args):
    """Handle file activation - detect frame rate and apply indicators."""
    global detected_frame_rate
    filename = notepad.getCurrentFilename()
    if filename and filename.lower().endswith(".scc"):
        editor.setMouseDwellTime(300)

        file_text = editor.getText()
        frame_rate, _ = detect_frame_rate(file_text)

        if frame_rate == "INVALID":
            console.write("ERROR: Invalid frame rate detected. Timecode math disabled.\n")
            detected_frame_rate = None
        else:
            console.write("Detected Frame Rate: {0}\n".format(frame_rate))
            detected_frame_rate = frame_rate

        setup_indicators()
        apply_all_indicators()
    else:
        editor.setMouseDwellTime(10000000)


editor.clearCallbacks([SCINTILLANOTIFICATION.DWELLSTART])
notepad.clearCallbacks([NOTIFICATION.BUFFERACTIVATED])

notepad.callback(on_buffer_activated, [NOTIFICATION.BUFFERACTIVATED])
editor.callback(on_dwell_start, [SCINTILLANOTIFICATION.DWELLSTART])

on_buffer_activated(None)
