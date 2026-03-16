# -*- coding: utf-8 -*-
"""
JSON-Driven Test Suite for SCC Inspector

Tests are loaded from JSON files in scc-core/test-cases/.
This file replaces test_all.py and test_control_commands.py after verification.
"""

import sys
import io
import os
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))


class MockConsole:
    def write(self, *args):
        pass


class MockEditor:
    def __init__(self):
        self.lines = []
        self.firstVisibleLine = 0

    def clearCallbacks(self, *args):
        pass

    def callback(self, *args):
        pass

    def getLineCount(self):
        return len(self.lines)

    def getLine(self, num):
        return self.lines[num] if num < len(self.lines) else ""

    def setMouseDwellTime(self, *args):
        pass

    def getText(self):
        return "\n".join(self.lines)

    def lineFromPosition(self, pos):
        return 0

    def positionFromLine(self, line):
        return 0

    def setIndicatorCurrent(self, *args):
        pass

    def indicatorClearRange(self, *args):
        pass

    def indicatorFillRange(self, *args):
        pass

    def annotationSetText(self, *args):
        pass

    def annotationSetStyles(self, *args):
        pass

    def callTipShow(self, *args):
        pass

    def indicSetStyle(self, *args):
        pass

    def indicSetFore(self, *args):
        pass

    def indicSetUnder(self, *args):
        pass

    def styleSetFore(self, *args):
        pass

    def styleSetBack(self, *args):
        pass

    def annotationSetVisible(self, *args):
        pass

    def docLineFromVisible(self, line):
        return line

    def visibleFromDocLine(self, line):
        return line

    def getLength(self):
        return 0


class MockNotepad:
    def clearCallbacks(self, *args):
        pass

    def callback(self, *args):
        pass

    def getCurrentFilename(self):
        return "test.txt"

    def getCurrentBufferID(self):
        return 1


class MockNpp:
    pass


sys.modules["Npp"] = MockNpp()
sys.modules["Npp"].editor = MockEditor()
sys.modules["Npp"].notepad = MockNotepad()
sys.modules["Npp"].console = MockConsole()
sys.modules["Npp"].SCINTILLANOTIFICATION = type("obj", (object,), {"DWELLSTART": 0, "UPDATEUI": 1})
sys.modules["Npp"].NOTIFICATION = type("obj", (object,), {"BUFFERACTIVATED": 0, "FILECLOSED": 1})
sys.modules["Npp"].INDICATORSTYLE = type("obj", (object,), {"SQUIGGLE": 0, "ROUNDBOX": 1})
sys.modules["Npp"].ANNOTATIONVISIBLE = type("obj", (object,), {"BOXED": 0})

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

import scc_inspector
from scc_decoder import (
    parse_scc_code,
    decode_single_code,
    iter_hex_words,
    is_pairing_command,
    HEX_PATTERN,
)
from scc_timecode import parse_timestamp_str, add_frames, detect_frame_rate, validate_timestamp
from scc_inspector import build_time_map, decode_full_line, find_errors
from Npp import editor

TEST_CASES_DIR = os.path.join(parent_dir, "scc-core", "test-cases")


