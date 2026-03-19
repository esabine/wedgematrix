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
- Print is a first-class citizen: `print.css` loaded with `media="print"`, pocket cards use `@page { size: 2in 3.5in }` (portrait).

**Templates (9 files):**
- `base.html` — nav, flash messages, content block, footer
- `dashboard.html` — summary cards, quick links, recent sessions
- `import.html` — file upload → parsed preview table → swing size batch-tagging (wedge data)
- `sessions.html` — session list with Bootstrap modal delete confirmation
- `shots.html` — filterable table with AJAX exclude toggles, batch select, club toggle buttons, errant/excluded row styling
- `club_matrix.html` — Club | Carry | Total | Max with percentile + session scope selectors
- `wedge_matrix.html` — Swing Size | AW | SW | LW, fraction=carry-only, clock-hand=carry/max
- `print_card.html` — standalone print page (no base.html), both matrices on one card
- `analytics.html` — 6 chart containers with session + club + temporal date range filters

**CSS (2 files):**
- `style.css` — full design system: `.btn-golf`, `.table-golf`, `.excluded-row`, `.errant-row`, `.matrix-cell.has-data`, `.shot-data-table` compact styling, `.club-toggle-btn`, responsive breakpoints
- `print.css` — pocket card sizing (2"×3.5" portrait), `@media print` hide rules, high-contrast table headers

**JS (3 files):**
- `app.js` — flash auto-dismiss, matrix control reload (percentile/session), AJAX shot exclude toggle, batch select/exclude, delete confirmation modal, club toggle buttons with client-side filtering
- `charts.js` — 6 Chart.js functions: carry distribution, dispersion scatter, spin vs carry, loft trend, shot shape (with crosshairs plugin), club comparison. Golf color palette. Instances tracked for cleanup. Temporal date_range param support.
- `import.js` — swing size batch-tagging: checkbox + shift-click row selection, assign dropdown, save validation (all wedge shots must have sizes)

**Key decisions:**
- Matrix selectors do full page reload (not AJAX) — simpler, and Fenster's routes return rendered templates
- Shot exclude toggles use AJAX POST → JSON response for instant visual feedback
- Charts load all 6 endpoints in parallel via `Promise.all`
- Swing size tagging uses hidden inputs per row, validated on form submit
- `print_card.html` does NOT extend `base.html` — completely standalone for clean print output
- Club filter uses toggle buttons (client-side row visibility), not a dropdown
- Shot table uses 0.8rem font + abbreviated headers to fit 19 columns without horizontal scroll pain

**API endpoints (all working):**
- `/api/analytics/carry-distribution`, `/api/analytics/dispersion`, `/api/analytics/spin-carry`
- `/api/analytics/loft-trend`, `/api/analytics/shot-shape`, `/api/analytics/club-comparison`
- `/shots/<id>/toggle-exclude` (POST → JSON with `success`), `/shots/batch-exclude` (POST → JSON with `success`)
- `/import/upload` (POST multipart), `/import/save` (POST form)
- `/sessions/<id>/delete` (POST)

### 2026-03-15 — Bug Fix Round

**Analytics charts were blank:** Root causes — (1) analytics route didn't pass `has_data` or `clubs` to template, so `loadAnalytics()` never ran. (2) Backend `carry_distribution()` returns a dict keyed by club, but JS expected an array. (3) Backend returns `club_short` but JS referenced `d.club`. (4) No `loft-trend` or `club-comparison` API endpoints existed. Fixed all mappings and added missing endpoints.

**Temporal filter controls added:** Bootstrap btn-group with radio buttons (7d/30d/60d/90d/All). Selecting one auto-refreshes charts, passing `date_range` query param for backend filtering.

**Shot table expanded:** Added Swing Size, L.Dir, Back Spin, Side Spin, Ball Speed, Apex, Landing Angle, Club Path, Face Angle, Attack Angle columns. Used 0.8rem font with abbreviated headers. Excluded column replaces verbose Status column.

**Club toggle buttons:** Replaced dropdown with 14 toggle buttons + All. Client-side row visibility filtering — instant, no server round-trip.

**Batch exclude/include fixed:** Backend wasn't returning `success` field. JS was sending `exclude` (bool) but backend expected `action` (string). Fixed both sides. Select-all now respects club-toggle visibility.

**Pocket card portrait:** Changed from 3.5"×2" landscape to 2"×3.5" portrait. Tightened fonts/padding to fit narrower width.

### 2026-03-18 — Performance, Analytics UX, Print Sizing, Batch Import

