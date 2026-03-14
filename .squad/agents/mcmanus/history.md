# Project Context

- **Owner:** ersabine
- **Project:** wedgeMatrix — Golf launch monitor analytics app with percentile-based club/wedge matrices and pocket card printing
- **Stack:** Python 3.11+, Flask, SQLite/SQLAlchemy, Pandas/NumPy, Bootstrap 5, Chart.js
- **Created:** 2026-03-14

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-14 — Full Frontend Build

**Architecture:**
- Base layout (`templates/base.html`): Bootstrap 5.3.3 CDN + Bootstrap Icons + Chart.js 4.4.7 CDN. No build step.
- Color palette anchored on `--golf-green: #2d6a4f` with CSS custom properties in `style.css` for consistency.
- Navigation uses `request.endpoint` matching for active-state highlighting.
- Print is a first-class citizen: `print.css` loaded with `media="print"`, pocket cards use `@page { size: 3.5in 2in }`.

**Templates (9 files):**
- `base.html` — nav, flash messages, content block, footer
- `dashboard.html` — summary cards, quick links, recent sessions
- `import.html` — file upload → parsed preview table → swing size batch-tagging (wedge data)
- `sessions.html` — session list with Bootstrap modal delete confirmation
- `shots.html` — filterable table with AJAX exclude toggles, batch select, errant/excluded row styling
- `club_matrix.html` — Club | Carry | Total | Max with percentile + session scope selectors
- `wedge_matrix.html` — Swing Size | AW | SW | LW, fraction=carry-only, clock-hand=carry/max
- `print_card.html` — standalone print page (no base.html), both matrices on one card
- `analytics.html` — 6 chart containers with session + club filters

**CSS (2 files):**
- `style.css` — full design system: `.btn-golf`, `.table-golf`, `.excluded-row`, `.errant-row`, `.matrix-cell.has-data`, responsive breakpoints
- `print.css` — pocket card sizing (3.5"×2"), `@media print` hide rules, high-contrast table headers

**JS (3 files):**
- `app.js` — flash auto-dismiss, matrix control reload (percentile/session), AJAX shot exclude toggle, batch select/exclude, delete confirmation modal
- `charts.js` — 6 Chart.js functions: carry distribution, dispersion scatter, spin vs carry, loft trend, shot shape (with crosshairs plugin), club comparison. Golf color palette. Instances tracked for cleanup.
- `import.js` — swing size batch-tagging: checkbox + shift-click row selection, assign dropdown, save validation (all wedge shots must have sizes)

**Key decisions:**
- Matrix selectors do full page reload (not AJAX) — simpler, and Fenster's routes return rendered templates
- Shot exclude toggles use AJAX POST → JSON response for instant visual feedback
- Charts load all 6 endpoints in parallel via `Promise.all`
- Swing size tagging uses hidden inputs per row, validated on form submit
- `print_card.html` does NOT extend `base.html` — completely standalone for clean print output

**API endpoints assumed (Fenster to build):**
- `/api/analytics/carry-distribution`, `/api/analytics/dispersion`, `/api/analytics/spin-carry`
- `/api/analytics/loft-trend`, `/api/analytics/shot-shape`, `/api/analytics/club-comparison`
- `/shots/<id>/toggle-exclude` (POST → JSON), `/shots/batch-exclude` (POST → JSON)
- `/import/upload` (POST multipart), `/import/save` (POST form)
- `/sessions/<id>/delete` (POST)
