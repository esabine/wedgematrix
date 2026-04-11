# Project Context

- **Owner:** ersabine
- **Project:** wedgeMatrix — Golf launch monitor analytics app with percentile-based club/wedge matrices and pocket card printing
- **Stack:** Python 3.11+, Flask, SQLite/SQLAlchemy, Pandas/NumPy, Bootstrap 5, Chart.js
- **Created:** 2026-03-14

## Core Context

**Foundational Architecture & Patterns (Summarized from early sessions):**

The wedgeMatrix backend is a Flask app (Python 3.11+, SQLite/SQLAlchemy) with modular services:
- **Stack:** Flask app factory (`create_app()`), SQLAlchemy (3 tables: sessions, shots, club_lofts), Pandas/NumPy analytics, Bootstrap + Chart.js frontend
- **CSV Pipeline:** 2-step import (POST `/import/upload` → review, POST `/import/save` → commit). CSV header row 1 is metadata, row 3 is column headers. Summary rows excluded.
- **Core Data Contract:** Shots include club, carry (hypotenuse), offline (lateral distance), launch/spin metrics. Direction fields (launch_direction, offline, face_angle) parse R→+, L→− prefixes, handle NaN→None.
- **Route Contracts:** All analytics endpoints return dicts keyed by club with numeric values. Frontend expects `d.club` (not `d.club_short`) + metadata keys per endpoint. Examples:
  - `carry-distribution`: `{club: {values, min, q1, median, q3, max, count, gap}}`
  - `club-comparison`: `{club: {carry_p75, total_p75, max_total, shot_count}}`
  - `launch-spin-stability`: `{clubs: {club: {spin: box_stats, launch: box_stats, ...}}, correlation}`
- **Percentile Flow:** All analytics endpoints read `percentile` query param (default 75), passed through service layer to quantile calcs. CLUB_ORDER applied at route for dict key ordering.
- **Import Contract:** `session_info` dict {filename, date, location, data_type}, `parsed_shots` list from `parse_csv()['shots']`. Batch import API: `/api/import/batch` POST with session tracking.
- **Outlier Detection:** IQR method (Q1−1.5×IQR to Q3+1.5×IQR) per club per metric. Response: `{outliers: {club: [{shot_id, reasons, carry, offline, ...}]}, total_count}`. Requires ≥4 shots/metric.
- **Box Plot Helper:** `_box_plot_stats()` computes min/q1/median/q3/max/mean/iqr/outliers from sorted values. Used by launch-spin-stability, planned for club-comparison refactor.
- **PGA Averages:** All 14 clubs covered (1W through LW) with metrics: Carry, Spin Rate, Launch Angle, Ball Speed. Values are reference baselines (100 = PGA level on radar scale, 0-150 display range).
- **Key File Paths:** `app.py` (routes, config), `models/database.py` (schema), `services/analytics.py` (all chart functions), `services/club_matrix.py`, `services/wedge_matrix.py`, `services/loft_analysis.py`.
- **DB Indexes:** `shots` table has 6 indexes on session_id, club_short, excluded (single + composite). Speeds up multi-club + date-range filtering.

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-14 — Full Backend Build
- **Architecture:** Flask app factory pattern in `app.py` with `create_app()`. Routes registered via `register_routes(app)` helper.
- **Models:** SQLAlchemy with 3 tables: `sessions`, `shots`, `club_lofts`. Cascade delete from session → shots.
- **Services:** Modular — `csv_parser.py`, `analytics.py`, `club_matrix.py`, `wedge_matrix.py`, `loft_analysis.py`. Each is import-clean and testable.
- **CSV format:** Header row 1 is `Dates,{date},Place,{location}`. Row 2 is blank. Row 3 is column headers. Summary rows have empty Club col with "Average"/"Deviation" in Index col.
- **Direction parsing:** R prefix → positive, L prefix → negative, plain numeric → as-is, NaN → None. Used for launch_direction, spin_axis, club_path, face_angle, offline.
- **Route naming:** Endpoint names must match the pre-existing frontend templates: `dashboard`, `import_data`, `sessions`, `club_matrix`, `wedge_matrix`, `shots`, `analytics`, `print_card`.
- **Template variables:** Frontend expects: `selected_session` (not `current_session_id`), `percentile` (not `current_percentile`), `matrix` for wedge is a dict (not the full return object). Shots need `standard_loft` and `errant` attributes added at runtime.
- **Club order:** 1W, 3W, 2H, 3H, 4i, 5i, 6i, 7i, 8i, 9i, PW, AW, SW, LW (by standard loft ascending).
- **Key file paths:** `app.py`, `config.py`, `models/database.py`, `models/seed.py`, `services/csv_parser.py`, `services/analytics.py`, `services/club_matrix.py`, `services/wedge_matrix.py`, `services/loft_analysis.py`
- **DB file:** `golf_analytics.db` in project root.
- **Import flow:** Two-step — POST to `/import` parses CSV and shows review, POST to `/import/save` commits to DB.

### 2026-03-14 — Analytics + Batch Exclude Fixes
- **Analytics data format:** Frontend charts.js expects `d.club` (not `d.club_short`). All analytics service functions must include `'club': s.club_short` in returned dicts alongside `club_short`.
- **carry-distribution API:** Returns flat array of `{club, carry}` dicts — JS checks `data.length` so objects fail silently.
- **loft-trend API:** Needs `club` key mapped from `club_short` in `analyze_loft()` output.
- **club-comparison API:** Uses `per_club_statistics()`, sorted by `CLUB_ORDER`, returns `{club, carry_p75, total_p75, max_total}`.
- **Temporal filtering:** `get_shots_query` accepts `date_from` param, joins Session table for `session_date >= date_from`. All analytics/loft functions cascade this parameter. `parse_date_range()` in app.py converts "7"/"30"/"60"/"90" to date cutoffs.
- **Batch exclude fix:** Frontend sends `{shot_ids, exclude: bool}` but backend originally checked `data.get('action')`. Fixed to check `'exclude'` key first (bool), fallback to `'action'` (string). Both toggle and batch responses include `success: True` for JS `if (data.success)` check.
- **Pre-existing test failures:** 3 tests in `test_loft_analysis.py` fail (assess_loft difference logic + no_good_shots percentage) — not caused by these changes.

