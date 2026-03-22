# Project Context

- **Owner:** ersabine
- **Project:** wedgeMatrix — Golf launch monitor analytics app with percentile-based club/wedge matrices and pocket card printing
- **Stack:** Python 3.11+, Flask, SQLite/SQLAlchemy, Pandas/NumPy, Bootstrap 5, Chart.js
- **Created:** 2026-03-14

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-14 — Complete test suite built (79 tests)

**Files created:**
- `tests/__init__.py` — package init
- `tests/conftest.py` — shared fixtures (Flask app, in-memory SQLite, sample data, seeded club_lofts)
- `tests/test_csv_parser.py` — 27 tests (header, direction, club names, real CSV integration, malformed)
- `tests/test_analytics.py` — 10 tests (percentile math, exclusion, errant flagging, per-club stats)
- `tests/test_club_matrix.py` — 9 tests (basic, ordering, scope, exclusions, rounding, empty, percentile)
- `tests/test_wedge_matrix.py` — 7 tests (AW/SW/LW only, fraction vs clock display, empty cell, exclusions)
- `tests/test_loft_analysis.py` — 12 tests (good/bad assessment, per-club %, exclusions, edge cases) [14 total with parametrize]

**Edge cases discovered from real CSV data:**
- `NaN` appears in Landing Angle for G-Wedge shots → direction parser must handle it
- Dynamic Loft = 0.0 appears in real data for some wedge shots (Club Path/Face Angle also zero)
- Side Spin column uses L/R prefix *and* a leading sign character (e.g., `L2908`, `R928`)
- Offline uses L/R prefix (e.g., `L10.0`, `R22.1`) — same parsing as Launch Direction
- The CSV header column has a leading space: `" Dynamic Loft"` not `"Dynamic Loft"`
- Clevelands file has no Driver or 3 Wood; Esabine has no 7 Iron or 3 Hybrid
- Carry = 0.7 and 0.5 appear for duffed shots — must not crash percentile calcs

**Key design patterns:**
- All percentile assertions verified against `numpy.percentile()` as ground truth
- Real CSV paths wired as session-scoped fixtures for integration tests
- Per-test in-memory SQLite ensures isolation (no cross-test bleed)
- `_make_shot()` helper in conftest reduces boilerplate across all test modules
- Tests are structured to be flexible on return format (dict vs list) for wedge matrix

### 2026-03-20 — Chart endpoint & percentile flow tests (29 tests)

**File created:**
- `tests/test_chart_endpoints.py` — 29 tests across 3 classes

**Test coverage:**
- `TestChartEndpointsReturnData` (8 tests): launch-spin-stability, radar-comparison, carry-distribution, dispersion, spin-carry, shot-shape, club-comparison, unknown chart 404
- `TestPercentileParameterFlow` (7 tests): P50 vs P90 carry distribution, club matrix accepts/changes with percentile, wedge matrix accepts percentile, default P75, launch-spin accepts percentile, radar accepts percentile
- `TestEdgeCases` (14 tests): no shots, single shot, 0 and 100 percentile, multi-club selection, empty club/wedge matrix, all-excluded shots, launch-spin 3-shot minimum

**Response shape discoveries:**
- `launch_spin_stability` returns `{'clubs': {club: {spin, launch, ...}}, 'correlation': ''}` — keys are `spin`/`launch`, not `spin_rate`/`launch_angle`
- `radar_comparison` returns `{'axes': [...], 'user': {values, raw}, 'pga': {values, raw}}` — flat structure, not per-club
- `club_matrix` returns `{'matrix': [list of dicts]}` — matrix is a list, not a dict
- These shape differences from the service function return values indicate the route handlers transform the data before jsonify

**Key patterns:**
- Needed a `routed_app` fixture that calls `register_routes(app)` — the existing conftest `app` fixture creates a bare Flask app without routes
- Used `_seed_multi_club_shots()` helper with 5 shots per club (7i, PW, 1W) — enough to satisfy the 3-shot minimum for box plots
- P0/P100 percentiles don't crash numpy — verified as safe boundary values
- 3 pre-existing failures in `test_loft_analysis.py` are unrelated to this work

### 2026-03-20 — Fenster & McManus Updates (Cross-Agent Note)
- Fenster fixed chart API response formats (launch-spin-stability, radar-comparison) for correct percentile passthrough
- McManus updated print card links to forward percentile params, removed header title, reduced width 5%
- These fixes enable our test cases to validate full percentile flow through all layers

### 2026-03-22 — Tests for TODO 61/62/63 (28 new tests, 133 total passing)

**File created:**
- `tests/test_new_features.py` — 28 tests across 12 classes

**Files updated (to match Fenster's implementations):**
- `tests/conftest.py` — Updated `wedge_shots` fixture: swing sizes `4/4→3/3`, `3/4→3/3`, `2/4→2/3`, `1/4→1/3`
- `tests/test_wedge_matrix.py` — Updated constants, fixtures, and assertions for new swing names + PW inclusion
- `tests/test_chart_endpoints.py` — Updated `_seed_wedge_shots` helper with new swing size labels

**Test coverage by feature:**

TODO 61 (test-data sessions): 13 tests
- Session.is_test column exists and defaults False
- Toggle endpoint (on/off/nonexistent 404)
- Test sessions excluded from analytics, shots, club matrix, wedge matrix
- `include_test=true` param re-includes test data
- Full round-trip: toggle on → excluded → toggle off → included

TODO 62 (swing size renames): 6 tests
- "4/4" absent from swing_sizes and matrix keys
- "3/3", "2/3", "1/3" present (old names absent)
- Old-label mapping: shots stored as "3/4" appear under "3/3"
- Fraction sizes precede clock sizes in order
- API endpoint reflects new names

TODO 63 (PW in wedge matrix): 7 tests
- PW in clubs list, data computed with percentile logic
- Column order: PW, AW, SW, LW
- P50 vs P90 verified against numpy
- API includes PW, PW clock swings have carry/max

Combined: 2 tests
- PW + new swing sizes work together
- Full matrix shape validation

**Key findings:**
- Fenster already implemented TODO 62 and 63 (wedge_matrix.py has PW, new swing names, SWING_RENAME mapping)
- Fenster added is_test column and toggle route for TODO 61
- All 28 new tests pass, all 105 existing tests still pass (same 3 pre-existing loft failures)
- Existing wedge tests updated: old assertions about "PW not in matrix" and "8 swing sizes" corrected
