# Squad Decisions

## Active Decisions

### 1. Backend Route Naming Aligns to Frontend Templates
**Date:** 2026-03-14 | **Author:** Fenster | **Status:** Implemented

Route endpoint names match existing frontend `url_for()` references:
- `import_data`, `sessions`, `club_matrix`, `wedge_matrix`, `print_card` (alias `/print/pocket-card`)
- Template variable contract: `matrix`, `selected_session`, `percentile`, `shot.standard_loft`, `shot.errant`
- Impact: Frontend and backend fully compatible without template modification

### 2. Frontend Architecture: AJAX for Shots, Full Reload for Matrices
**Date:** 2026-03-14 | **Author:** McManus | **Status:** Implemented

- Matrix selectors → full page reload (simpler state management)
- Shot exclude toggles → AJAX POST with instant visual feedback
- Charts load 6 endpoints in parallel via `Promise.all()`
- Print card is standalone (no base.html extension)
- Pocket card size: 3.5" × 2" via CSS `@page`

### 3. Club Selector Click Behavior: Exclusive + Ctrl+Click Additive
**Date:** 2026-03-19 | **Author:** McManus | **Status:** Implemented

- Plain click = exclusive select (deselects all, selects only that club)
- Ctrl/Cmd+click = additive toggle (add/remove from multi-selection)
- All/None quick-action buttons
- Applies to both shots and analytics pages

### 4. Batch Import API for Wedge Data
**Date:** 2026-03-18 | **Author:** Fenster | **Status:** Implemented

- `/api/import/batch` POST: incremental imports with session_id tracking
- First call: `session_id: null` → creates Session, returns session_id
- Subsequent: pass session_id, appends shots with per-shot `swing_size`
- Club imports remain on `/import/save` form POST

### 5. Test Strategy: pytest with In-Memory SQLite and NumPy Oracle
**Date:** 2026-03-14 | **Author:** Hockney | **Status:** Implemented

- Fresh in-memory DB per test (function-scoped), no test-order dependencies
- Real CSV integration tests catch format drift
- All percentile assertions cross-checked against `numpy.percentile()`
- Service function signatures: `csv_parser`, `analytics`, `club_matrix`, `wedge_matrix`, `loft_analysis`

### 6. Print Card Sizing: 2.5"×4" Club / 2.5"×3" Wedge on One Sheet
**Date:** 2026-03-18 | **Author:** McManus | **Status:** Implemented

- Club matrix: 2.5" × 4"; Wedge matrix: 2.5" × 3"
- Both on single letter-size page with dashed cut guides
- `@page` uses `letter portrait`, ID-specific sizing (`#club-card`, `#wedge-card`)

### 7. Import Pipeline Data Contract: Two-Step Flow with JSON
**Date:** 2026-03-14 | **Author:** Fenster | **Status:** Implemented

- Step 1: `POST /import/upload` → template receives `parsed_shots`, `session_info`
- Step 2: `POST /import/save` → form sends `session_info` and `shots_data` as JSON strings, `swing_sizes[N]` as bracket notation fields
- Any template/route changes must respect this contract

### 8. Suggested Exclusions API Response: Nested Club Dict
**Date:** 2026-03-19 | **Author:** Fenster | **Status:** Implemented

- Response format: `{outliers: {club_short: [{shot_id, reasons, carry, offline, carry_bounds, direction_bounds}]}, total_count, iqr_multiplier}`
- Rule: any backend change must be coordinated with matching frontend change
- Frontend expects club-keyed dict, not flat array

### 9. Server-Side Pagination for Shots Page
**Date:** 2026-03-19 | **Author:** Fenster | **Status:** Implemented

- 50 shots per page (configurable 25/50/100/200)
- Club toggles are now server-side filters (not client-side show/hide)
- All filter controls auto-navigate on change
- Trade-off: club toggle clicks now reload page instead of instant filtering

### 10. Disable Flask JSON Key Sorting to Preserve CLUB_ORDER
**Date:** 2026-03-20 | **Author:** Fenster | **Status:** Implemented

- Set `app.json.sort_keys = False` in `create_app()`
- Preserves Python dict insertion order in all JSON responses
- Impact: club-keyed API responses now respect CLUB_ORDER (Woods→Hybrids→Irons→Wedges)
- Affects: carry-distribution, loft-summary, radar-comparison, launch-spin-stability, suggested-exclusions

### 11. Chart Endpoint Tests Require Routed App Fixture
**Date:** 2026-03-20 | **Author:** Hockney | **Status:** Implemented

- Separate `routed_app` fixture calls `register_routes(app)` — avoids breaking lightweight bare-app fixture
- API response shapes differ from service functions (route handlers reshape data)
- Launch-spin-stability: `{clubs: {club: {spin, launch, ...}}, correlation}`
- Radar-comparison: `{axes, user: {values, raw}, pga: {values, raw}}`

### 12. Print Percentile Passthrough and Title Removal
**Date:** 2026-03-20 | **Author:** McManus | **Status:** Implemented

