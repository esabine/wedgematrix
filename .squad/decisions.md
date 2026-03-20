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

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
- Inbox files auto-merged into this document after batch completion
