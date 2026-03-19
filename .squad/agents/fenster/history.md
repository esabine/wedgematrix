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