- Print links append `?percentile={{ percentile or 75 }}` and conditionally `&session_id={{ selected_session }}`
- Club matrix `.card-header-row` removed from DOM (previously hidden only in CSS)
- Printed matrix width reduced 5% (3.06" → 2.91") — cards fit letter sheet with cut guides
- Footer row shows correct percentile (not always P75)

### 13. Chart Data Format Fixes: Launch-Spin and Radar APIs
**Date:** 2026-03-20 | **Author:** Fenster | **Status:** Implemented

- Launch-spin-stability: renamed keys (`spin_rate`→`spin`, `launch_angle`→`launch`, `diagnosis`→`analysis`), wrapped in `{clubs: ..., correlation}`
- Radar-comparison: aggregated per-club data into single radar, dropped smash_factor (no club head speed), normalized 0-100 scale
- Percentile parameter now flows through carry+ball_speed in radar (was hardcoded median)

### 14. User Directive: Commit Between Features
**Date:** 2026-03-14 | **Author:** ersabine (via Copilot) | **Status:** Active

- Each fix/feature from todo.md should be committed individually before moving to the next
- Captures user's preferred workflow for incremental commits

### 15. /api/shots Response Format Change
**Date:** 2026-03-20 | **Author:** Fenster | **Status:** Implemented

- `/api/shots` response changed from flat JSON array to paginated envelope: `{shots: [...], page, per_page, total_count, total_pages}`
- Supports `club` as comma-separated list, `date_range`, `include_hidden`, `page`, `per_page`
- Max 200 per page to prevent memory spikes
- Any future JS code calling `/api/shots` must unwrap `data.shots` (not iterate `data` directly)
- Currently no frontend callers — shots page uses server-rendered route

### 16. Batch Exclude/Include Logic Moved to Shots Inline Script
**Date:** 2026-03-22 | **Author:** McManus | **Status:** Implemented

- Batch select/exclude logic for the shots page now lives in the `shots.html` inline `<script>` block, not in `app.js`
- `app.js` `initBatchSelectExclude` skips when `shots-date-range-group` is detected (same pattern as `initClubToggleButtons`)
- Uses `action: 'exclude'`/`action: 'include'` string contract (backend supports both string and bool)
- Rationale: keeps all shots-page JS in one place, eliminates potential timing/scope conflicts between app.js and the inline script
- Impact: no behavior change on other pages (no other page uses batch select)

### 17. Test Session Filtering Strategy
**Date:** 2026-03-22 | **Author:** Fenster | **Status:** Implemented

- **When `session_id` is provided:** No test filtering — user explicitly selected that session, even if it's marked test.
- **When aggregating across sessions (`session_id=None`):** Exclude test sessions by default. Accept `include_test=true` query param to include them.
- **Session dropdowns (matrix/analytics pages):** Show all sessions including test ones, so users can still select a test session if they want to view it directly.
- **`get_shots_query` default:** `include_test=False` so all analytics functions automatically exclude test sessions without needing signature changes.
- **Impact:** All route handlers, API endpoints, and service functions respect this convention. Frontend adds `include_test=true` param only if it wants to show test data in aggregate views. Toggle endpoint at `POST /api/sessions/<id>/toggle-test`.

### 18. Wedge Matrix — Swing Size Rename + PW Column
**Date:** 2026-03-22 | **Author:** Fenster | **Status:** Implemented

- **Swing sizes:** `['3/3', '2/3', '1/3', '10:2', '10:3', '9:3', '8:4']`. No more 4/4.
- **FRACTION_SIZES:** `{'3/3', '2/3', '1/3'}` — carry only cells.
- **WEDGE_CLUBS:** `['PW', 'AW', 'SW', 'LW']` — PW first.
- **DB migration:** Renames old swing_size values on app startup. Idempotent (no-op if already renamed).
- **Runtime mapping:** `build_wedge_matrix` also maps old names at query time for robustness (handles unmigrated DBs and in-memory test DBs).
- **4/4 shots:** 15 shots remain in DB with swing_size='4/4' — they're real data but excluded from wedge matrix display. Visible on the shots page if filtered by swing_size.
- **Impact:** Templates already updated by McManus — no frontend work needed. Any future import of wedge shots must use the new swing size names. The import template dropdown already shows the new values.

### 19. Dispersion API Response Shape Change
**Date:** 2026-03-22 | **Author:** Fenster | **Status:** Implemented

- The `/api/analytics/dispersion` endpoint response changed from a flat array to an envelope:
  - **Before:** `[{carry, offline, club, club_short}, ...]`
  - **After:** `{shots: [{carry, offline, club, club_short}, ...], dispersion_boundary: {club_name: [{carry, offline}, ...]}}`
