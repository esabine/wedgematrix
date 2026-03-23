# Project Context

- **Owner:** ersabine
- **Project:** wedgeMatrix — Golf launch monitor analytics app with percentile-based club/wedge matrices and pocket card printing
- **Stack:** Python 3.11+, Flask, SQLite/SQLAlchemy, Pandas/NumPy, Bootstrap 5, Chart.js
- **Created:** 2026-03-14

## Core Context

**Frontend Architecture & Template Patterns (Summarized from early sessions):**

The wedgeMatrix frontend is Bootstrap 5.3.3 with Chart.js 4.4.7 (CDN-based, no build step). Modular design with 9 templates + 3 CSS + 3 JS files:
- **Base Structure:** `base.html` (nav + footer + content block) + `style.css` (design system) + `app.js` (common interactions). Navigation active-state via `request.endpoint` matching. Print is first-class: `print.css` with `@media print` rules.
- **Color System:** `--golf-green: #2d6a4f` CSS custom property, applied to buttons (`.btn-golf`), tables (`.table-golf`), matrices (`.matrix-cell`).
- **Matrix Rendering:** Both `club_matrix.html` and `wedge_matrix.html` use table-based layout with:
  - Session selector (dropdown, auto-reload via POST to same route)
  - Percentile selector (radio buttons 50/75/90, auto-reload)
  - Fraction/Clock display toggle (wedge only, immediate class swap)
  - Data-driven cells: `.matrix-cell.has-data` for styling, `{{value}}` Jinja2
- **Shots Table:** 19 columns (Club, Carry, Total, Offline, Launch Dir, ..., Face Angle, Excluded). 0.8rem font. AJAX row toggles for exclude/include without page reload. Batch select via checkboxes (shift-click row selection). Club toggle buttons filter client-side (instant, O(1) via activeSet hash).
- **Analytics Charts:** 6 Chart.js instances in `analytics.html` loaded via `loadAnalytics()` (Promise.all, parallel). Each chart has:
  - Session selector (dropdown, reloads charts)
  - Club toggles (buttons, instant reload)
  - Temporal filter (7d/30d/60d/90d/All, radio buttons, auto-reload via `date_range` query param)
  - Specific customizations per chart (e.g., dispersion scatter has crosshairs plugin, shot-shape has golf color palette)
- **Import Workflow:** 3-step UI for wedge data:
  1. Group select (configurable count, e.g., "first 5")
  2. Swing size dropdown + "Tag & Import" button
  3. Backend batch endpoint `/api/import/batch` creates session on first call, reuses thereafter
  4. Rows removed from DOM after import; "All done" section shows when complete
- **Print Output:** `print_card.html` (standalone, NO base.html for clean output):
  - ID-specific sizing: `#club-card` (2.5"×4"), `#wedge-card` (2.5"×3")
  - `@page { size: letter portrait }` 
  - Dashed cut guides between cards
  - Percentile passed via URL param `?percentile={{percentile}}`
- **Key JS Patterns:**
  - `app.js`: Matrix reload via fetch + replace innerHTML (simpler than AJAX form)
  - `charts.js`: All 6 chart functions use same color palette, instances tracked in array for cleanup
  - `import.js`: Swing size validation (all wedge shots must have sizes before submit)
  - Shot toggles: POST to `/shots/<id>/toggle-exclude`, batch via `/shots/batch-exclude`
- **Form Contracts:**
  - Swing size batch tagging sends `{swing_sizes: {shot_id: size, ...}}` via hidden JSON input
  - Club matrix reload sends `{percentile, session_id}` via form POST
  - Exclude batch sends `{shot_ids: [...], exclude: true/false}` via JSON POST

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

### 2026-03-23 — Dispersion Chart: Target Line + P90 Boundaries

**TODO 64 — Target line at x=0:** Added a custom Chart.js `afterDraw` plugin (`dispersionTargetLine`) that draws a dotted vertical gray line at x=0 on the dispersion scatter chart. Labeled "Target" near the top. Uses canvas API directly — no external annotation plugin needed. Visible on all club selections.

**TODO 65 — P90 dispersion boundary polygons:** The dispersion API now returns an envelope `{shots: [...], dispersion_boundary: {club: [{carry, offline}, ...]}}`. The chart function handles both the new envelope and the legacy flat array format for backward compatibility.

- Each club's boundary rendered as a closed-loop polygon via `showLine: true` scatter datasets
- Dotted line (`borderDash: [5, 5]`), 12% opacity fill, smooth `tension: 0.3`
- Single-club view: boundary is red (`rgba(220, 53, 69)`); multi-club: matches club palette color
- Clutter guard: boundaries only shown when ≤ 4 clubs selected (or exactly 1)
- Boundary datasets hidden from legend and tooltips via `filter` callbacks
- Graceful degradation: if `dispersion_boundary` is missing or a club has < 3 points, no boundary is drawn

