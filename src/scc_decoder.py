# -*- coding: utf-8 -*-
"""
SCC Decoder Module

Low-level EIA-608 closed caption decoding logic based on libcaption reference implementation.
This module contains stable, tested decoding functions and should NOT be modified unless
fixing bugs in the core decoder logic.

DO NOT MODIFY unless you understand the EIA-608 specification.
"""

import re


# Bit-masking functions for EIA-608 command detection
def is_preamble(cc_data):
    return 0x1040 == (0x7040 & cc_data)


def is_midrow_change(cc_data):
    return 0x1120 == (0x7770 & cc_data)


def is_control(cc_data):
    if 0x0200 & cc_data:
        return False
    return (0x1400 == (0x7600 & cc_data)) or (0x1700 == (0x7700 & cc_data))


def is_tab_offset(cc_data):
    return 0x1720 == (0x777C & cc_data)


# Pattern matching
HEX_PATTERN = re.compile(r"\b[0-9a-fA-F]{4}\b")
TIMESTAMP_PATTERN = re.compile(r"\d\d:\d\d:\d\d[:;]\d\d")

# EIA-608 Character Map
CHAR_MAP = u" !\"#$%&'()á+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[é]íóúabcdefghijklmnopqrstuvwxyzç÷Ññ█®°½¿™¢£♪à èâêîôûÁÉÓÚÜü‘¡*’—©℠•“”ÀÂÇÈÊËëÎÏïÔÙùÛ«»ÃãÍÌìÒòÕõ{}\\^_¦~ÄäÖöß¥¤|ÅåØø┌┐└┘"  # fmt: skip

# Color codes
COLOR_LIST = ("White", "Green", "Blue", "Cyan", "Red", "Yellow", "Magenta", "Italics")

# Row mapping
ROW_MAP = [10, -1, 0, 1, 2, 3, 11, 12, 13, 14, 4, 5, 6, 7, 8, 9]

# Control command names
COMMAND_NAMES = {
    0x20: "Resume Caption Loading (RCL)",
    0x21: "Backspace",
    0x24: "Delete to End of Row (DER)",
    0x25: "Roll-Up 2 Lines (RU2)",
    0x26: "Roll-Up 3 Lines (RU3)",
    0x27: "Roll-Up 4 Lines (RU4)",
    0x28: "Flash ON (FON)",
    0x29: "Resume Direct Captioning (RDC)",
    0x2A: "Text Restart (TR)",
    0x2B: "Resume Text Display (RTD)",
    0x2C: "Clear Screen (EDM)",
    0x2D: "Carriage Return (CR)",
    0x2E: "Erase Non-Displayed Memory (ENM)",
    0x2F: "Display Caption (EOC)",
}


class HexWord:
    """Represents a hex word in an SCC file with pairing information"""

    __slots__ = ("text", "start", "end", "is_paired", "pair_start", "pair_end")

    def __init__(self, match, is_paired=False, pair_match=None):
        self.text = match.group(0).lower()
        self.start = match.start()
        self.end = match.end()
        self.is_paired = is_paired

        if is_paired and pair_match:
            self.pair_start = min(match.start(), pair_match.start())
            self.pair_end = max(match.end(), pair_match.end())
        else:
            self.pair_start = self.start
            self.pair_end = self.end


def is_pairing_command(val):
    """Check if a hex value requires pairing (control, preamble, midrow, or tab)"""
    masked = val & 0x7F7F
    return is_control(masked) or is_preamble(masked) or is_midrow_change(masked) or is_tab_offset(masked)


def iter_hex_words(line_text):
    """Iterate through hex words in a line, detecting and pairing commands"""
    matches = list(HEX_PATTERN.finditer(line_text))
    i = 0
    while i < len(matches):
        curr = matches[i]
        curr_text = curr.group(0).lower()
        curr_val = int(curr_text, 16)

        if is_pairing_command(curr_val) and i + 1 < len(matches):
            next_match = matches[i + 1]
            if next_match.group(0).lower() == curr_text:
                yield HexWord(curr, is_paired=True, pair_match=next_match)
                yield HexWord(next_match, is_paired=True, pair_match=curr)
                i += 2
                continue

        yield HexWord(curr, is_paired=False)
        i += 1


