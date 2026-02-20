# Performance Analysis

## Test File
- **File**: DowntonAbbeyOnMasterpiece_S5_E4503_CB_Edit23822_Acquisition_CC-en.scc
- **Lines**: 5,460
- **Words/Codes**: 25,739
- **Annotations**: 1,285
- **Timestamps**: 2,729

## Load Time Breakdown

| Operation | Time | % of Total | Notes |
|-----------|------|------------|-------|
| Time map building | 0.25s | 11% | Single-pass state machine to track caption display times |
| Highlighting | 0.75s | 33% | Drawing indicators (error squiggles, pair boxes, parity boxes) |
| Error detection | 0.75s | 33% | Parity errors + overflow detection (scans forward 100 lines per line) |
| Annotations | 0.50s | 22% | Rendering decoded caption text below each line |
| **TOTAL** | **2.25s** | **100%** | |

## Python vs Notepad++ Overhead

- **Pure Python decoding**: ~0.18s (fast)
- **Notepad++ UI operations**: ~2.07s (the bottleneck)

The Python code itself is efficient. The slowdown comes from Notepad++ API calls:
- `editor.indicatorClearRange()` / `indicatorFillRange()` - called for every line
- `editor.annotationSetText()` / `annotationSetStyles()` - called 1,285 times
- `editor.getLine()` - called 5,460+ times (multiple passes)

## Optimization Opportunities

### High Impact (0.75s+ savings each)

1. **Defer error detection** (saves 0.75s)
   - Skip overflow detection on load
   - Run on-demand (first hover, manual trigger, or background after load)
   - Overflow check is expensive: scans forward 100 lines for each line

2. **Lazy-load annotations** (saves 0.5s)
   - Only render annotations for visible lines
   - Update as user scrolls
   - Still decode on load, just defer rendering

3. **Optimize highlighting** (saves 0.75s)
   - Batch indicator operations
   - Skip clearing indicators if not previously set
   - Consider reducing indicator types

### Medium Impact (0.25s savings)

4. **Optimize time map building** (saves 0.25s)
   - Already single-pass, but could cache results
   - Consider making optional if annotations are disabled

### Low Impact

5. **Make features optional**
   - Add config to disable expensive features
   - User can choose speed vs functionality

## Recommended Approach

**Phase 1: Quick wins (target: <1s load time)**
- Defer error detection to after load
- Make annotations lazy-loaded

**Phase 2: Further optimization (target: <0.5s load time)**
- Optimize highlighting with batched operations
- Make time map building optional

**Phase 3: Advanced (target: instant load)**
- Background processing after initial display
- Incremental updates on edit