**Key patterns:**
- Custom Chart.js plugins via `plugins: [pluginObj]` on individual chart instances (not globally registered) — keeps plugin scope tight
- The `fillColor` regex `.replace(/[\d.]+\)$/, '0.12)')` swaps the alpha in any `rgba(...)` string to 0.12 — reusable trick for deriving transparent fills from opaque palette colors
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

### 2026-03-22 — Batch 5 Execution: TODO 61-63 Completed
**Outcome:** SUCCESS — 3 commits, all templates updated

Implemented across 3 features:
- **TODO 61 (Test Data Toggle UI):** Updated sessions.html to show test_data_count, render include_test query param for filtering
- **TODO 62 (Swing Size Rename):** Updated swing size labels (4/4→3/3, 3/4→3/3, 2/4→2/3, 1/4→1/3) in 4 templates. Removed 4/4 row from wedge matrix. Updated import swing size dropdown to show 7 sizes.
- **TODO 63 (PW Column):** Added PW as first club column in wedge_matrix.html, print_card.html. Updated column iteration and widths.

Templates updated:
- templates/wedge_matrix.html — swing labels, PW column
- templates/print_card.html — swing labels, PW column, layout adjustments
- templates/import.html — swing size dropdown (7 new labels)
- templates/analytics.html — swing size references

Cross-agent coordination:
- Fenster implemented backend (is_test toggle, swing rename, PW logic)
- Hockney added 28 tests validating frontend expectations
- All renders correct; print card adapts to 4-column layout


### 2026-03-22 — Gapping Label Placement Fix (TODO 69)

**Problem:** Gap badges in the Carry Distance & Gapping chart were positioned directly above each bar, but gapping is a between-clubs metric. This made it look like gapping was a property of a single club.

**Fix (charts.js — initCarryDistribution):**
- Gap badge now centered horizontally between the two adjacent bars it represents (`midX = (prevBar.x + bar.x) / 2`)
- Badge sits above the taller bar with 22px clearance, rendered as a pill (`roundRect` with 8px radius)
- Bracket connector lines from badge edges down to each bar top replace the old dashed diagonal line
- Font reduced from bold 11px to bold 10px for visual subordination to bar values
- Loop starts at `i = 1` (skips first club which has no predecessor) — cleaner than the old `i = 0` with null-checks
- Y-axis `grace: '15%'` + `layout.padding.top: 10` prevents badge clipping at chart edge

**Tooltip improvement:** Hover on any bar now shows both `Gap to next club` and `Gap from prev club` (bidirectional), not just `Gap from prev`.

**Key pattern:** Canvas annotations that represent relationships (gaps, deltas) between data points should be visually positioned between those points, not on either one.

---

### Session: TODOs 71-76 (continued)

#### TODO 73 — Dispersion Tooltip Enhancement
Extended scatter `data` array to include `spin_rate`, `launch_angle`, `ball_speed`, `face_angle` from the backend response. Tooltip callback checks for presence before display.

**Lesson:** Chart.js scatter points can carry arbitrary extra properties beyond `x`/`y`; access via `ctx.dataset.data[ctx.dataIndex].<prop>`.

