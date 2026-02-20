# -*- coding: utf-8 -*-
"""
SCC Tooltip Module

Tooltip formatting logic for hover tooltips.
Handles marker generation, line wrapping, and text formatting.
"""

TOOLTIP_WIDTH = 60


def format_buffer_with_markers(buffer_text, highlight_start, highlight_end, is_control):
    """
    Add caret markers to show where in the buffer the current word affects.

    Returns: (formatted_text, marker_text)
    """
    prefix = "BUF : "
    full_text = prefix + buffer_text

    if is_control and buffer_text:
        full_text += " "

    markers = [" "] * len(full_text)

    if highlight_start >= 0 and highlight_end > highlight_start:
        abs_start = highlight_start + len(prefix)
        abs_end = highlight_end + len(prefix)
        for i in range(abs_start, min(abs_end, len(markers))):
            markers[i] = "^"
    elif is_control and buffer_text:
        markers[-1] = "^"

    return full_text, "".join(markers)


def wrap_tooltip_lines(text, markers, max_width=TOOLTIP_WIDTH):
    """
    Wrap long tooltip lines with proper indentation.

    Returns: list of formatted lines
    """
    lines = []
    indent = "      "
    is_first = True
    segments = []

    # Split into segments
    while text:
        limit = max_width if is_first else (max_width - len(indent))
        text_slice = text[:limit]
        mark_slice = markers[:limit]
        display_text = text_slice if is_first else (indent + text_slice)
        display_mark = mark_slice if is_first else (indent + mark_slice)
        text = text[limit:]
        markers = markers[limit:]
        segments.append((display_text, display_mark, "^" in mark_slice))
        is_first = False

    # Output segments with caret positioning
    i = 0
    while i < len(segments):
        text_line, mark_line, has_carets = segments[i]
        lines.append(text_line)

        if not has_carets:
            i += 1
            continue

        is_last_segment = i >= len(segments) - 1
        if is_last_segment:
            lines.append(mark_line)
            i += 1
        else:
            # Merge carets with next line
            next_text = segments[i + 1][0]
            caret_str = mark_line.lstrip()
            padding = max(0, max_width - len(next_text) - len(caret_str))
            lines.append(next_text + " " * padding + caret_str)
            if segments[i + 1][2]:
                lines.append(segments[i + 1][1])
            i += 2

    return lines


def format_tooltip(event_desc, timestamp_desc, buffer_text, highlight_start, highlight_end, is_control, overflow_info=None):
    """
    Format complete tooltip with event info, timestamp, and buffer state.

    Args:
        event_desc: Description of the event (e.g., "TEXT: 'Hello' (4865)")
        timestamp_desc: Timestamp info (e.g., "TIME: 00:00:01:00 (+2f)")
        buffer_text: Current buffer state string
        highlight_start: Start position of highlight in buffer (-1 if none)
        highlight_end: End position of highlight in buffer (-1 if none)
        is_control: Whether this is a control command
        overflow_info: Tuple of (is_overflow, overflow_count) or None

    Returns: Formatted tooltip string
    """
    separator = "-" * TOOLTIP_WIDTH

    full_buf, markers = format_buffer_with_markers(buffer_text, highlight_start, highlight_end, is_control)
    wrapped = wrap_tooltip_lines(full_buf, markers)
    
    if overflow_info and overflow_info[0]:
        overflow_msg = "!!! BUFFER OVERFLOW !!!"
        buffer_section = overflow_msg + "\n" + "\n".join(wrapped)
    else:
        buffer_section = "\n".join(wrapped)

    return "%s\n%s\n%s\n%s\n%s" % (
        event_desc,
        separator,
        timestamp_desc,
        separator,
        buffer_section,
    )