**Shots tab toggle performance:** Cached all DOM row references and club text at init time. Replaced `getActiveClubs()` array scan with `activeSet` object hash for O(1) lookups. Eliminated per-toggle `querySelectorAll` re-queries. Toggle now instant even with 500+ rows.

**Analytics club toggles:** Replaced single-club `<select>` dropdown with toggle buttons matching shots page UX. Added "All" and "None" quick-action buttons. Charts auto-refresh on toggle via `loadAnalytics()`. Comma-separated club values passed in hidden input.

**Print card sizing:** Club matrix resized from 2"×3.5" to 2.5"×4". Wedge matrix set to 2.5"×3". Both cards now print on a single letter-size sheet with dashed cut guides. Used ID-specific sizing (`#club-card`, `#wedge-card`) instead of single `.pocket-card` size. `@page` changed from card-size to `letter portrait`.

**Batch import UX:** Reorganized controls into a clean 3-step card layout: (1) group-select with configurable count, (2) swing size dropdown, (3) "Tag & Import" button that assigns size + sends to backend in one click. Imported rows removed from DOM. "All done" section with session link appears when no rows remain. Backend `/api/import/batch` endpoint (built by Fenster) handles incremental saves with session_id tracking across batches.

### 2026-03-19 — Print Scaling, Club Selector UX, Percentile UI

**Print card scaling:** Both pocket cards widened 37% (2.5"→3.4") and all print font sizes doubled. Club matrix now 3.4"×4", wedge matrix 3.4"×3". Still fits on one letter-size sheet with dashed cut guides. Updated card-label preview text to match.

**Club selector behavior change:** Both shots page and analytics page club toggles now use click=exclusive-select, ctrl+click=additive-toggle. "All" selects everything, "None" deselects everything. Added "None" button to shots page (analytics already had one). Uses `e.ctrlKey || e.metaKey` detection.

**Percentile selector on analytics:** Added btn-group radio buttons (P25/P50/P75/P90/P95, default P75) to analytics filter bar. Hidden input `#analytics-percentile` feeds into `loadAnalytics()` which passes `?percentile=XX` to all 6 chart API endpoints. Also expanded club_matrix and wedge_matrix dropdowns with P25 and P95 options.

**Percentile explanation cards:** Added light green info cards at the bottom of analytics, club_matrix, and wedge_matrix pages. Each card explains percentiles in golf terms with concrete examples (e.g., "P75 = 155 yards means 75% of shots carry at least that far"). Wedge matrix card uses wedge-specific examples (swing sizes, carry/max).

### 2026-03-20 — Shots UX, Print Polish, Analytics Cleanup

**Hidden shots toggle:** Excluded shots now hidden by default on the shots page. A `form-switch` toggle ("Show Hidden" with badge count) in the filter bar controls `include_hidden` URL param. Backend counts hidden shots before filtering them out so the badge is accurate regardless of toggle state. Toggle triggers page reload with updated filter params.

**Suggested exclusions UI:** Added AJAX-driven collapsible card at top of shots page that fetches from `/api/shots/suggested-exclusions`. Shows outlier shots grouped with club, carry, offline, and reason. Per-shot Exclude (calls toggle-exclude endpoint) and Dismiss (session-only, no server call) buttons. Bulk "Exclude All Suggested" uses batch-exclude endpoint. Section auto-hides when no suggestions available.

**Dispersion chart origin:** Set Y-axis (carry) `min: 0` on dispersion scatter chart so patterns always show relative to origin.

**Refresh button removed:** Removed the manual refresh button from analytics page. Charts already auto-refresh when any filter (clubs, percentile, date range, session) changes — the button was redundant.

**Percentile explanation rewrite:** All three pages (analytics, club_matrix, wedge_matrix) now use a golf analogy: "line up shots shortest to longest." Explains WHY numbers go UP with higher percentiles — because `np.percentile(carries, N)` picks further up the sorted list. P50 = safe, P75 = reliable go number, P90 = A-game distance.

**Print card sizing:** Removed fixed `height` from `#club-card` and `#wedge-card` in print.css — table height now flows naturally from row count. Width reduced 10% from 3.4" to 3.06". Both cards still fit on one letter sheet with cut guides.

**Print card metadata:** Added `.card-footer-row` below each printed matrix — percentile ("P75") left-justified, today's date (mm/dd/yyyy via JS) right-justified. Thin border-top separator. Club card heading changed from "My Distances" to "Club Distances". Print route already passes `percentile` to template context.
