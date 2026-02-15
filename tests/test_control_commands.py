# -*- coding: utf-8 -*-
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))


class MockNpp:
    pass


sys.modules["Npp"] = MockNpp()

from scc_decoder import parse_scc_code  # noqa: E402

# All control commands from SCC_Codes.html
CONTROL_COMMANDS = {
    # Channel 1
    "9420": "Resume Caption Loading (RCL)",
    "9429": "Resume Direct Captioning (RDC)",
    "9425": "Roll-Up 2 Lines (RU2)",
    "9426": "Roll-Up 3 Lines (RU3)",
    "94a7": "Roll-Up 4 Lines (RU4)",
    "942a": "Text Restart (TR)",
    "94ab": "Resume Text Display (RTD)",
    "942c": "Erase Displayed Memory (EDM)",
    "94ae": "Erase Non-displayed Memory (ENM)",
    "942f": "End Of Caption (EOC)",
    "94a1": "BackSpace (BS)",
    "94a4": "Delete to End of Row (DER)",
    "94ad": "Carriage Return (CR)",
    "94a8": "Flash ON (FON)",
    # Channel 2
    "1c20": "Resume Caption Loading (RCL)",
    "1c29": "Resume Direct Captioning (RDC)",
    "1c25": "Roll-Up 2 Lines (RU2)",
    "1c26": "Roll-Up 3 Lines (RU3)",
    "1ca7": "Roll-Up 4 Lines (RU4)",
    "1c2a": "Text Restart (TR)",
    "1cab": "Resume Text Display (RTD)",
    "1c2c": "Erase Displayed Memory (EDM)",
    "1cae": "Erase Non-displayed Memory (ENM)",
    "1c2f": "End Of Caption (EOC)",
    "1ca1": "BackSpace (BS)",
    "1ca4": "Delete to End of Row (DER)",
    "1cad": "Carriage Return (CR)",
    "1ca8": "Flash ON (FON)",
    # Channel 3
    "1520": "Resume Caption Loading (RCL)",
    "1529": "Resume Direct Captioning (RDC)",
    "1525": "Roll-Up 2 Lines (RU2)",
    "1526": "Roll-Up 3 Lines (RU3)",
    "15a7": "Roll-Up 4 Lines (RU4)",
    "152a": "Text Restart (TR)",
    "15ab": "Resume Text Display (RTD)",
    "152c": "Erase Displayed Memory (EDM)",
    "15ae": "Erase Non-displayed Memory (ENM)",
    "152f": "End Of Caption (EOC)",
    "15a1": "BackSpace (BS)",
    "15a4": "Delete to End of Row (DER)",
    "15ad": "Carriage Return (CR)",
    "15a8": "Flash ON (FON)",
    # Channel 4
    "9d20": "Resume Caption Loading (RCL)",
    "9d29": "Resume Direct Captioning (RDC)",
    "9d25": "Roll-Up 2 Lines (RU2)",
    "9d26": "Roll-Up 3 Lines (RU3)",
    "9da7": "Roll-Up 4 Lines (RU4)",
    "9d2a": "Text Restart (TR)",
    "9dab": "Resume Text Display (RTD)",
    "9d2c": "Erase Displayed Memory (EDM)",
    "9dae": "Erase Non-displayed Memory (ENM)",
    "9d2f": "End Of Caption (EOC)",
    "9da1": "BackSpace (BS)",
    "9da4": "Delete to End of Row (DER)",
    "9dad": "Carriage Return (CR)",
    "9da8": "Flash ON (FON)",
}

TAB_OFFSETS = {
    "97a1": "Tab Offset 1 column (TO1)",
    "1fa1": "Tab Offset 1 column (TO1)",
    "97a2": "Tab Offset 2 columns (TO2)",
    "1fa2": "Tab Offset 2 columns (TO2)",
    "9723": "Tab Offset 3 columns (TO3)",
    "1f23": "Tab Offset 3 columns (TO3)",
}


def test_all_control_commands():
    passed = 0
    failed = 0

    for code, _ in CONTROL_COMMANDS.items():
        evt = parse_scc_code(code)
        if evt["type"] != "CONTROL":
            print(f"[FAIL] {code}: Expected CONTROL, got {evt['type']}")
            failed += 1
            continue

        if "name" not in evt:
            print(f"[FAIL] {code}: Missing 'name' field")
            failed += 1
            continue

        passed += 1

    return passed, failed


def test_all_tab_offsets():
    passed = 0
    failed = 0

    for code, _ in TAB_OFFSETS.items():
        evt = parse_scc_code(code)
        if evt["type"] != "INDENT":
            print(f"[FAIL] {code}: Expected INDENT, got {evt['type']}")
            failed += 1
            continue

        if "spaces" not in evt:
            print(f"[FAIL] {code}: Missing 'spaces' field")
            failed += 1
            continue

        passed += 1

    return passed, failed


if __name__ == "__main__":
    print("=== Control Command Tests ===\n")

    print("--- Testing Control Commands ---")
    p1, f1 = test_all_control_commands()
    print(f"Control Commands: {p1} passed, {f1} failed")

    print("\n--- Testing Tab Offsets ---")
    p2, f2 = test_all_tab_offsets()
    print(f"Tab Offsets: {p2} passed, {f2} failed")

    total_passed = p1 + p2
    total_failed = f1 + f2
    total = total_passed + total_failed

    print("\n" + "=" * 50)
    print(f"Results: {total_passed} passed, {total_failed} failed")
    print(f"Total: {total} tests")
    print("=" * 50)

    if total_failed == 0:
        print("\n✓ All control command tests passed!")
    else:
        print(f"\n✗ {total_failed} test(s) failed!")
