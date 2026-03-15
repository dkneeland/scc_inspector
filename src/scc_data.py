# -*- coding: utf-8 -*-
"""
SCC Data Module

Loads shared EIA-608 data from scc-core/data/ JSON files.
This module provides a single source of truth for both Python and TypeScript implementations.
Compatible with Python 2.7 and Python 3.x.
"""

import json
import os
import io

_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'scc-core', 'data')


def _load_json(filename):
    """Load a JSON file from the data directory."""
    filepath = os.path.join(_DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise IOError("Shared data file not found: {0}\nEnsure scc-core/data/ directory exists with JSON files.".format(filepath))
    with io.open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


_char_map_data = _load_json('char_map.json')
CHAR_MAP = _char_map_data['charString']

_parity_data = _load_json('parity_table.json')
VALID_BYTES = frozenset(_parity_data['validBytes'])

_colors_data = _load_json('colors.json')
COLOR_LIST = tuple(_colors_data['colors'])

_row_map_data = _load_json('row_map.json')
ROW_MAP = _row_map_data['map']

_commands_data = _load_json('control_commands.json')
COMMAND_NAMES = {}
for hex_key, value in _commands_data['commands'].items():
    byte_val = int(hex_key, 16)
    COMMAND_NAMES[byte_val] = value['description']

_frame_rates_data = _load_json('frame_rates.json')
FRAME_RATES = _frame_rates_data['frameRates']
DROP_FRAME_RULES = _frame_rates_data['dropFrameRules']
DETECTION_RULES = _frame_rates_data['detectionRules']


def get_frame_rate_config(frame_rate_str):
    """Get frame rate configuration by name.

    Returns dict with: videoFps, isDropFrame, cadence, maxFrame, description
    Raises ValueError if frame rate not found.
    """
    if frame_rate_str not in FRAME_RATES:
        raise ValueError("Invalid frame rate: {0}".format(frame_rate_str))
    return FRAME_RATES[frame_rate_str]