def parse_scc_code(word_text, is_pair=False):
    """
    Parse a single SCC hex word into a structured event dictionary.

    Based on libcaption reference implementation.
    Returns dict with 'type' key and type-specific fields.
    """
    word = word_text.lower()

    if word == "8080" or word == "0000":
        return {"type": "NULL"}

    raw_val = int(word, 16)
    b1 = (raw_val >> 8) & 0xFF
    b2 = raw_val & 0xFF
    if not (bin(b1).count("1") % 2 != 0 and bin(b2).count("1") % 2 != 0):
        return {"type": "ERROR", "desc": "Parity Error"}

    cc_data = raw_val & 0x7F7F
    chan = 1 if (raw_val & 0x0800) else 0
    field = 1 if (raw_val & 0x0100) else 0
    channel = field * 2 + chan + 1
    label = "" if channel == 1 else "CC%d" % channel

    if is_tab_offset(cc_data):
        return {"type": "INDENT", "label": label, "spaces": (cc_data & 0xFF) - 0x20}

    if is_control(cc_data):
        cmd_byte = cc_data & 0xFF
        if cmd_byte in COMMAND_NAMES:
            return {
                "type": "CONTROL",
                "label": label,
                "name": COMMAND_NAMES[cmd_byte],
                "is_newline": cmd_byte == 0x2D,
                "is_backspace": cmd_byte == 0x21,
            }

    if is_preamble(cc_data):
        row_idx = ((0x0700 & cc_data) >> 7) | ((0x0020 & cc_data) >> 5)
        row = ROW_MAP[row_idx] if row_idx < len(ROW_MAP) else 14
        underline = bool(cc_data & 1)

        if cc_data & 0x10:
            col = 4 * ((0x000E & cc_data) >> 1)
            color = "White"
        else:
            col = 0
            color_idx = (0x000E & cc_data) >> 1
            color = COLOR_LIST[color_idx] if color_idx < len(COLOR_LIST) else "White"

        return {
            "type": "PAC",
            "label": label,
            "row": row,
            "col": col,
            "color": color,
            "underline": underline,
            "is_italic": color == "Italics",
        }

    if is_midrow_change(cc_data):
        color_idx = (0x000E & cc_data) >> 1
        color = COLOR_LIST[color_idx] if color_idx < len(COLOR_LIST) else "White"
        return {
            "type": "MIDROW",
            "label": label,
            "color": color,
            "underline": bool(cc_data & 1),
            "is_italic": color == "Italics",
        }

    if 0x1130 == (cc_data & 0x7770):
        idx = (cc_data & 0xFFFF) - 0x1130 + 0x60
        if 0 <= idx < len(CHAR_MAP):
            return {
                "type": "TEXT",
                "label": label,
                "text": CHAR_MAP[idx],
                "is_extended": False,
            }

    if 0x1220 == (cc_data & 0x7660):
        idx = -1
        if 0x1220 <= cc_data < 0x1240:
            idx = cc_data - 0x1220 + 0x70
        elif 0x1320 <= cc_data < 0x1340:
            idx = cc_data - 0x1320 + 0x90
        if 0 <= idx < len(CHAR_MAP):
            return {
                "type": "TEXT",
                "label": label,
                "text": CHAR_MAP[idx],
                "is_extended": True,
            }

    if 0 != ((cc_data & 0x7F00) >> 8):
        c1 = (cc_data >> 8) - 0x20
        c2 = -1
        if 0x0020 <= (cc_data & 0xFF) < 0x0080:
            c2 = (cc_data & 0xFF) - 0x20
        chars = ""
        if 0 <= c1 < len(CHAR_MAP):
            chars += CHAR_MAP[c1]
        if 0 <= c2 < len(CHAR_MAP):
            chars += CHAR_MAP[c2]
        return {"type": "TEXT", "label": label, "text": chars}

    return {"type": "UNKNOWN", "label": label, "raw": word}


def decode_single_code(word_text, is_pair=False):
    """Convert a hex word to human-readable description"""
    evt = parse_scc_code(word_text, is_pair)
    prefix = "[Pair] " if is_pair else ""
    lbl = evt.get("label", "")

    if evt["type"] == "PAC":
        ul = " Underlined" if evt["underline"] else ""
        return "{0}{1}Row {2:02}, Col {3:02}, {4}{5}".format(prefix, lbl, evt["row"], evt["col"], evt["color"], ul)
    elif evt["type"] == "MIDROW":
        ul = " Underlined" if evt["underline"] else ""
        return "{0}{1}Mid-row: {2}{3}".format(prefix, lbl, evt["color"], ul)
    elif evt["type"] == "CONTROL":
        return evt.get("desc") or "{0}{1}{2}".format(prefix, lbl, evt["name"])
    elif evt["type"] == "INDENT":
        n = evt["spaces"]
        return "{0}{1}Indent {2} {3}".format(prefix, lbl, n, "space" if n == 1 else "spaces")
    elif evt["type"] == "TEXT":
        return '{0}{1}Text: "{2}"'.format(prefix, lbl, evt["text"])
    elif evt["type"] == "NULL":
        return "Null / Padding"
    elif evt["type"] == "ERROR":
        return "Error: " + evt["desc"]
    return "Unknown Code"


# Buffer state helper functions
def get_command_byte(word_text):
    """Extract command byte from hex word (works for all channels)"""
    return int(word_text, 16) & 0xFF


def _is_command(word_text, cmd_byte):
    """Check if word_text matches the given command byte"""
    try:
        return get_command_byte(word_text) == cmd_byte
    except (ValueError, TypeError, AttributeError):
        return False


def is_eoc(word_text):
    """Check if command is End of Caption (0x2F)"""
    return _is_command(word_text, 0x2F)


def is_rcl(word_text):
    """Check if command is Resume Caption Loading (0x20)"""
    return _is_command(word_text, 0x20)


def is_enm(word_text):
    """Check if command is Erase Non-displayed Memory (0x2E)"""
    return _is_command(word_text, 0x2E)


def is_edm(word_text):
    """Check if command is Erase Displayed Memory (0x2C)"""
    return _is_command(word_text, 0x2C)
