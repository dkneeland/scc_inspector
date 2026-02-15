# -*- coding: utf-8 -*-
"""
SCC Buffer Formatting Module

Fast single-pass annotation rendering.
"""

from scc_decoder import iter_hex_words, parse_scc_code


def render_line_annotation(line_text):
    """
    Fast single-pass annotation renderer.

    Returns list of (text, style) tuples for display.
    Style can be: False (normal), True (italic), or 'newline' (carriage return symbol).
    Skips lines with only control commands.
    """
    segments = []
    current_text = ""
    is_italic = False
    has_content = False

    for word in iter_hex_words(line_text):
        if word.is_paired and word.start > word.pair_start:
            continue

        evt = parse_scc_code(word.text, word.is_paired)

        if evt["type"] == "TEXT":
            current_text += evt["text"]
            has_content = True

        elif evt["type"] == "PAC":
            if current_text:
                segments.append((current_text, is_italic))
                current_text = ""
            if segments:  # Mid-line PAC = newline
                segments.append((u"⏎", "newline"))  # fmt: skip
            is_italic = evt.get("is_italic", False)
            has_content = True

        elif evt["type"] == "MIDROW":
            if current_text:
                segments.append((current_text, is_italic))
                current_text = ""
            is_italic = evt.get("is_italic", False)
            has_content = True

        elif evt["type"] == "INDENT":
            current_text += " " * evt["spaces"]
            has_content = True

        elif evt["type"] == "CONTROL":
            if evt.get("is_backspace") and current_text:
                current_text = current_text[:-1]

    if current_text:
        segments.append((current_text, is_italic))

    return segments if has_content else []
