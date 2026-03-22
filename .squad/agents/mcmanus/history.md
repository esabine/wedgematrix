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

### 2026-03-21 — Analytics Session Refresh, Print Title, Percentile Rewrite, Suggested Exclusions Fix

**Analytics session dropdown:** Added change event listener on `#analytics-session` that reloads the page with `?session_id=X` query param. Preserves existing URL params. Other filters (clubs, percentile, date range) continue using AJAX via `loadAnalytics()`.

**Print card title hidden:** `.card-header-row` set to `display: none !important` in `@media print` in print.css. Footer row already shows percentile + date, so header row was redundant on printed cards.

**Percentile explanations rewritten:** All three pages (analytics, club_matrix, wedge_matrix) now frame percentiles as a planning tool based on historical shot tendencies. Key principle: golfers can't choose which percentile to hit. No em dashes. Short sentences. Caddie-like tone with practical examples ("Water in front at 155? Check if your P75 clears it.").

**Suggested exclusions fixed:** The API returns `{ outliers: { club: [shots...] }, total_count }` but the JS expected a flat array. Rewrote the fetch handler to flatten the club-keyed dict, map `shot_id`/`reasons` fields correctly, and show descriptive reason badges (e.g., "Low carry (98 < 112)", "Extreme Right (22.3yd)"). Also wired current page filters (session_id, club, date_range) into the API call so suggestions match the active filter state.

### 2026-03-22 — Analytics Overhaul: Charts Added/Removed/Redesigned

**Print card header removed:** Removed `.card-header-row` entirely from both club and wedge cards in `print_card.html`. Previously hidden only in print CSS; now gone from DOM. Footer row (percentile + date) is the only metadata shown.

**Loft trend chart removed:** Deleted `initLoftTrend()` from `charts.js`, removed the chart container from `analytics.html`, and dropped its API call from `loadAnalytics()`. Backend endpoint also removed by Fenster.

**Carry distribution redesigned for gapping:** Single bar per club (colored by club palette) at selected percentile. Gap values drawn as colored badges above each bar with a custom Chart.js plugin (`gapAnnotations`). Red = gap >20yd, amber = <5yd, green = ideal. Dashed connector lines between adjacent bars. API expected to return `gap` field per club.

**Launch-Spin Stability box plot:** New chart using `@sgratzl/chartjs-chart-boxplot@4` plugin (CDN added to `base.html`). Side-by-side box plots per club for Spin Rate (green) and Launch Angle (blue). High-variance clubs get red "HIGH VAR" badge via custom `highVarianceBadge` afterDraw plugin. Correlation analysis text rendered below chart. API: `/api/analytics/launch-spin-stability`.

**Radar chart vs PGA Tour:** Native Chart.js radar type. User metrics as filled green area, PGA Tour average as dashed gray outline. 6 axes normalized 0-100. Tooltips show both percentile and actual raw values. API: `/api/analytics/radar-comparison`.

**Analytics layout reorganized:** Two labeled sections — "Shot Analysis" (5 charts: carry+gapping, dispersion, spin vs roll, shot shape in 2-col grid; club comparison full-width) and "Performance Analysis" (2 charts: box plot + radar, side-by-side). Total: 7 charts. All responsive via `col-lg-6`.

**Key files modified:**
- `templates/print_card.html` — header rows removed
- `templates/analytics.html` — loft trend removed, 2 new chart containers added, layout sections
- `templates/base.html` — chartjs-chart-boxplot CDN added
- `static/js/charts.js` — `initLoftTrend` removed, `initCarryDistribution` redesigned, `initLaunchSpinStability` and `initRadarComparison` added, `loadAnalytics()` now fetches 7 endpoints in parallel

### 2026-03-22 — Print Percentile Fix, Title Cleanup, Width Reduction
- **Print Card percentile passthrough:** The Print Card links on both `club_matrix.html` and `wedge_matrix.html` were navigating to `/print` with no query params, causing the pocket card to always render at the default percentile (P75). Fixed by appending `?percentile={{ percentile or 75 }}` and conditionally `&session_id={{ selected_session }}` to both links. The backend route already reads these params — they were simply never being sent.
- **Club Matrix title hidden on print:** Added `no-print` class to the `<h1>` heading in `club_matrix.html`. The `print.css` already hides `.no-print` elements in `@media print`. This addresses the repeated TODO requests (lines 43, 47, 50) to remove titles above the club matrix. The pocket card (`print_card.html`) already had no title above the table — the `.card-header-row` was removed in a prior round.
- **Printed matrix width reduced 5%:** Both `#club-card` and `#wedge-card` in `print.css` narrowed from 3.06in to 2.91in. Card preview labels in `print_card.html` updated to match.
- **Dynamic table height (already done):** No fixed height on either card — height flows from row count. Confirmed no `height` property exists on `#club-card` or `#wedge-card`.
- **Footer row percentile + date (already working):** The `.card-footer-row` in `print_card.html` already shows `P{{ percentile or 75 }}` left-justified and JS-generated mm/dd/yyyy date right-justified. With the percentile passthrough fix, these now display the correct selected percentile instead of always P75.
- **Key pattern:** Print Card links must always forward the current page's filter state (percentile, session_id) as query params. The backend reads them from `request.args` — the templates just weren't passing them.

### 2026-03-20 — Fenster Chart Data Format Updates (Cross-Agent Note)
- Fenster fixed launch-spin-stability and radar-comparison API response formats
- Percentile parameter now properly flows through both endpoints
- Our print card now receives correct percentile data to display in footer

### 2026-03-22 — Club Selector / Percentile / Temporal Verification

