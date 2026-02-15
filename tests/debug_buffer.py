# -*- coding: utf-8 -*-
"""
Buffer Debug Tool

Interactive tool to test buffer buildup and hover behavior.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from test_all import MockEditor, MockNotepad, MockConsole

# Setup mocks before importing
mock_editor = MockEditor()
mock_notepad = MockNotepad()
mock_console = MockConsole()

sys.modules["Npp"] = type(
    "obj",
    (),
    {
        "editor": mock_editor,
        "notepad": mock_notepad,
        "console": mock_console,
        "SCINTILLANOTIFICATION": type("obj", (), {"DWELLSTART": 0, "UPDATEUI": 1})(),
        "NOTIFICATION": type("obj", (), {"BUFFERACTIVATED": 0})(),
        "INDICATORSTYLE": type("obj", (), {"SQUIGGLE": 0, "ROUNDBOX": 1, "STRAIGHTBOX": 2})(),
        "ANNOTATIONVISIBLE": type("obj", (), {"STANDARD": 0})(),
    },
)()

from scc_decoder import iter_hex_words, parse_scc_code  # noqa: E402
from scc_inspector import build_buffer_snapshot  # noqa: E402
from scc_tooltip import format_buffer_with_markers, wrap_tooltip_lines  # noqa: E402


def debug_hover_on_line(line_num, line_text):
    """Show buffer state when hovering over each word in a line"""
    print("\n" + "=" * 70)
    print("LINE {}: {}".format(line_num, line_text[:60] + "..." if len(line_text) > 60 else line_text))
    print("=" * 70)

    words = list(iter_hex_words(line_text))

    for idx, word in enumerate(words):
        if word.is_paired and word.start > word.pair_start:
            continue

        evt = parse_scc_code(word.text, word.is_paired)
        buffer_text, hl_start, hl_end = build_buffer_snapshot(line_text, idx, line_num)

        print("\n[Word {}] {} - {}".format(idx, word.text, evt["type"]))
        if evt["type"] == "TEXT":
            print("  Text: '{}'".format(evt.get("text", "")))
        elif evt["type"] == "CONTROL":
            print("  Cmd: {}".format(evt.get("name", "")))
        elif evt["type"] == "PAC":
            print("  Row: {}, Col: {}".format(evt["row"], evt["col"]))

        if buffer_text:
            full_buf, markers = format_buffer_with_markers(buffer_text, hl_start, hl_end, evt["type"] in ("CONTROL", "NULL"))
            wrapped = wrap_tooltip_lines(full_buf, markers)
            for line in wrapped:
                print("  {}".format(line))
        else:
            print("  Buffer: (empty)")


def main():
    # EDIT LINES HERE - Just paste your SCC lines between the triple quotes:
    test_data = """
00:00:13:10	9420 9440 5bc1 4c4c 20cd 49c7 c854 5d80 91ae d9ef 7520 f761 6ef4 20f4 ef20 e5f8 7061 6e64 94e0 97a2 91ae f468 e520 68e5 f2ef 2062 e9ec ec62 ef61 f264 20e3 6861 f2f4 bf80 942c 8080 8080 942f
    """

    lines = [line.strip() for line in test_data.strip().split("\n") if line.strip()]
    mock_editor.lines = lines

    for line_num, line_text in enumerate(lines):
        debug_hover_on_line(line_num, line_text)


if __name__ == "__main__":
    main()