def load_test_cases(filename):
    filepath = os.path.join(TEST_CASES_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def check_parity(byte_val):
    return bin(byte_val).count("1") % 2 != 0


passed = 0
failed = 0
skipped = 0


def run_test(name, test_func):
    global passed, failed, skipped
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


def test_decoder_cases():
    cases = load_test_cases("decoder_cases.json")

    for case in cases["standard_characters"]:
        evt = parse_scc_code(case["input"])
        if evt["type"] != case["expectedType"]:
            return False
        if evt.get("text", "") != case["expectedText"]:
            return False
    return True


def test_extended_characters():
    cases = load_test_cases("decoder_cases.json")

    for case in cases["extended_characters"]:
        evt = parse_scc_code(case["input"])
        if evt["type"] != case["expectedType"]:
            return False
        if evt.get("text", "") != case["expectedText"]:
            return False
        if evt.get("is_extended", False) != case["isExtended"]:
            return False
    return True


def test_special_characters():
    cases = load_test_cases("decoder_cases.json")

    for case in cases["special_characters"]:
        evt = parse_scc_code(case["input"])
        if evt["type"] != case["expectedType"]:
            return False
        if evt.get("text", "") != case["expectedText"]:
            return False
    return True


def test_pac():
    cases = load_test_cases("decoder_cases.json")

    for case in cases["pac_tests"]:
        evt = parse_scc_code(case["input"])
        if evt["type"] != case["expectedType"]:
            return False
        if evt.get("row") != case["expectedRow"]:
            return False
        if evt.get("col") != case["expectedCol"]:
            return False
    return True


def test_midrow():
    cases = load_test_cases("decoder_cases.json")

    for case in cases["midrow_tests"]:
        evt = parse_scc_code(case["input"])
        if evt["type"] != case["expectedType"]:
            return False
        if case["expectedColor"] and evt.get("color") != case["expectedColor"]:
            return False
    return True


def test_control_codes_not_text():
    cases = load_test_cases("decoder_cases.json")

    for case in cases["control_codes_not_text"]:
        evt = parse_scc_code(case["input"])
        if evt["type"] == "TEXT":
            return False
        if evt["type"] not in ["CONTROL", "PAC", "UNKNOWN", "ERROR"]:
            return False
    return True


def test_line_decode():
    cases = load_test_cases("decoder_cases.json")

    for case in cases["line_decode_tests"]:
        segments = decode_full_line(case["line"])
        text = "".join([seg[0] for seg in segments])
        if case["expectedContains"] not in text:
            return False
    return True


def test_pair_detection():
    cases = load_test_cases("decoder_cases.json")

    for case in cases["pair_detection"]:
        words = list(iter_hex_words(case["line"]))
        result = [w.is_paired for w in words]
        if result != case["expectedPaired"]:
            return False
    return True


def test_hex_pattern():
    cases = load_test_cases("decoder_cases.json")

    for case in cases["hex_pattern"]:
        matches = HEX_PATTERN.findall(case["input"])
        if len(matches) != case["expectedMatchCount"]:
            return False
    return True


def test_control_commands():
    cases = load_test_cases("control_commands_cases.json")

    for case in cases["control_commands"]:
        evt = parse_scc_code(case["input"])
        if evt["type"] != case["expectedType"]:
            return False
        if not evt.get("name"):
            return False
    return True


def test_tab_offsets():
    cases = load_test_cases("control_commands_cases.json")

    for case in cases["tab_offsets"]:
        evt = parse_scc_code(case["input"])
        if evt["type"] != case["expectedType"]:
            return False
        if evt.get("spaces") != case["expectedSpaces"]:
            return False
    return True


def test_parse_timestamp():
    cases = load_test_cases("timecode_cases.json")

    for case in cases["parse_timestamp"]:
        result = parse_timestamp_str(case["input"])
        expected = tuple(case["expected"])
        if result != expected:
            return False
    return True


def test_add_frames_ndf():
    cases = load_test_cases("timecode_cases.json")

    for case in cases["add_frames"]["29.97 NDF"]:
        result_tc, result_offset = add_frames(case["hh"], case["mm"], case["ss"], case["ff"], case["offset"], "29.97 NDF")
        if result_tc != case["expectedTc"]:
            return False
        if result_offset != case["expectedOffset"]:
            return False
    return True


def test_add_frames_df():
    cases = load_test_cases("timecode_cases.json")

    for case in cases["add_frames"]["29.97 DF"]:
        result_tc, result_offset = add_frames(case["hh"], case["mm"], case["ss"], case["ff"], case["offset"], "29.97 DF")
        if result_tc != case["expectedTc"]:
            return False
        if result_offset != case["expectedOffset"]:
            return False
    return True


def test_add_frames_2398():
    cases = load_test_cases("timecode_cases.json")

    for case in cases["add_frames"]["23.98"]:
        result_tc, result_offset = add_frames(case["hh"], case["mm"], case["ss"], case["ff"], case["offset"], "23.98")
        if result_tc != case["expectedTc"]:
            return False
        if result_offset != case["expectedOffset"]:
            return False
    return True


def test_add_frames_25():
    cases = load_test_cases("timecode_cases.json")

    for case in cases["add_frames"]["25"]:
        result_tc, result_offset = add_frames(case["hh"], case["mm"], case["ss"], case["ff"], case["offset"], "25")
        if result_tc != case["expectedTc"]:
            return False
        if result_offset != case["expectedOffset"]:
            return False
    return True


def test_validate_timestamp():
    cases = load_test_cases("timecode_cases.json")

    for ts in cases["validate_timestamp"]["valid"]:
        if not validate_timestamp(ts):
            return False
    for ts in cases["validate_timestamp"]["invalid"]:
        if validate_timestamp(ts):
            return False
    return True


def test_frame_rate_detection():
    cases = load_test_cases("timecode_cases.json")

    for case in cases["frame_rate_detection"]:
        rate, count = detect_frame_rate(case["content"])
        if rate != case["expectedRate"]:
            return False
    return True


def test_parity_odd():
    cases = load_test_cases("parity_cases.json")

    for byte_val in cases["odd_parity_bytes"]:
        if not check_parity(byte_val):
            return False
    return True


def test_parity_even():
    cases = load_test_cases("parity_cases.json")

    for byte_val in cases["even_parity_bytes"]:
        if check_parity(byte_val):
            return False
    return True


def test_parity_valid_codes():
    cases = load_test_cases("parity_cases.json")

    for code in cases["valid_scc_codes"]:
        errors = find_errors(code)
        parity_errors = [e for e in errors if e[2] == "parity_error"]
        if parity_errors:
            return False
    return True


def test_parity_invalid_codes():
    cases = load_test_cases("parity_cases.json")

    for case in cases["invalid_scc_codes"]:
        errors = find_errors(case["code"])
        parity_errors = [e for e in errors if e[2] == "parity_error"]
        if case["shouldHaveError"] and not parity_errors:
            return False
        if not case["shouldHaveError"] and parity_errors:
            return False
    return True


def test_parity_error_position():
    cases = load_test_cases("parity_cases.json")
    ep = cases["error_position"]

    errors = find_errors(ep["line"])
    parity_errors = [e for e in errors if e[2] == "parity_error"]
    if len(parity_errors) != ep["expectedErrorCount"]:
        return False
    start, end, _, _ = parity_errors[0]
    return ep["line"][start:end] == ep["expectedErrorCode"]


def test_event_times():
    cases = load_test_cases("event_time_cases.json")

    for case in cases["event_times"]:
        editor.lines = case["lines"]
        time_map, _, _ = build_time_map(case["frameRate"])
        times = time_map.get(case["startLine"], (None, None))
        start, end = times[0], times[1]
        if start != case["expectedStart"] or end != case["expectedEnd"]:
            return False
    return True


def test_parity_priority():
    """Issue 1: test_parity_priority_over_invalid"""
    cases = load_test_cases("parity_cases.json")

    for case in cases["priority_tests"]:
        errors = find_errors(case["input"])
        if not errors:
            return False
        if errors[0][2] != case["expectedErrorType"]:
            return False
    return True


def test_special_na_backspace():
    """Issue 1: test_special_na_no_backspace - 9137 (music note) has is_extended: false"""
    cases = load_test_cases("decoder_cases.json")

    for case in cases["special_characters"]:
        if case["input"] == "9137" or case["input"] == "1937":
            evt = parse_scc_code(case["input"])
            if evt["type"] != "TEXT":
                return False
            if evt.get("is_extended", False) != case["isExtended"]:
                return False
            if case["isExtended"] != False:
                return False
    return True


def test_westeu_backspace():
    """Issue 1: test_westeu_triggers_backspace - 92a1 (extended char) has is_extended: true"""
    cases = load_test_cases("decoder_cases.json")

    for case in cases["extended_characters"]:
        if case["input"] == "92a1" or case["input"] == "1aa1":
            evt = parse_scc_code(case["input"])
            if evt["type"] != "TEXT":
                return False
            if evt.get("is_extended", False) != case["isExtended"]:
                return False
            if case["isExtended"] != True:
                return False
    return True


def test_pairing_command():
    """Issue 1: test_is_command - is_pairing_command() returns true for 0x9140, false for 0xc1c2"""
    cases = load_test_cases("decoder_cases.json")

    for case in cases["pairing_command_tests"]:
        val = int(case["input"], 16)
        result = is_pairing_command(val)
        if result != case["isPairingCommand"]:
            return False
    return True


def test_decode_single():
    """Issue 1: test_decode_single_code - decode_single_code() contains expected text"""
    cases = load_test_cases("decoder_cases.json")

    for case in cases["decode_single_code_tests"]:
        result = decode_single_code(case["input"])
        if case["expectedContains"] not in result:
            return False
    return True


def test_iterator_module():
    """Issue 1: test_iterator - iter_hex_words returns correct word count and pairing"""
    cases = load_test_cases("decoder_cases.json")

    for case in cases["iterator_tests"]:
        words = list(iter_hex_words(case["line"]))
        if len(words) != case["expectedWordCount"]:
            return False
        result = [w.is_paired for w in words]
        if result != case["expectedPairing"]:
            return False
    return True


if __name__ == "__main__":
    print("=== SCC Inspector JSON-Driven Test Suite ===\n")

    print("--- Decoder Tests ---")
    run_test("Standard Characters", test_decoder_cases)
    run_test("Extended Characters", test_extended_characters)
    run_test("Special Characters", test_special_characters)
    run_test("PAC Tests", test_pac)
    run_test("MIDROW Tests", test_midrow)
    run_test("Control Codes Not Text", test_control_codes_not_text)
    run_test("Line Decode Tests", test_line_decode)
    run_test("Pair Detection", test_pair_detection)
    run_test("Hex Pattern", test_hex_pattern)

    print("\n--- Control Command Tests ---")
    run_test("Control Commands", test_control_commands)
    run_test("Tab Offsets", test_tab_offsets)

    print("\n--- Timecode Tests ---")
    run_test("Parse Timestamp", test_parse_timestamp)
    run_test("Add Frames 29.97 NDF", test_add_frames_ndf)
    run_test("Add Frames 29.97 DF", test_add_frames_df)
    run_test("Add Frames 23.98", test_add_frames_2398)
    run_test("Add Frames 25", test_add_frames_25)
    run_test("Validate Timestamp", test_validate_timestamp)
    run_test("Frame Rate Detection", test_frame_rate_detection)

    print("\n--- Parity Tests ---")
    run_test("Odd Parity Check", test_parity_odd)
    run_test("Even Parity Check", test_parity_even)
    run_test("Valid SCC Codes", test_parity_valid_codes)
    run_test("Invalid SCC Codes", test_parity_invalid_codes)
    run_test("Error Position", test_parity_error_position)
    run_test("Parity Priority", test_parity_priority)
    run_test("Special NA No Backspace", test_special_na_backspace)
    run_test("West EU Triggers Backspace", test_westeu_backspace)
    run_test("Is Command (Pairing)", test_pairing_command)
    run_test("Decode Single Code", test_decode_single)
    run_test("Iterator Module", test_iterator_module)

    print("\n--- Event Time Tests ---")
    run_test("Event Times", test_event_times)

    print("\n" + "=" * 50)
    print("Results: {} passed, {} failed, {} skipped".format(passed, failed, skipped))
    print("Total: {} tests".format(passed + failed + skipped))
    print("=" * 50)

    if failed == 0:
        print("\nAll tests passed!")
    else:
        print("\n{} test(s) failed!".format(failed))