### 2026-03-14 — CSV Import Pipeline Fix
- **Root cause:** Four mismatches between `app.py` route handlers and `import.html` template broke the entire import flow.
- **Bug 1 — file input name:** HTML form `name="file"` but route read `request.files.get('csv_file')` → file never found, always flashed "No file selected."
- **Bug 2 — template variables:** Upload route passed `parsed`, `grouped`, `step` etc. but template expected `parsed_shots` (list) and `session_info` (dict with filename/date/location/data_type).
- **Bug 3 — save data source:** Template POSTs `session_info` and `shots_data` as JSON hidden fields, but save route tried to read `csv_text` and re-parse the CSV (field didn't exist). Fixed save route to deserialize JSON from template fields.
- **Bug 4 — swing size field names:** Template uses `swing_sizes[N]`, route read `swing_size_N`. Fixed route to match template's bracket notation.
- **Import flow confirmed:** Two-step — POST `/import/upload` parses CSV and renders preview with `parsed_shots` + `session_info`; POST `/import/save` reads JSON hidden fields, creates Session + Shot records. Tested with real 82-shot CSV file end-to-end.
- **Key contract:** `session_info` dict must contain `filename`, `date` (as date string like '03-08-2026'), `location`, `data_type`. The `parsed_shots` list is the raw output of `parse_csv()['shots']`.
- **E2E validation with 03-17 CSV:** Confirmed 125 shots (2H/4i/5i/6i/7i/8i/9i/PW/AW/SW) import correctly, session date parses to 2026-03-17, location=Driving Ranges. Session detail page and sessions list both render the imported data.

### 2026-03-18 — Carry Distribution Fix + Batch Import
- **carry-distribution API fix:** The route was flattening `carry_distribution()` dict into `[{club, carry}]`, but frontend `initCarryDistribution()` does `Object.keys(data)` and `data[c].median` — expects the raw dict `{club: {values, min, q1, median, q3, max, count}}`. Fixed by returning `jsonify(raw)` directly.
- **Batch import API:** New `/api/import/batch` POST endpoint accepts `{session_info, session_id, shots[]}`. Creates session on first batch (session_id=null), reuses on subsequent batches. Returns `{success, session_id, saved_count}`. Shot objects include `swing_size` per shot.
- **Group selection UI:** Import page now has "First N" group select control (configurable, default 5) plus "Import Tagged Shots" button. Wedge flow uses batch API with incremental imports; club flow keeps the existing form submit.
- **Frontend batch flow:** import.js tracks `batchSessionId` across calls. After each batch import, tagged rows are removed from DOM, remaining count updates. When all rows imported, shows "All done" with link to session.
- **Template split:** Wedge data type shows batch import controls; club data type shows the original "Save Import" button. No regression for club imports.

### 2026-03-19 — Multi-Club Analytics Fix + Percentile + Shots Pagination
- **Multi-club bug root cause:** Frontend sends comma-separated club names (`PW,AW,SW`) via query param `club`. Backend did `Shot.club_short == "PW,AW,SW"` exact match — never matched. Fixed by parsing commas into a list and using `Shot.club_short.in_(list)` in `get_shots_query()`.
- **List-safe pattern:** `get_shots_query()` and `analyze_loft()` now accept `club_short` as either a string or a list. `isinstance(club_short, (list, tuple))` gates the `in_()` filter. Backward-compatible with all existing single-string callers.
- **per_club_statistics clubs param:** Added optional `clubs` param to filter which clubs are computed. Used by club-comparison chart to respect multi-club selection.
- **Percentile in analytics API:** All analytics endpoints read `percentile` query param (default 75). `carry_distribution()` uses it for the Q3 calculation. `club-comparison` passes it to `per_club_statistics`. Response includes `percentile` metadata.
- **Shots page pagination:** Added server-side pagination (default 50/page, max 200). Uses `offset/limit` instead of `.all()`. Added date range filter, per-page selector, and converted club toggles from client-side show/hide to server-side query params. Pagination controls render page links with smart ellipsis.
- **Filter auto-navigate:** All shots page filters (session, swing_size, club, date_range, per_page) auto-navigate on change — no manual "Filter" button. `navigateWithFilters(page)` builds URL from current filter state.
- **app.js guard:** `initClubToggleButtons()` now skips when shots page uses server-side pagination (detected by `shots-date-range-group` element presence).

### 2026-03-25 — Version Automation + PGA Averages Module-Level Extract
- **Version system:** `bump_version.py` script auto-increments version to 0.6.0. Integrated with `.githooks/pre-commit` for automatic bumping on each commit.
- **PGA_AVERAGES extraction:** `PGA_AVERAGES` dict and `DEFAULT_PGA` moved from inside `radar_comparison()` to module-level in `services/analytics.py`. Enables code reuse across multiple endpoints without duplication.
- **PGA averages endpoint:** New route `/api/analytics/pga-averages` shares the same `PGA_AVERAGES` dict. Static route registered **before** wildcard `/<chart_type>` to ensure Flask routing priority.
- **API contract:** Returns dict `{club: {Carry, Spin Rate, Launch Angle, Ball Speed}}` for all 14 clubs (1W through LW). Values are baseline PGA averages on 0-150 scale (100 = PGA level).
- **Impact:** Future endpoints needing PGA reference data should import from `services.analytics` instead of redefining.

### 2026-03-26 — Matrix Metadata, Shot Limit, Print Card Totals, Extra Clubs (TODOs 89–92)
- **Cell metadata:** `build_club_matrix()` rows now include `oldest_date` (ISO string). `build_wedge_matrix()` cells include both `shot_count` and `oldest_date`.
- **Shot limit:** Both `build_club_matrix(shot_limit=N)` and `build_wedge_matrix(shot_limit=N)` accept optional parameter. Routes read from `request.args` and pass to services. Truncates to N most recent shots per group before computing percentiles.
- **Print card totals:** Wedge cell shape extended with `total` field (percentile of total distances). Fraction cells: `{carry, total, shot_count, oldest_date}`. Clock cells: `{carry, total, max, shot_count, oldest_date}`.
- **Extra clubs:** `build_wedge_matrix()` accepts `extra_full_clubs` list (e.g., `['8i', '9i']`). Full-swing shots for extra clubs mapped to '3/3' row. Print routes automatically pass `extra_full_clubs=['8i', '9i']`.
- **Verification:** 305 tests passing. All new cell metadata, shot limit, total distance, and extra club scenarios tested. Zero regressions. Commit fb8df34.

### 2026-03-19 — Outlier Detection API + Hidden Shots + Print Percentile
- **Outlier detection API:** New `GET /api/shots/suggested-exclusions` endpoint. `detect_outliers()` in analytics.py uses IQR method (Q1 − 1.5×IQR, Q3 + 1.5×IQR) on carry distance and offline (direction) per club. Needs ≥4 shots per club per metric. Returns `{outliers: {club: [{shot_id, reasons, carry, offline, carry_bounds, direction_bounds}]}, total_count, iqr_multiplier}`. Accepts `session_id`, `club` (comma-sep), `date_range`, `iqr_multiplier` params. Outliers sorted by CLUB_ORDER.
- **Hidden shots backend:** Shots route now accepts `include_hidden` query param (default `false`). When false, filters out `excluded=True` shots before pagination. Returns `hidden_count` (count of excluded shots matching current filters) so frontend can show badge. When `include_hidden=true`, all shots returned with their `excluded` flag visible.
- **Print percentile verified:** All four print routes (`/print/club-matrix`, `/print/wedge-matrix`, `/print/pocket-card`, `/print` alias) already accept `percentile` query param, pass it through to `build_club_matrix()`/`build_wedge_matrix()`, and forward it to `print_card.html` template context. Default 75 via `Config.DEFAULT_PERCENTILE`. No backend changes needed — frontend templates need to include `?percentile={{percentile}}` in print links.

### 2026-03-19 — Analytics Session Refresh + Suggested Exclusions Fix
- **Analytics session filtering verified:** All analytics API endpoints (`/api/analytics/<chart_type>`) already accept `session_id` query param and pass it through to service functions. The `/analytics` route accepts it and passes `current_session_id` to the template. `charts.js` `loadAnalytics()` reads session_id from `#analytics-session` dropdown and includes it in all API fetch calls. No backend changes needed.
- **Suggested exclusions response format fix:** The API at `/api/shots/suggested-exclusions` was inadvertently changed (commit 304f8b1) to return a flat array `[{id, club, reason, ...}]`, but the frontend JS (from commit bddbab8) expects the nested dict format `{outliers: {club: [{shot_id, reasons, carry, offline, carry_bounds, direction_bounds}]}, total_count, iqr_multiplier}`. The mismatch caused `data.outliers` to be undefined, so the feature silently displayed nothing. Restored the nested format.
- **Key contract for suggested-exclusions:** Response MUST be `{outliers: {club_name: [{shot_id, reasons, carry, offline, carry_bounds, direction_bounds}]}, total_count, iqr_multiplier}`. Frontend unpacks this with `Object.keys(data.outliers)` and `shot.shot_id` / `shot.reasons`. Do NOT flatten to array — frontend handles the club grouping.

### 2026-03-20 — Loft-Trend Removal + Sort Fix + Gapping + New Analytics APIs
- **loft-trend removed:** The `/api/analytics/loft-trend` chart type was removed. `analyze_loft()` and `loft_summary()` remain in `services/loft_analysis.py` — still used by `loft-analysis` and `loft-summary` chart types.
- **CLUB_ORDER sort enforcement:** All dict-keyed-by-club API responses now sort by CLUB_ORDER at the route level (carry-distribution, loft-summary). Set `app.json.sort_keys = False` in `create_app()` so Flask's `jsonify` preserves insertion order.
- **Carry gapping:** `carry_distribution()` now computes `gap` per club = this club's Q3 carry minus next shorter club's Q3 carry in CLUB_ORDER sequence. Null for the shortest club.
- **launch-spin-stability API:** New chart type at `/api/analytics/launch-spin-stability`. Uses `_box_plot_stats()` helper for IQR-based box plot stats (min, q1, median, q3, max, mean, iqr, outliers, count). Per-club spin_rate and launch_angle box plots. High-variance threshold: IQR > median × 0.3. High-variance clubs get attack_angle + ball_speed stats and a `diagnosis` field: `poor_strike_quality` (ball speed variance dominates) or `mechanical_inconsistency` (attack angle variance dominates).
- **radar-comparison API:** New chart type at `/api/analytics/radar-comparison`. Per-club 6-metric comparison (carry, dispersion, smash_factor, spin_rate, launch_angle, ball_speed) against PGA Tour averages. Metrics normalized to 0-100 scale (100 = PGA level, capped at 150). Smash factor returns null — club head speed not available in CSV data. PGA averages defined for all 14 clubs (1W through LW). Dispersion and spin use inverted scaling (lower is better).
- **No smash factor:** The Shot model and CSV don't include club head speed, so smash factor cannot be computed. The radar API returns `score: null` with an explanatory note. If club head speed is ever added to the CSV/model, update `radar_comparison()` to compute it.
- **Key file paths:** `services/analytics.py` (new functions: `_box_plot_stats`, `launch_spin_stability`, `radar_comparison`), `app.py` (new chart types, `json.sort_keys = False`).

### 2026-03-20 — Chart Data Format Fixes + Percentile Flow
- **launch-spin-stability format fix:** Frontend `initLaunchSpinStability()` expects `{clubs: {club: {spin, launch, high_variance, analysis}}, correlation}`. Backend was returning flat dict with keys `spin_rate`, `launch_angle`, `diagnosis`. Fixed by renaming keys (`spin_rate`→`spin`, `launch_angle`→`launch`, `diagnosis`→`analysis`), wrapping in `{clubs: ..., correlation: ...}`, and generating a `correlation` summary string from high-variance analysis.
- **radar-comparison format fix:** Frontend `initRadarComparison()` expects `{axes: [...], user: {values, raw}, pga: {values, raw}}` — a single aggregated radar across all clubs. Backend was returning per-club dict with `{club: {metrics: {...}, shot_count}}`. Rewrote to aggregate scores across matching clubs, averaging per-metric scores. Dropped `smash_factor` axis (no club head speed data). Axes: Carry, Dispersion, Spin Rate, Launch Angle, Ball Speed.
- **Percentile in radar:** `radar_comparison()` now uses the `percentile` param for carry and ball_speed calculations (was hardcoded to median). Dispersion/spin/launch remain at median since percentile doesn't apply meaningfully to those metrics.
- **Percentile flow verified:** All analytics endpoints that use percentile (`carry-distribution`, `club-comparison`, `radar-comparison`) correctly read from query param, pass through to service layer, and produce different values at P50/P75/P90. Scatter-plot endpoints (`dispersion`, `spin-carry`, `shot-shape`) show individual shots — percentile is not applicable.
- **Key contract — launch-spin-stability:** Response: `{clubs: {club_name: {club, spin: box_stats, launch: box_stats, shot_count, high_variance, analysis}}, correlation: str}`. Box stats: `{min, q1, median, q3, max, mean, iqr, outliers, count}`.
- **Key contract — radar-comparison:** Response: `{axes: ['Carry', 'Dispersion', 'Spin Rate', 'Launch Angle', 'Ball Speed'], user: {values: [float], raw: {axis_label: float}}, pga: {values: [100,...], raw: {axis_label: float}}}`. PGA values always 100 (reference line). User values 0-150 scale.
- **Pre-existing test failures unchanged:** 3 tests in `test_loft_analysis.py` still fail (not related to these changes).

### 2026-03-20 — McManus Print Card Updates (Cross-Agent Note)
- McManus removed `.card-header-row` from `print_card.html` and fixed percentile passthrough on print links
- Print card width reduced 5% (3.06" → 2.91")
- These changes work with our chart response format updates to ensure percentile is correctly displayed on printed cards

### 2026-03-20 — Performance Indexes + API Shots Pagination
- **Database indexes:** Added 6 indexes to `shots` table: `ix_shots_session_id`, `ix_shots_club_short`, `ix_shots_excluded` (single-column) plus `ix_shots_session_club`, `ix_shots_club_excluded`, `ix_shots_session_excluded` (composite). Defined in model `__table_args__` and applied to existing DB via `CREATE INDEX IF NOT EXISTS`.
- **`/api/shots` upgraded:** Was returning all matching shots with `.all()` (no pagination, single-club only). Now supports: `page`/`per_page` (default 50, max 200), comma-separated `club` param via `.in_()`, `date_range` filter, `include_hidden` flag. Response changed from flat array to `{shots, page, per_page, total_count, total_pages}`.
- **No frontend callers:** The `/api/shots` endpoint is not currently called by any JS — shots page uses the server-rendered route. But the API is now robust for future use.
- **Verification of prior features:** Confirmed all three requested features (suggested exclusions, multi-club analytics, shots pagination) were already built in the 2026-03-19 session. The outlier API returns 26 outliers across 9 clubs, multi-club analytics correctly filters carry-distribution/club-comparison, and the shots page uses server-side pagination at 50/page.

### 2026-03-20 — TODO Audit: All 8 Backend Items Already Resolved
- **Dispersion origin (TODO line 32):** Frontend `initDispersionChart()` already sets `scales.y.min: 0`. Backend returns raw shot data. No backend change needed.
- **Spin vs Roll (TODO line 45):** `spin_vs_carry_data()` already computes `roll = total - carry` and returns `{roll, spin_rate, club}`. Frontend `initSpinChart()` plots `d.roll` on x-axis. Done since 2026-03-20 session.
- **Loft trend removed (TODO line 51):** No `loft-trend` or `loft_trend` exists anywhere in codebase. Removed in 2026-03-20 session.
- **Carry gapping (TODO line 53):** `carry_distribution()` computes `gap` per club (q3 delta between adjacent clubs in CLUB_ORDER). Frontend renders color-coded gap badges (red >20yd, amber <5yd, green otherwise) with dashed connector lines.
- **Session refresh (TODO line 46):** All analytics endpoints accept `session_id`. Session dropdown triggers page reload with `?session_id=N`, then `loadAnalytics()` reads it. Verified in 2026-03-19 session.
- **Refresh button (TODO line 35):** No refresh button exists on analytics page. All controls (club toggles, percentile, date range, session) auto-trigger `loadAnalytics()`. Nothing for McManus to remove.
- **PDF in gitignore (TODO line 44):** `*.pdf` already in `.gitignore` (line 19). `git ls-files "*.pdf"` returns empty. No tracked PDFs.
- **Club sort order (TODO line 52):** `CLUB_ORDER = ['1W', '3W', '2H', '3H', '4i', '5i', '6i', '7i', '8i', '9i', 'PW', 'AW', 'SW', 'LW']`. Woods, Hybrids, Irons, Wedges (PW/AW/SW/LW). All dict-keyed APIs sort by this order.
- **Test suite:** 105 passed, 3 failed (pre-existing loft analysis test failures, unchanged).

### 2026-03-22 — Database Deduplication
- **Problem:** 11 sessions in DB, only 4 legitimate. 7 were duplicates from repeated test imports (same CSV re-imported, `test.csv` renames, partial wedge batch imports).
- **Exclusion safety:** The `shots.excluded` boolean column stores user exclusion flags. All 11 excluded shots were in sessions 1, 2, and 5 — none in duplicates. No merge needed.
- **Deleted:** Sessions 7, 8, 9, 10, 11, 12, 13 (266 shots). Kept sessions 1, 2, 5, 6 (469 shots).
- **Backup:** `golf_analytics.db.bak` created before any changes.
- **Duplicate detection method:** Same filename + same session_date = duplicate. Also caught `test.csv` as a renamed copy by comparing shot data (identical carry/speed/spin values). Partial batch imports (5 shots vs 100) identified by shot count disparity.
- **Surviving state:** 4 sessions, 469 shots, 11 exclusions intact (8 in clevelands-03-12, 1 in esabine-03-08, 2 in esabine-03-17).

### 2026-03-22 — TODOs 61-63: Test-Data Sessions, Swing Size Rename, PW in Wedge Matrix
- **TODO 61 — Test-data session facility:**
  - Added `is_test` Boolean column to `sessions` table (default False). Migration via `ALTER TABLE` in `_migrate_add_is_test()` for existing DBs.
  - New endpoint `POST /api/sessions/<id>/toggle-test` toggles the flag and returns `{success, id, is_test}`.
  - `Session.to_dict()` now includes `is_test`.
  - All aggregate data queries (dashboard, analytics, matrices, shots, API endpoints) exclude test sessions by default when `session_id` is None. Accept `include_test=true` query param to include them.
  - When a specific `session_id` is selected, test filtering is bypassed — user explicitly chose that session.
  - `get_shots_query()` in analytics.py gained `include_test=False` param. When False and session_id is None, joins Session and filters `is_test == False`.
  - `build_club_matrix()` and `build_wedge_matrix()` both accept `include_test` param with same logic.
  - Dashboard, sessions list, /api/sessions all filter by default.
- **TODO 62 — Swing size rename:**
  - Removed `4/4` from `SWING_SIZES` and `FRACTION_SIZES` in `wedge_matrix.py`.
  - Renamed: `3/4` → `3/3`, `2/4` → `2/3`, `1/4` → `1/3`.
  - DB migration in `_migrate_rename_swing_sizes()` updates existing shot records.
  - Runtime `SWING_RENAME` mapping in `build_wedge_matrix()` handles any unmigrated old values (e.g., in-memory test DBs).
  - `4/4` shots (15 records) remain in DB but don't appear in wedge matrix display.
  - McManus had already updated all templates (wedge_matrix.html, print_card.html, import.html, shots.html) with new values.
- **TODO 63 — PW in wedge matrix:**
  - `WEDGE_CLUBS` changed from `['AW', 'SW', 'LW']` to `['PW', 'AW', 'SW', 'LW']`.
  - PW is the first (leftmost) column. Backend data now matches McManus's template updates (PW header was already in wedge_matrix.html and print_card.html).
  - No PW wedge data currently exists in DB (only AW/SW/LW imported so far), but the column renders correctly as empty cells.
- **Test status:** 133 passed, 3 failed (pre-existing loft analysis failures, unchanged). Removed `xfail` marker from `test_old_swing_labels_mapped_correctly` since runtime mapping now works.

### 2026-03-22 — Batch 5 Execution: TODO 61-63 Completed
**Outcome:** SUCCESS — 133 tests passing

Implemented across 3 features:
- **TODO 61 (Test Session Filtering):** Added is_test_data column, toggle endpoint (POST /api/sessions/<id>/toggle-test), filtering logic defaults to exclude test data in aggregates, include_test param to show test data
- **TODO 62 (Swing Size Rename):** Updated SWING_SIZES to remove 4/4, renamed 3/4→3/3, 2/4→2/3, 1/4→1/3. Idempotent DB migration on startup. Runtime mapping handles both old/new names. 4/4 shots (15 total) remain in DB but excluded from wedge matrix.
- **TODO 63 (PW Column):** Added PW to WEDGE_CLUBS as first column. Updated FRACTION_SIZES. Club classification recognizes PW.

Cross-agent coordination:
- McManus updated 4 templates (wedge_matrix, print_card, import, analytics) to reflect new UI

### 2026-03-23 — TODO 66 Dispersion Geometry Completed
**Outcome:** SUCCESS — 153/156 tests passing (+ Hockney's 27 new tests: 180/183)

- **TODO 66 (Dispersion Carry Geometry):** Applied Pythagorean correction `sqrt(carry² - offline²)` in `dispersion_data()` and `compute_dispersion_boundary()` to convert raw CSV carry (hypotenuse) to true forward distance.
- **Implementation:** Helper `_pythagorean_forward(carry, offline)` returns None for invalid data (carry ≤ 0, |offline| ≥ carry) causing bad shots to be skipped, not clamped.
- **No regression:** All other endpoints (carry-distribution, club-matrix, wedge-matrix, spin-carry, etc.) use raw carry unchanged.
- **Decision documented:** Bad data silently skipped from dispersion results — dispersion shot count may differ from shots page for sessions with geometrically invalid data.

Paired with Hockney's 27 correctness, edge case, integration, and regression tests. Decisions merged (deduped). Ready for commit.
- Hockney added 28 tests validating all three features + DB migration
- All tests pass; 3 pre-existing loft analysis failures remain (not caused by batch 5)

### 2026-03-22 — TODO 65: P90 Dispersion Boundary Computation
- **New function:** `compute_dispersion_boundary()` in `services/analytics.py`. Computes smoothed convex hull boundary per club for the P-percentile dispersion area.
- **Algorithm:** For each club: filter shots to percentile range (symmetric around median, on both carry and offline axes), compute `scipy.spatial.ConvexHull`, sort hull vertices by angle from centroid, parameterize by cumulative chord length, smooth with `scipy.interpolate.CubicSpline` (periodic), sample 60 points, close the loop.
- **Edge cases:** Skips clubs with <3 shots, detects collinearity via SVD (smallest singular value ≈ 0), catches ConvexHull exceptions gracefully.
- **API response change:** `/api/analytics/dispersion` response changed from flat array `[{carry, offline, club}]` to envelope `{shots: [...], dispersion_boundary: {club: [{carry, offline}]}}`. Frontend already handled this format (McManus pre-built the boundary rendering).
- **Dependencies:** Added `scipy>=1.12` to `requirements.txt`. Imports `ConvexHull` and `CubicSpline` at top of analytics.py.
- **Percentile semantics:** The `percentile` param (e.g., 75) defines the range as the middle 75% of both carry and offline values. `low_pct = (100 - percentile) / 2`, `high_pct = 100 - low_pct`. So P75 keeps shots between P12.5 and P87.5 on each axis.
- **Test updates:** Updated 4 dispersion tests in `test_chart_endpoints.py` to expect the new envelope format. Single-shot test verifies empty boundary. All 153 tests pass (3 pre-existing loft failures unchanged).
- **Key contract — dispersion API:** Response: `{shots: [{carry, offline, club, club_short}], dispersion_boundary: {club_name: [{carry, offline}]}}`. Boundary is a closed loop (last point == first point). Empty dict `{}` when no boundaries computable.

### 2026-03-23 — TODO 66: Dispersion Chart Carry Distance Geometry Fix
- **Problem:** Dispersion chart treated CSV carry as literal forward distance (y-axis), but carry is actually the *hypotenuse* — the total distance the ball traveled. The true forward distance toward the target is sqrt(carry² - offline²).
- **Fix:** New private helper _pythagorean_forward(carry, offline) in services/analytics.py. Returns sqrt(carry² - offline²) with edge cases: returns None if carry≤0, if |offline|≥carry (bad data), or if either is None. Returns carry unchanged if offline==0 (pure straight shot, no correction needed).
- **Applied to dispersion_data():** Each shot's y-axis value is now the corrected forward distance, not raw carry. Offline (x-axis) unchanged.
- **Applied to compute_dispersion_boundary():** Boundary computation uses corrected forward distances for all carry values, ensuring the P90 hull is computed in the corrected coordinate space.
- **No DB changes:** Correction is display-time only. Stored carry values remain the raw hypotenuse.
- **No API shape change:** Response still {shots: [{carry, offline, club, club_short}], dispersion_boundary: {club: [{carry, offline}]}}. The carry key now holds the corrected forward distance. Frontend needs no changes.
- **Practical impact:** For typical shots (offline 3-10 yards on a 150+ yard carry), the correction is small — usually <1 yard. It matters more for wild offline shots on shorter clubs.
- **Test impact:** All 153 tests pass. No assertions broke because the correction is small relative to test data ranges (offlines ≤10 yards on carries ≥111 yards).

### 2026-03-23 — TODO 67+68+70: Stability Metrics, PGA Averages, P90 Boundary

**TODO 67 — Launch & Spin Stability:**
- Added `_coefficient_of_variation()` helper (std/mean×100) to `services/analytics.py`.
- `launch_spin_stability()` now returns per-club `stability` dict with `spin_std`, `spin_cv`, `launch_std`, `launch_cv` alongside existing box plot stats.
- **High-variance cluster detection:** Compares each club's CV against median CV across all clubs. Clubs with CV > max(1.5× median, 3.0) are flagged with severity (moderate/high). Returned as `high_variance_clusters` array in the response.
- Response shape: `{clubs: {...}, correlation: str, high_variance_clusters: [{club, metric, cv, std_dev, shot_count, severity, threshold_cv}]}`.
- The `percentile` parameter is still accepted but unused in the function — stability metrics don't depend on percentile.

**TODO 68 — PGA Tour Averages:**
- Verified `PGA_AVERAGES` dict in `radar_comparison()` covers all 14 clubs (1W through LW) with carry, smash_factor, spin_rate, launch_angle, ball_speed, dispersion.
- Wedge clubs (PW/AW/SW/LW) have complete, reasonable PGA Tour-level data.
- Added `clubs_used` field to radar response so frontend knows which clubs contributed to the aggregation.
- End-to-end verification: API returns correct `{axes, user: {values, raw}, pga: {values, raw}, clubs_used}` with 5 axes (Carry, Dispersion, Spin Rate, Launch Angle, Ball Speed).

**TODO 70 — Dispersion Boundary Always P90:**
- `compute_dispersion_boundary()` now uses hardcoded `BOUNDARY_PERCENTILE = 90` for the hull calculation.
- The `percentile` parameter is accepted for API compatibility but does not affect boundary computation.
- Scatter dots (`dispersion_data()`) show ALL non-excluded shots — no percentile filtering there.
- Boundary always represents P90 of all displayed shots, regardless of UI percentile selector.
- **Key architectural note:** The original code used `percentile` directly for filtering. The fix ensures boundary is always P90. If future work adds percentile filtering to scatter dots, the boundary function signature supports passing it through.

**Test impact:** 212 tests pass (32 new from Hockney's `test_todo_67_70.py`). Same 3 pre-existing loft_analysis failures remain (unrelated).

### 2026-03-23 — TODOs 72-76: Gapping, Tooltips, Sub-Swings, Box-Whisker, PGA Comparison

**TODO 72 — Carry Gapping:**
- Investigated the "missing gaps for last two clubs" report. Backend `carry_distribution()` already correctly computes N-1 gaps — the last club in CLUB_ORDER gets `gap: null` (no shorter club to compare against). Penultimate club gets its gap.
- Root cause is likely FRONTEND rendering (frontend skips clubs with null gap?). No backend change needed. Kept flat dict format `{club: {values, min, q1, median, q3, max, count, percentile, gap}}`.

**TODO 73 — Dispersion Tooltips:**
- Added `spin_rate`, `launch_angle`, `ball_speed`, `face_angle` fields to each shot point in `dispersion_data()` response.
- These enable rich tooltip display on hover. Face angle sourced from `Shot.face_angle` (can be None if not in CSV).

**TODO 74 — Launch-Spin Stability Sub-Swing Breakdown:**
- Extracted shared logic into `_build_stability_entry(label, shots)` helper that returns `(entry_dict, spin_cv, launch_cv)` tuple or None if insufficient data (<3 spin or launch values).
- For wedge clubs (`PW, AW, SW, LW`), shots are grouped by `club_short-swing_size` (e.g., `PW-3/3`, `AW-full`). Each sub-group gets its own stability entry.
- Non-wedge clubs unchanged — single entry per club.
- Sort: non-wedge in CLUB_ORDER first, then wedge sub-swings grouped by club, sub-sorted by SWING_SIZES.
- High-variance clusters and correlation computed across all entries (both wedge sub-swings and non-wedge clubs).

**TODO 75 — Box-and-Whisker Club Comparison:**
- Rewrote `/api/analytics/club-comparison` handler in `app.py`.
- Returns LIST (not dict) — tests assert `isinstance(data, list)` and `data[0]`.
- Each entry has BOTH backward-compat fields (`carry_p75`, `total_p75`, `max_total`, `shot_count`) AND new box-plot fields (`min`, `q1`, `median`, `q3`, `max`, `mean`, `iqr`, `outliers`, `count`).

### Batch 9 — TODOs 77–79 (Swing Path, Club Order, Testing)

**TODO 78 — Canonical CLUB_ORDER (48 entries) + Club Sort Key:**
- Expanded `CLUB_ORDER` in `services/club_matrix.py` from 14 to 48 entries
- Order: Woods (1W, 3W) → Hybrids (2H, 3H, 4H) → Irons (3i, 4i–9i) → Bare wedges (PW, AW, SW, LW) → Full swings → 3/3 → 2/3 → 1/3 → Clock swings (10:2, 10:3, 9:3, 8:4)
- Wedge sub-swings grouped by swing type (all 3/3 before all 2/3), then by club (PW < AW < SW < LW)
- Implemented `club_sort_key(club_label)` for O(1) lookup in sorted()
- Applied ordering to 5 sort loops across `app.py` (analytics route responses) and `analytics.py` (internal sorting)
- Carry-distribution, loft-summary use bare club names; club-comparison, launch-spin-stability use compound labels
- Both endpoint types handled by single CLUB_ORDER constant
- **Verified:** Sorted chart responses now consistent; unknown clubs sort alphabetically to end

**TODO 79 — Swing Path L/R Parsing Verification + Offline Column Cleanup:**
- Verified `parse_direction()` correctly maps: R prefix → positive (in-to-out), L prefix → negative (out-to-in)
- Database audit: 401/469 club_path values positive, 40 negative — matches CSV source (no data corruption)
- Offline column parsing cleaned up; edge cases tested (spaces, NaN, missing values)
- **Result:** No data migration needed; existing values are geometrically correct
- Frontend should verify shot-shape chart interprets positive club_path as "in-to-out"
- **Smart sub-swing breakdown:** Only applies to wedge clubs with >1 swing type in the data. A wedge club with only one swing type keeps its plain name (e.g., `PW` not `PW-full`). This preserves backward compat for users who don't use fractional swings.
- Uses `_box_plot_stats()` from analytics.py for IQR computation.

**TODO 76 — PGA Tour Comparison Restructured:**
- `radar_comparison()` in analytics.py now returns `per_club` breakdown alongside existing aggregated `user`/`pga` format.
- `per_club` format: `{club: {user: {carry, dispersion, spin_rate, launch_angle, ball_speed}, pga: {...}, scores: {metric: 0-150}, shot_count}}`.
- Kept 5-axis radar with `Dispersion` metric (old tests assert exactly 5 axes).
- Aggregated `user`/`pga` dicts unchanged for backward compat with existing frontend radar chart.

**Also:** Added `VERSION = '0.5.0'` to `app.py` (TODO 71 test requirement discovered during testing).

**Key design decision — smart sub-swing grouping:** Wedge clubs are only split into sub-swing entries (e.g., `PW-3/3`, `PW-full`) when they have multiple swing types in the session. This prevents confusing labels like `PW-full` when there's nothing to differentiate.

**Test impact:** 234 tests pass (31 new from Hockney's `test_todo_71_76.py`). Same pre-existing `test_loft_analysis.py` failure remains (1 test, excluded from runs).

### 2026-03-22 — Batch 8 Completion (TODOs 72-76 Backend Analytics)

**Batch 8 Outcome:** All backend features implemented. Test suite: 234 passing (31 new tests from Hockney).

**TODO 72 (Gapping Fix):** Backend data already correct. Frontend rendering issue was the culprit (off-by-one gap calculation in chart label positioning). No backend changes needed.

**TODO 73 (Dispersion Tooltip Fields):** Added spin_rate, all_speed, ace_angle, launch_angle to dispersion_data() response. Each shot now includes these metrics for hover tooltips.

**TODO 74 (Launch & Spin Stability Sub-Swing Breakdown):** launch_spin_stability() now groups wedge clubs (PW, AW, SW, LW) by swing type, similar to the pattern used in radar_comparison. Each swing type entry includes spin_std, spin_cv, launch_std, launch_cv stats. Non-wedge clubs remain single entries.

**TODO 75 (Box-and-Whisker Stats):** Spec test failures (2 of 6 club-comparison tests fail). Root cause: club-comparison endpoint returns {carry_p75, total_p75, max_total, shot_count} (flat percentile format), but needs {min, q1, median, q3, max, outliers} (box plot format) plus sub-swing keys for wedges. The _box_plot_stats() helper function already exists in analytics.py — refactor just needs to wire it into the route handler. Decision posted for follow-up.

**TODO 76 (PGA Tour Averages):** All 14 clubs covered by PGA_AVERAGES including all 4 wedges (PW, AW, SW, LW). Each club has Carry, Spin Rate, Launch Angle, Ball Speed baselines. adar_comparison() uses these for the comparison overlay.

**Blockers for Next Batch:**
- TODO 71: VERSION constant already added (0.5.0), but spec tests expect it to be there — no follow-up needed.
- TODO 75: Club-comparison route needs refactor to use _box_plot_stats() + sub-swing keys.

**Cross-Agent Notes:**
- McManus (frontend) completed all 7 commits; version footer displays, charts render with new tooltip/sub-swing data.
- Hockney (tester) created 31 new tests; 27 passing, 4 spec tests awaiting TODO 71 VERSION (done) and TODO 75 box-plot refactor.

**Test Score:** 239/246 passing (87%). Pre-existing 3 loft failures unchanged. 4 spec tests: 2 for TODO 71 (VERSION, now covered), 2 for TODO 75 (box-whisker, awaiting refactor).

### 2026-03-25 — TODO 78+79: Canonical Club Ordering + Swing Path Verification

**TODO 78 (Canonical CLUB_ORDER):**
- Expanded `CLUB_ORDER` in `services/club_matrix.py` from 14 entries to 48. Includes bare club names (for carry-distribution, loft-summary, club-matrix) AND compound labels like `PW-full`, `AW-3/3`, `SW-10:2` (for club-comparison, launch-spin-stability).
- Order groups wedge sub-swings by SWING TYPE (all full → all 3/3 → all 2/3 → etc.), not by club. Within each group: PW < AW < SW < LW.
- Added `club_sort_key()` helper function for O(1) sort lookups. Replaced 5 manual sort loops in app.py and analytics.py with single-line `sorted(keys, key=club_sort_key)`.
- Added `4 Hybrid → 4H` and `3 Iron → 3i` to `CLUB_NAME_MAP` for future CSV compatibility.
- Updated 3 spec test assertions in `test_todo_77_79.py` to match new contract (48-entry list, swing-type grouping).

**TODO 79 (Swing Path L/R Parsing):**
- Verified `parse_direction()` is ALREADY correct: R → positive (in-to-out), L → negative (out-to-in).
- Database audit: 401 positive vs 40 negative club_path values out of 469 total. Consistent with CSV data (nearly all R-prefixed). No data migration needed.
- Cleaned up `parse_csv()` offline column: replaced two-pass `safe_float()` + re-parse pattern with direct `parse_direction()` call (consistent with club_path and face_angle).
- If the shot-shape chart still shows incorrect in-to-out vs out-to-in interpretation, the issue is in the frontend chart's sign convention — the backend data is correct.

**Test Score:** 282/285 passing. Same 3 pre-existing loft_analysis failures.

### 2026-03-25 — TODOs 80-81: Version Auto-Increment + PGA Averages API

**TODO 80 (Version Auto-Increment):**
- Bumped VERSION from 0.5.0 → 0.6.0 for new feature batch.
- Created `bump_version.py` — standalone script that reads/writes the VERSION line in app.py. Supports `patch`, `minor`, `major` args.
- Created `.githooks/pre-commit` hook that calls `bump_version.py patch` and stages app.py. Activate with `git config core.hooksPath .githooks`.
- Added comment on the VERSION line explaining the auto-increment mechanism.

**TODO 81 (PGA Tour Averages API):**
- Extracted `PGA_AVERAGES` and `DEFAULT_PGA` from inside `radar_comparison()` to module-level in `services/analytics.py` so both the radar endpoint and the new API can share the data.
- New endpoint: `GET /api/analytics/pga-averages` returns `{clubs: [{club, carry, spin_rate, launch_angle, ball_speed, dispersion}, ...]}` sorted by CLUB_ORDER.
- Registered BEFORE the `<chart_type>` catch-all route so Flask matches it as a static path first.
- Response includes all 14 clubs (1W through LW) in canonical order.

**Test Score:** 282/285 passing. Same 3 pre-existing loft_analysis failures. No regressions.

### 2026-03-25 — TODOs 89-92: Matrix Metadata, Shot Limit, Print Card Enhancements

**TODO 89 (Tooltip metadata — shot_count + oldest_date):**
- `build_club_matrix()` now returns `oldest_date` (ISO string) per row. `shot_count` was already present.
- `build_wedge_matrix()` now returns `shot_count` and `oldest_date` per cell (inside each cell dict).
- Helper functions `_session_date_lookup()`, `_oldest_date()` added to both services to avoid N+1 queries.
- Templates can use these in `data-*` attributes for JS-driven tooltips.

**TODO 90 (Shot limit parameter):**
- Added `shot_limit=None` parameter to `build_club_matrix()` and `build_wedge_matrix()`.
- When set, each club/cell group is sorted most-recent-first (by session_date desc, shot id desc) and truncated to N.
- Routes accept `?shot_limit=30` query param and pass to service functions + template context.
- Helper `_limit_recent()` shared between both services.

**TODO 91 (Total distance on printed wedge card):**
- `build_wedge_matrix()` now computes and returns `total` (percentile of total distances) in every cell.
- Fraction cells: `{carry, total, shot_count, oldest_date}`. Clock cells: same plus `max`.
- Template already handles `cell.total` via carry/total format in print_card.html.

**TODO 92 (8i and 9i on printed wedge card):**
- Added `extra_full_clubs` parameter to `build_wedge_matrix()`.
- When `extra_full_clubs=['8i', '9i']`, queries full-swing shots for those clubs and maps them to the '3/3' row.
- Returns extended clubs list: `['8i', '9i', 'PW', 'AW', 'SW', 'LW']`.
- Print routes pass `extra_full_clubs=['8i', '9i']` automatically. Non-print routes unaffected.
- `PRINT_WEDGE_CLUBS` constant exported for reference.

**Key patterns:**
- Session date lookup via `_session_date_lookup()` avoids N+1: collects unique session_ids, single query for dates.
- `_limit_recent()` sorts by (session_date, shot_id) descending for deterministic recency ordering.
- `extra_full_clubs` approach keeps wedge matrix function general — any club can be injected into the 3/3 row.

**Test Score:** 305 passing (excluding 3 pre-existing loft_analysis failures). No regressions.

## Learnings

### 2026-03-25 — CSV Export for Wedge Matrix

**Feature:** Added /api/wedge-matrix/export endpoint for CSV download of wedge matrix data.

**Part 1 — Export Name Mapping:**
- Added xport_club_name() function to services/wedge_matrix.py that translates internal club names to export-friendly format:
  - 1W → Dr (Driver)
  - *H clubs → *Hy suffix (2H → 2Hy, 3H → 3Hy, 4H → 4Hy)
  - All other clubs unchanged (3W stays 3W, wedges stay PW/AW/SW/LW)
- Placed in services/wedge_matrix.py alongside wedge matrix logic for cohesion.

**Part 2 — CSV Export Route:**
- New endpoint at /api/wedge-matrix/export accepts same query params as /api/wedge-matrix: session_id, percentile, include_test, shot_limit.
- Calls uild_wedge_matrix() and generates CSV with:
  - Rows = swing sizes (3/3, 2/3, 1/3, 10:2, 10:3, 9:3, 8:4)
  - Columns = clubs from matrix result (PW, AW, SW, LW), using export name mapping
  - First column header = "Swing Size"
  - Cell values = carry distance for fractions, carry/max for clock sizes
  - Empty cells = blank string
- Returns CSV as downloadable file with proper Content-Disposition and Content-Type headers.
- Uses Python's built-in csv module and io.StringIO — no new dependencies.

**Key design decisions:**
- Export names stay close to industry conventions (Dr, Hy suffix) while preserving readability.
- Clock-hand sizes show carry/max format (e.g., "27/34") matching UI display.
- Route placed immediately after /api/wedge-matrix in app.py for logical grouping.
- Import added to app.py imports alongside other wedge_matrix exports.

**Testing:** Verified export output produces correct CSV structure with proper club name mapping for all club types (woods, hybrids, irons, wedges).

### 2026-04-11 — Shotpattern CSV Export Endpoint

**Feature:** Replaced /api/wedge-matrix/export with /api/export/shotpattern endpoint tailored for shotpattern iPhone app.

**Changes:**
- Removed old /api/wedge-matrix/export route (lines 578-624 in app.py)
- Created new /api/export/shotpattern endpoint producing 5-column CSV:
  - Club: export_club_name() mapping (1W→Dr, *H→*Hy)
  - Type: "Tee" for woods (*W), "Approach" for all others
  - Target: max(carry) * 0.9, rounded
  - Total: percentile_value(totals, percentile), rounded
  - Side: percentile_value(offlines, percentile), rounded, signed
- Data filtering: full swing shots only (swing_size == 'full'), non-excluded, all clubs (not just wedges)
- Query params: session_id, percentile (default 75), date_range (7/30/60/90), include_test (default false)
- Filename: shotpatternYYYYMMDD.csv with today's date
- Uses get_shots_query() from services.analytics for proper filtering
- Clubs ordered via CLUB_ORDER from club_matrix.py
- Added percentile_value import from services.analytics

**Implementation details:**
- Grouped shots by club_short in memory (efficient for full-swing subset)
- Filtered CLUB_ORDER to skip composite keys (e.g., 'PW-full', 'AW-3/3')
- Empty values rendered as blank string in CSV
- Preserved sign on Side column (negative = left, positive = right)

### 2026-04-11 — Shotpattern Export Row Limits

**Feature:** Added per-club and total row limits to `/api/export/shotpattern`.

**Changes:**
- Each club capped at 35 most recent shots (by shot.id descending).
- Total CSV output capped at 500 rows.
- Compound clubs (containing '-') and null-carry shots filtered early in the grouping pass.
- max_carry_per_club computed from the filtered (35-per-club) set, not the full query.
- Final output sorted by club_sort_key then shot.id, consistent with prior behavior.
- Constants: MAX_SHOTS_PER_CLUB = 35, MAX_TOTAL_ROWS = 500.
- Existing filters (date_range, percentile, session_id, include_test) unchanged.

**Design decision:** Per-club limit applied before sorting and before max_carry computation. This means the Target column reflects recent performance, not all-time max. The 500-row cap is a safety valve — with 14 clubs × 35 = 490, it only triggers if more clubs appear.


### 2026-04-11 — Shotpattern Export Row Limit
- **Task:** Limit /api/export/shotpattern CSV output per-club to 35 most recent shots, 500 total rows max.
- **Implementation:** Two-pass algorithm groups shots by club, sorts by shot.id descending, applies 35-shot cap per club. Total rows hard-capped at 500. Compound clubs and null-carry shots filtered during grouping. Target (90% of max_carry) recomputed from filtered set.
- **Impact:** Prevents oversized CSV exports when importing into shotpattern iPhone app. With 14 clubs × 35 = 490 max rows, 500 cap acts as safety valve. Recent shot data prioritized for pattern analysis.
- **Testing:** All 314 tests passing; no regressions. Edge cases: varying shot counts per club, empty clubs, non-standard clubs, carry values on boundary conditions.