- Adding P90 dispersion boundary data alongside the scatter points requires a structured envelope rather than a flat array. The boundary is computed per-club using convex hull + cubic spline smoothing.
- **Frontend:** McManus already prepared `initDispersionChart()` to handle both formats (envelope and legacy array). No frontend changes needed.
- **Tests:** 4 dispersion tests updated to expect the new envelope format.
- **New dependency:** `scipy>=1.12` added to `requirements.txt` for ConvexHull and CubicSpline.
- **Any future consumer** of `/api/analytics/dispersion` must unwrap `data.shots` (not iterate `data` directly).

### 20. Dispersion Boundary Minimum Shot Threshold
**Date:** 2026-03-22 | **Author:** Hockney | **Status:** Observation

- The `compute_dispersion_boundary()` function uses double percentile filtering (carry range + offline range), which means a club needs **8+ well-spread shots** to reliably produce a boundary polygon.
- 3 shots pass the initial `len(carries) < 3` gate but get filtered out by the P75 carry/offline percentile ranges.
- 5 shots with tight spread also fail to survive the double filter.
- This is good behavior (noisy small-sample boundaries would be misleading), but any future UI or docs should set user expectations: "dispersion areas appear when you have enough data per club."
- **Impact:** Frontend should handle missing boundary gracefully — a club may have shots but no boundary.

### 21. Dispersion Boundary Visibility and Color Rendering
**Date:** 2026-03-23 | **Author:** McManus | **Status:** Implemented

- **API response format:** `/api/analytics/dispersion` returns `{shots: [...], dispersion_boundary: {club: [{carry, offline}, ...]}}` instead of flat array. Frontend handles both formats.
- **Boundary visibility threshold:** Boundaries shown only when ≤ 4 clubs are selected to prevent visual clutter. Single-club always shows boundary.
- **Color contract:** Single-club boundary is red; multi-club boundaries match club scatter palette color.
- **Boundary datasets labeled `{club} P90`** — filtered from legend and tooltips via label suffix check.
- **Impact:** Any test asserting `isinstance(data, list)` on the dispersion endpoint needs updating to expect the new dict envelope.

### 22. Dispersion Boundary Tests Need Update for Pythagorean Carry
**Date:** 2026-03-25 | **Author:** Hockney | **Status:** Observation

- 6 tests in `test_dispersion_boundary.py` fail because `compute_dispersion_boundary()` uses Pythagorean-corrected carry (from TODO 66), but those tests seed shots with raw carry/offline values and expect boundaries based on raw carry ranges.
- Fix: update seed data in `test_dispersion_boundary.py` to account for the correction (use larger carry values or smaller offlines so corrected carries still produce boundaries). This is a test maintenance task, not a code bug.
- **Impact:** No production impact. The boundary computation is correct. Only the test assertions are stale.

### 23. Launch-Spin Stability Response Shape Extended
**Date:** 2026-03-23 | **Author:** Fenster | **Status:** Implemented

- `launch_spin_stability()` response now includes two additional top-level fields:
  - `high_variance_clusters`: array of `{club, metric, cv, std_dev, shot_count, severity, threshold_cv}` objects identifying clubs with unusually high variance relative to other clubs.
  - Per-club entries now include `stability: {spin_std, spin_cv, launch_std, launch_cv}` alongside existing `spin`/`launch` box plot stats.
- **Backward compatible:** Existing `clubs`, `correlation` keys unchanged. Frontend can optionally consume the new fields.
- **Detection algorithm:** CV (coefficient of variation) compared against median CV across all clubs. Threshold: max(1.5× median, floor of 3.0%).
- **Impact:** McManus can highlight flagged clusters in the chart UI using the `high_variance_clusters` array and `severity` field.

### 24. Dispersion Boundary Always Uses P90 Regardless of Percentile Selector
**Date:** 2026-03-23 | **Author:** Fenster | **Status:** Implemented

- `compute_dispersion_boundary()` now hardcodes `BOUNDARY_PERCENTILE = 90` internally.
- The `percentile` query parameter is accepted for API compatibility but does not change the boundary hull computation.
- Scatter dots (`dispersion_data()`) always show ALL non-excluded shots with no percentile filtering.
- Boundary = P90 of all displayed shots, always.
- **Impact:** Frontend sees the same API shape. Boundary is now wider (P90 vs old P75 default), which better represents the true dispersion area.
- **Supersedes behavior from Decision 19:** The old code used the `percentile` param to filter shots before hull. Now boundary is always P90.

### 25. Carry Gapping Badge Positioning: Between Bars, Not Above
**Date:** 2026-03-23 | **Author:** McManus | **Status:** Implemented

- Gap badges in the Carry Distance & Gapping chart are now positioned **between** the two adjacent bars they represent, not above a single bar.
- A bracket connector (two thin lines from badge edges to bar tops) visually ties the gap to both clubs.
- Y-axis uses `grace: '15%'` to make room for badges above the tallest bar.
- **Pattern rule:** Any future chart annotation representing a relationship between data points (gap, delta, difference) must be positioned between the related elements, not on one of them.
- **Impact:** Visual only — no backend or data contract changes. Tooltip now shows bidirectional gap info on hover.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
- Inbox files auto-merged into this document after batch completion
