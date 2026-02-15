# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Initial public release
- SCC file parsing and decoding
- Real-time tooltip display on hover
- Buffer state visualization
- Error detection (parity errors, invalid timestamps, CC buffer overflow)
- Timecode calculations with frame rate detection
- Inline annotations showing decoded caption text
- Caption display timing (start/end times in annotations)
- Test suite

### Features
- Hover tooltips showing:
  - Decoded command/text
  - Timestamp with packet offset
  - Current buffer state with highlighting
- Visual indicators for:
  - Parity errors (red box)
  - Invalid codes (red squiggle)
  - CC buffer overflow (red squiggle)
  - Paired codes (green box)
- Inline annotations displaying decoded captions with start/end times
- Automatic frame rate detection (23.98, 25, 29.97 NDF, 29.97 DF)

### Limitations
- Pop-on captions only (roll-up not fully tested)
- Other frame rates not yet implemented

## [1.0.0] - 2026-02-14

Initial release - Pop-on captions only