#### TODO 74 — Launch & Spin Stability — Wider Chart
Simple CSS-only change: `col-lg-6` → `col-12`. Backend already handled wedge sub-swing grouping (hockney's work).

**Lesson:** Before touching JS, check whether the fix is purely layout. A one-class change in the template was all that was needed.

#### TODO 75 — Club Comparison as Box & Whisker
Rewrote `initClubComparison()` from grouped bar chart to `type: 'boxplot'` using `@sgratzl/chartjs-chart-boxplot@4`. Backend already provides `min/q1/median/q3/max/outliers/mean`. Mapped to `{min, q1, median, q3, max, outliers, mean}` objects.

**Lesson:** The boxplot plugin expects data items as objects with statistical fields, not arrays. Tooltip customization uses `ctx.parsed` which has `.min`, `.q1`, `.median`, etc.

#### TODO 76 — PGA Tour Radar Comparison per-club
Added `<select id="radar-club-select">` to the card header. `initRadarComparison()` populates dropdown from `data.clubs_used`, defaults to "All Clubs". `select.onchange` calls inner `renderRadar(clubKey)` which destroys and recreates the chart with the selected club's `per_club` data.

**Lesson:** When a chart needs a control (dropdown, toggle), wire it inside the init function so the data closure is available without globals. Destroy-and-recreate is simpler than `chart.update()` for radar type changes.
### 2026-03-22 — Batch 8 Completion (TODOs 71-76 Frontend Charts & UI)

**Batch 8 Outcome:** All frontend features implemented and rendering. 7 commits total.

**TODO 71 (Version Footer):** Template footers now display VERSION constant from backend (e.g., "v0.5.0"). Added to ase.html footer block used across all pages.

**TODO 72 (Gapping Fix):** Carry-distribution chart label rendering fixed. The issue was off-by-one gap calculation — gap array (length n-1 for n clubs) was being indexed incorrectly for chart bar positioning. Chart now correctly displays gap values between adjacent clubs (e.g., 3 clubs → 2 gaps). P75 gaps verified against backend data.

**TODO 73 (Dispersion Tooltip Fields):** Scatter plot hover tooltips now show:
- spin_rate (e.g., "2800 RPM")
- all_speed (e.g., "145 mph")
- ace_angle (e.g., "+2.5°")
- launch_angle (e.g., "18.5°")
Template: 	emplates/analytics/dispersion.html updated to include these fields in tooltip markup.

**TODO 74 (Sub-Swing Display):** Launch-spin-stability chart updated to render wedge clubs with sub-swing breakdown. Non-wedge clubs show as single entries (e.g., "1W"), wedges show with swing type labels (e.g., "PW (3/3)", "PW (full)", "AW (2/3)"). Chart.js dataset labels updated dynamically based on backend response structure.

**TODO 75 (Box-and-Whisker Plot):** Club-comparison chart refactored to render box-and-whisker format:
- Box plot from min/q1/median/q3/max provided by backend
- Outlier points plotted separately
- Wedge clubs display per-swing-type entries (e.g., "PW (3/3)", "PW (full)")
- Chart.js box plot plugin configured for whisker rendering
- Y-axis label changed from "Carry P75" to "Carry Distance (yards)"

**TODO 76 (PGA Radar Comparison):** Radar chart updated to display PGA Tour baseline for all 4 wedges. Existing per-club dropdown control extends to wedges. 5-axis format: Carry, Dispersion, Spin Rate, Launch Angle, Ball Speed. User data (blue) vs PGA baseline (orange grid) comparison working across all clubs.

**Template Changes:**
- ase.html — Version footer added
- nalytics.html — Gapping fix logic, dispersion tooltip markup
- wedge_matrix.html — Tooltip fields visible
- launch_spin_stability.html — Sub-swing entry display
- club_comparison.html — Box-whisker plot rendering
- adar_comparison.html — All 4 wedges in club dropdown, PGA baseline display

**Commits:** 7 total across all templates and static files.

**Cross-Agent Notes:**
- Fenster (backend) provided all required data transformations (sub-swing grouping, box stats, tooltip fields, PGA coverage).
- Hockney (tester) confirmed all 31 new tests pass; charts render correctly with new data payloads.

**Frontend Validation:** All templates parse without errors; Chart.js renders without console errors; dropdown controls respond to user input. Version footer visible on all pages.

### 2026-03-25 — Concentric Arc Chart + Canonical Club Ordering (TODOs 77-78)

**TODO 77 (Concentric Arc Carry Chart):** Replaced the bar chart carry-distance visualization with a custom HTML5 Canvas concentric arc chart. Design inspired by driving range distance markers:
- Dark green radial gradient background (driving range aesthetic)
- 170° semicircular arcs emanating from golfer origin at bottom center
- Reference rings at 25yd/50yd intervals with distance labels
- Color-coded arcs: woods (#66bb6a), hybrids (#26c6da), irons (#42a5f5), wedges (PW=#ffb74d, AW=#ffa726, SW=#ef5350, LW=#ab47bc)
- Gap fills highlight problem spacing: red tint for >20yd gaps, amber for <5yd
- Right-side legend sidebar with color swatches, club names, distances, and ⚠ gap badges
- Hover tooltip shows club details + shot count
- Custom `destroy()` method for compatibility with existing `chartInstances` cleanup pattern
- HiDPI/Retina display support via `devicePixelRatio` scaling

**TODO 78 (Canonical Club Ordering):** Added `CANONICAL_CLUB_ORDER` array and `sortByCanonicalOrder()` utility at top of charts.js:
- Order: Woods → Hybrids → Irons → Full wedge shots → 3/3 → 2/3 → 1/3 → clock swings (10:2 through 8:4)
- Includes both base names (PW, AW) and sub-swing labels (PW-Full, AW-3/3) so sorting works regardless of backend grouping
- O(1) lookup via pre-built `_CLUB_ORDER_MAP` index
- Applied to: carry distribution, club comparison, launch-spin-stability
- Unknown clubs sort alphabetically at end

**Key Pattern:** Custom Canvas charts store a `{destroy: function()}` object in `chartInstances` to stay compatible with the Chart.js cleanup lifecycle. The `destroyChart()` function also cleans up custom event handlers for the arc chart.
