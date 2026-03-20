# Project Context

- **Owner:** ersabine
- **Project:** wedgeMatrix — Golf launch monitor analytics app with percentile-based club/wedge matrices and pocket card printing
- **Stack:** Python 3.11+, Flask, SQLite/SQLAlchemy, Pandas/NumPy, Bootstrap 5, Chart.js
- **Created:** 2026-03-14

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
