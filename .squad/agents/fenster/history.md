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