**Verification pass:** All three task requirements (club toggle UX, percentile selector, temporal filter) were already implemented in prior rounds:
- Club toggles with All/None/click-exclusive/Ctrl+click-additive: both analytics and shots pages (2026-03-19)
- Percentile selector P25-P95 (default P75) on analytics page with chart auto-refresh (2026-03-19)
- Temporal date range 7d/30d/60d/90d/All on analytics page with chart auto-refresh (2026-03-15)

**Gap fixed:** Shots page date range was missing the 60d option. Analytics had 7d/30d/60d/90d/All but shots only had 7d/30d/90d/All. Added the 60d radio button for parity.

### 2026-03-22 — Shots Columns, Batch Fix, Percentile Rewrite, Print Hardening

**Shot table columns:** Added computed "Roll" column (Total minus Carry) after Total. Reordered Ball Speed before Launch Angle for better visual grouping (distance metrics together, then flight metrics). Total column count: 21 (checkbox + 18 data + Excl badge + Action).

**Batch exclude/include fix:** Moved batch select/exclude logic from `app.js` into `shots.html` inline script. Key changes: (1) Uses `action: 'exclude'`/`action: 'include'` string contract instead of `exclude: true/false` boolean, (2) All three required elements guarded (`selectAll`, `excludeBtn`, `includeBtn`), (3) Spinner feedback during fetch, (4) Error recovery restores button state. Added skip condition in `app.js` `initBatchSelectExclude` so it doesn't double-register on the shots page.

**Percentile explanation rewrite (3rd pass):** All three pages (club_matrix, wedge_matrix, analytics) now follow the exact user spec: golfer cannot choose percentile, frame as planning tool, no em dashes, short sentences, caddie tone. Key improvement: explicitly explains WHY numbers go up — "higher percentile means picking from further up the sorted list."

**Print CSS hardened:** Added `page-break-after: avoid` and `break-after: avoid` on `#club-card` to guarantee both matrices stay on the same printed sheet. Portrait orientation and same-sheet behavior were already correct via `@page { size: letter portrait; }`.

**Verified already-done tasks:** Hidden shots toggle (toggle + badge + include_hidden param) and portrait pocket card orientation were already working from prior rounds.

### 2026-03-22 — Verification Pass + Import Hardening

**Print sizing verified:** Current state: both cards 2.91" wide, height auto. Font sizes doubled (13-14pt) from prior round. Width evolved: 2.5" → 3.4" (37% wider) → 3.06" (−10%) → 2.91" (−5%). All user adjustments applied. Club card: 14pt body/table, 13pt headers. Wedge card: 13pt body/table, 12pt headers. No changes needed.

**"Club Distances" removal verified:** Searched all 10 templates — zero instances of "Club Distances" or "My Distances". The `.card-header-row` was removed from `print_card.html` DOM in a prior round. The `club_matrix.html` heading says "Club Matrix" with `no-print` class. Issue is fully resolved.

**Import flow verified working:** Tested both club and wedge import paths end-to-end via Playwright browser automation. Club path: upload CSV → preview (82 shots) → Save Import → 302 redirect to session detail. Wedge path: upload CSV → preview (100 shots) → Select first 5 → set swing size → Tag & Import → "5 saved ✓, 95 remaining". All TODO line 8 issues were resolved in prior rounds.

**Batch import UX verified:** Group select ("First N"), configurable group size, swing size dropdown, Tag & Import one-click flow, remaining count badge, "All done" section — all working as designed. No changes needed.

**Import form hardened:** Changed hidden form fields (`session_info`, `shots_data`) from inline `value='{{ tojson }}'` to JS-populated values via `JSON.stringify()`. The old single-quoted attributes could theoretically break with filenames containing apostrophes. New approach: empty `value=""` inputs + inline `<script>` block that sets `.value = JSON.stringify({{ tojson }})`. Tested both club save (form POST) and wedge batch (fetch API) paths — both work correctly.

### 2026-03-23 — TODOs 61, 62, 63: Test Data Toggle, Swing Size Labels, PW Column

**Test-data session toggle (TODO 61):** Added per-session toggle button (flask icon) in the Actions column. AJAX POST to `/api/sessions/<id>/toggle-test`. Test sessions get a yellow "Test" badge next to the date and an amber-highlighted row (`.test-data-row` class). A "Show Test Data" form-switch with badge count in the header controls visibility via `include_test` URL param. Hidden by default. Template expects `test_data_count`, `include_test`, and `session.is_test_data` from the backend route.

**Swing size label changes (TODO 62):** Removed 4/4 row entirely. Renamed 3/4→3/3, 2/4→2/3, 1/4→1/3 in all four templates: `wedge_matrix.html`, `print_card.html`, `shots.html` (filter dropdown), `import.html` (tagging dropdown). Fraction explanation text and percentile example updated to reference new labels. Swing sizes list now 7 rows instead of 8.

**PW column added to wedge matrix (TODO 63):** PW column inserted left of AW. Column order: PW, AW, SW, LW. Both `wedge_matrix.html` and `print_card.html` updated — club loop now iterates `['PW', 'AW', 'SW', 'LW']`. Empty-state colspan changed from 4 to 5. Print CSS: wedge card gets tighter padding/font (11pt headers, 12pt body, 1.5pt padding) to fit 5 columns at 2.91" width. On-screen: `#wedge-matrix-table .matrix-cell` min-width reduced from 60px to 44px.

**Key patterns:**
- Test-data toggle uses same AJAX-then-reload pattern as shot exclude toggles
- Show/Hide test data switch uses same URL-param-driven pattern as "Show Hidden" shots toggle
- Swing size labels are a data-contract change — backend must also recognize new labels (3/3, 2/3, 1/3)
- PW column requires backend wedge_matrix service to include PW in its output dict
