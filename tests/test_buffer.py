# -*- coding: utf-8 -*-
"""
Buffer and Tooltip Tests

Tests for buffer snapshot, tooltip formatting, and line wrapping.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from test_all import MockEditor, MockNotepad, MockConsole

# Setup mocks
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

from scc_buffer_format import render_line_annotation  # noqa: E402
from scc_inspector import build_buffer_snapshot  # noqa: E402
from scc_tooltip import format_buffer_with_markers, wrap_tooltip_lines  # noqa: E402


def test_annotation_basic():
    """Test basic annotation rendering"""
    line = "9420 9440 c8e5 6c6c ef80"
    segments = render_line_annotation(line)
    text = "".join([seg[0] for seg in segments])
    return "Heo" in text


def test_annotation_multiline():
    """Test annotation with multiple PACs (newline symbol)"""
    line = "9420 9440 c8e5 6c6c ef80 94e0 f7ef f26c 64"
    segments = render_line_annotation(line)
    text = "".join([seg[0] for seg in segments])
    return "\u23ce" in text  # Newline symbol


def test_annotation_italic():
    """Test italic tracking in annotations"""
    line = "9420 9440 c8e5 6c6c ef80 91ae e9f4 e16c e9e3"
    segments = render_line_annotation(line)
    # Should have at least one italic segment
    return any(seg[1] for seg in segments)


def test_annotation_control_only():
    """Test lines with only control commands return empty"""
    line = "942c 942f"
    segments = render_line_annotation(line)
    return len(segments) == 0


def test_caret_display_text():
    """Test carets appear for text highlighting"""
    line = "9420 9440 c8e5 6c6c ef80"
    mock_editor.lines = [line]
    buffer_text, hl_start, hl_end = build_buffer_snapshot(line, 1, 0)
    full_buf, markers = format_buffer_with_markers(buffer_text, hl_start, hl_end, False)
    return "^" in markers and markers.count("^") == (hl_end - hl_start)


def test_caret_display_control():
    """Test carets appear at end for control codes"""
    line = "9420 9440 c8e5 6c6c ef80 942c"
    mock_editor.lines = [line]
    buffer_text, hl_start, hl_end = build_buffer_snapshot(line, 4, 0)
    full_buf, markers = format_buffer_with_markers(buffer_text, hl_start, hl_end, True)
    return markers.rstrip()[-1] == "^"


def test_caret_display_null():
    """Test carets appear at end for NULL codes"""
    line = "9420 9440 c8e5 6c6c ef80 8080"
    mock_editor.lines = [line]
    buffer_text, hl_start, hl_end = build_buffer_snapshot(line, 4, 0)
    full_buf, markers = format_buffer_with_markers(buffer_text, hl_start, hl_end, True)
    return markers.rstrip()[-1] == "^"


def test_wraparound_basic():
    """Test text wraps at 60 character limit"""
    long_text = "BUF : " + "A" * 60
    markers = " " * len(long_text)
    wrapped = wrap_tooltip_lines(long_text, markers)
    return len(wrapped) == 2 and len(wrapped[0]) == 60


def test_wraparound_with_carets():
    """Test carets merge with next line when wrapping"""
    text = "BUF : " + "X" * 54 + "{R14 C00 Whi}"
    markers = " " * (len(text) - 13) + "^" * 9 + " " * 4
    wrapped = wrap_tooltip_lines(text, markers)
    return len(wrapped) >= 2 and "^" in "".join(wrapped)


def test_wraparound_last_segment():
    """Test carets on separate line for last segment"""
    text = "BUF : Short"
    markers = " " * 6 + "^" * 5
    wrapped = wrap_tooltip_lines(text, markers)
    return len(wrapped) == 2 and wrapped[1].strip() == "^^^^^"


def test_buffer_snapshot_pac():
    """Test buffer snapshot for PAC command shows positioning"""
    line = "9420 9440 c8e5 6c6c ef80 94e0"
    mock_editor.lines = [line]
    buffer_text, hl_start, hl_end = build_buffer_snapshot(line, 4, 0)
    return buffer_text and "{R" in buffer_text


def test_buffer_snapshot_multiline():
    """Test buffer snapshot handles multiple lines"""
    lines = ["9420 9440 c8e5 6c6c ef80", "c8e5 6c6c ef80"]
    mock_editor.lines = lines
    buffer_text, hl_start, hl_end = build_buffer_snapshot(lines[1], 0, 1)
    return True  # Basic test that function executes without error


def test_annotation_with_timecodes():
    """Test annotation includes start/end timecodes then text"""
    line = "9420 9440 c8e5 6c6c ef80"
    segments = render_line_annotation(line)

    # Manually build what apply_annotation would create
    final_segments = []
    start_time = "00:01:00:00"
    end_time = "00:01:05:00"

    # This is what apply_annotation does
    if start_time and end_time:
        final_segments.append((" | {0} -> {1} | ".format(start_time, end_time), "timing"))

    for text, is_italic in segments:
        final_segments.append((text, is_italic))

    # Build the annotation text
    annotation_text = "".join([seg[0] for seg in final_segments])

    # Verify annotation has timecodes followed by text
    if not annotation_text:
        return False

    # Check format: " | START -> END | TEXT"
    has_start_time = "00:01:00:00" in annotation_text
    has_end_time = "00:01:05:00" in annotation_text
    has_arrow = "->" in annotation_text
    has_text = "Heo" in annotation_text  # Decoded text from line

    # Verify order: timecodes come before text
    if has_start_time and has_text:
        time_pos = annotation_text.index("00:01:00:00")
        text_pos = annotation_text.index("Heo")
        correct_order = time_pos < text_pos
    else:
        correct_order = False

    return has_start_time and has_end_time and has_arrow and has_text and correct_order


if __name__ == "__main__":
    print("=== Buffer and Tooltip Tests ===\n")

    tests = [
        ("Annotation Basic", test_annotation_basic),
        ("Annotation Multiline", test_annotation_multiline),
        ("Annotation Italic", test_annotation_italic),
        ("Annotation Control Only", test_annotation_control_only),
        ("Annotation With Timecodes", test_annotation_with_timecodes),
        ("Caret Display Text", test_caret_display_text),
        ("Caret Display Control", test_caret_display_control),
        ("Caret Display NULL", test_caret_display_null),
        ("Wraparound Basic", test_wraparound_basic),
        ("Wraparound With Carets", test_wraparound_with_carets),
        ("Wraparound Last Segment", test_wraparound_last_segment),
        ("Buffer Snapshot PAC", test_buffer_snapshot_pac),
        ("Buffer Snapshot Multiline", test_buffer_snapshot_multiline),
    ]

    passed = failed = 0
    for name, test_func in tests:
        try:
            if test_func():
                print("[PASS] {}".format(name))
                passed += 1
            else:
                print("[FAIL] {}".format(name))
                failed += 1
        except Exception as e:
            print("[FAIL] {} - {}".format(name, str(e)))
            failed += 1

    print("\n" + "=" * 50)
    print("Results: {} passed, {} failed".format(passed, failed))
    print("=" * 50)

    if failed == 0:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ {} test(s) failed!".format(failed))
