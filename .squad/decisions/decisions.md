# Squad Decisions

## Dispersion Carry Geometry (TODO 66)

**Date:** 2026-03-23 | **Author:** Fenster & Hockney | **Status:** Approved

### Decision: Pythagorean Correction Applied at Query Time

**Problem:** Dispersion chart y-axis (carry) was using raw CSV carry (hypotenuse), not true forward distance toward target.

**Solution:**
- Apply correction `carry_corrected = sqrt(carry² - offline²)` at query time in `dispersion_data()` and `compute_dispersion_boundary()`
- Helper `_pythagorean_forward(carry, offline)` computes forward component
- Returns `None` for invalid data (carry ≤ 0, |offline| ≥ carry), causing those shots to be skipped
- No DB changes; no API shape changes; frontend field names unchanged (`carry`, `offline`)

**Rationale:**
- Dispersion chart now shows geometrically accurate shot scatter **toward the target**, not total ball travel distance
- Bad data is silently dropped rather than clamped to 0 (cleaner — a shot with 0 forward distance is noise anyway)
- All other endpoints (carry-distribution, club-comparison, wedge-matrix, spin-carry, etc.) remain unaffected — still use raw carry for their specific analytics

**Impact & Communication:**
- Any future consumer of `/api/analytics/dispersion` should know that `carry` in the response is the corrected forward distance, not the raw CSV value
- Frontend does not need changes — field names and value ranges remain compatible
- Dispersion chart may show fewer shots than the shots page for sessions with geometrically invalid data (|offline| ≥ carry), but this is expected and acceptable

**Verification:**
- 27 new tests confirm correctness, edge cases, boundary integration, and regression safety
- All 153 pre-existing tests still passing
- Final score: 180/183 (3 pre-existing loft analysis failures unrelated to this work)

---

## Dispersion Geometry: Bad Data Skipped, Not Clamped

**Date:** 2026-03-23 | **Author:** Hockney | **Status:** Observation

When `|offline| >= carry` (physically impossible data):
- `_pythagorean_forward()` returns `None` and the shot is **silently dropped** from dispersion results
- This means the dispersion chart may show fewer shots than the shots page for sessions with bad data
- Alternative (rejected): clamp to 0 forward distance. Current behavior (skip) is cleaner — a shot with 0 forward distance is noise anyway
- **Frontend impact:** Dispersion shot count does not need to equal total shot count; shots page shows all, dispersion shows only geometrically valid ones

---

## Dispersion Chart Pythagorean Carry Correction

**Date:** 2026-03-23 | **Author:** Fenster | **Status:** Implemented

- **Dispersion `carry` field is now corrected forward distance:** `sqrt(carry² - offline²)`, not raw CSV carry
- The raw CSV carry is the hypotenuse (total ball travel); the y-axis of the dispersion chart should be true forward component toward target
- Correction applied at query time in `dispersion_data()` and `compute_dispersion_boundary()` via `_pythagorean_forward()` helper
- No DB changes; no API shape changes; frontend field names unchanged (`carry`, `offline`)
- Edge cases handled: carry≤0 → skip, |offline|≥carry → skip (bad data), offline==0 → no correction, None values → skip
- **Impact:** Any future consumer of `/api/analytics/dispersion` should know that `carry` in the response is the corrected forward distance, not the raw CSV value. Other endpoints (carry-distribution, club-comparison, etc.) still use raw carry — this correction is dispersion-chart-specific.

---

## Canonical CLUB_ORDER: 48-Entry List with Compound Wedge Labels

**Date:** 2026-03-25 | **Author:** Fenster | **Status:** Implemented

- `CLUB_ORDER` in `services/club_matrix.py` expanded from 14 bare club names to 48 entries covering both bare names and compound wedge-swing labels.
- Order: Woods → Hybrids (incl. 4H) → Irons (incl. 3i) → Bare wedges (PW, AW, SW, LW) → Full swings → 3/3 → 2/3 → 1/3 → 10:2 → 10:3 → 9:3 → 8:4.
- Wedge sub-swings grouped by **swing type** (all 3/3 before all 2/3), NOT by club. Within each group: PW < AW < SW < LW.
- `club_sort_key()` function provides O(1) lookup for sorted(). Unknown labels sort alphabetically after all known entries.
- **Impact:** All dict-keyed and list-keyed chart API responses now sort via `club_sort_key`. Carry-distribution, loft-summary use bare names. Club-comparison, launch-spin-stability use compound labels. Both are handled by the same constant.
- **Frontend note:** No changes needed — the response shapes are unchanged, only key ordering differs.

---

## Swing Path L/R Parsing: Backend Correct, Frontend May Need Audit

**Date:** 2026-03-25 | **Author:** Fenster | **Status:** Verified

- `parse_direction()` correctly maps R prefix → positive, L prefix → negative for club_path and face_angle.
- Database audit confirmed: 401/469 club_path values positive (R, in-to-out), 40 negative (L, out-to-in). Matches CSV source data.
- No data migration needed — existing values are correct.
- If the shot-shape chart still misinterprets swing path direction (shows "out-to-in" for positive values), the issue is in the frontend chart's sign/label convention, not the backend.
- **Impact:** McManus should verify the shot-shape chart interprets positive club_path as "in-to-out" and negative as "out-to-in."

---

## Canonical Club Order Applied in Frontend Charts

**Date:** 2026-03-25 | **Author:** McManus | **Status:** Implemented

- `CANONICAL_CLUB_ORDER` array defined in `charts.js` with full wedge sub-swing coverage:
  `1W, 3W, 2H, 3H, 4H, 3i, 4i, 5i, 6i, 7i, 8i, 9i, PW, PW-Full, AW, AW-Full, SW, SW-Full, LW, LW-Full, [3/3 group], [2/3 group], [1/3 group], [clock swings]`
- `sortByCanonicalOrder(clubs)` utility sorts any club label array by this order; unknowns go to end alphabetically.
- Applied client-side to: carry distribution (concentric arc), club comparison (boxplot), launch-spin stability (boxplot).
- Backend already sorts carry-distribution by `CLUB_ORDER` (Decision 10), but frontend re-sorts for safety.
- **Impact:** Any new chart consuming club-keyed data should call `sortByCanonicalOrder()` on its labels before rendering.

---

## Carry Distance Chart: Custom Canvas (Not Chart.js)

**Date:** 2026-03-25 | **Author:** McManus | **Status:** Implemented

- The carry distance visualization is now a custom HTML5 Canvas drawing, NOT a Chart.js instance.
- Stored in `chartInstances['carry-distribution']` as `{destroy: function()}` for lifecycle compatibility.
- `destroyChart()` also cleans up custom `mousemove` handlers on the canvas element.
- **Pattern rule:** Any future custom Canvas chart must provide a `destroy()` method and be stored in `chartInstances` for cleanup on analytics reload.

---

## Club-Comparison Endpoint Needs Box Plot + Sub-Swing Refactor (TODO 75)

**Date:** 2026-03-26 | **Author:** Hockney | **Status:** Proposed

**Problem:** TODO 75 asks for box-and-whisker data in the club comparison chart, with wedge clubs broken by sub-swing type. Currently `/api/analytics/club-comparison` returns `{club, carry_p75, total_p75, max_total, shot_count}` — a flat percentile summary.

**Proposed Solution:** Fenster should refactor the `club-comparison` route handler to:
1. Use `_box_plot_stats()` (already exists in analytics.py) to compute min/q1/median/q3/max/outliers per club
2. For wedge clubs (PW, AW, SW, LW), generate separate entries per swing type, keyed like `"PW (3/3)"`, `"PW (full)"` etc. — same pattern Fenster already used for `launch_spin_stability` sub-swing breakdown
3. Non-wedge clubs remain as single entries

**Impact:**
- 2 spec tests in `test_todo_71_76.py` will pass once implemented
- Frontend (McManus) will need to update the Chart.js club-comparison chart to render box-and-whisker format instead of simple bar chart
- The sub-swing keys should match the pattern used in launch-spin-stability for consistency

**Verification:** 4 of 6 club-comparison tests already passing; 2 spec tests awaiting this refactor.

---

## PGA_AVERAGES Extracted to Module-Level Constant

**Date:** 2026-03-25 | **Author:** Fenster | **Status:** Implemented

- `PGA_AVERAGES` and `DEFAULT_PGA` moved from inside `radar_comparison()` to module-level in `services/analytics.py`.
- Both `radar_comparison()` and the new `/api/analytics/pga-averages` endpoint share the same dict.
- Any future endpoint or service that needs PGA reference data should import `PGA_AVERAGES` from `services.analytics` rather than redefining it.
- The `/api/analytics/pga-averages` route is registered **before** the `<chart_type>` wildcard so Flask resolves it as a static path match. If anyone adds more `/api/analytics/...` static routes, they must also go before the wildcard.

---

## Consistent Club Colors via getClubColor()

**Date:** 2026-03-25 | **Author:** McManus | **Status:** Implemented

- Global `getClubColor(club)` function maps club names to fixed palette indices using `CANONICAL_CLUB_ORDER`.
- All 4 scatter/bar charts (carry distribution, dispersion, spin vs roll, shot shape) now use it.
- Club comparison and launch-spin-stability use their own color schemes (box plot styling, not per-club scatter).
- Radar comparison is two-dataset (user vs PGA) so does not use per-club colors.
- **Pattern rule:** Any future chart that shows per-club data points must use `getClubColor(club)` instead of `CLUB_PALETTE[i]`.
- **Impact:** Visual consistency — 7i is always the same color on every chart. No backend changes.

---

## User Directive: Strikethrough DONE Format for TODOs

**Date:** 2026-03-26 | **Author:** ersabine | **Status:** Directive

- Going forward, when a TODO item is done, mark it in TODO.md using ~~strikethrough~~ DONE format
- Replaces prior comment-based tracking
- User-requested pattern for improved visibility in task tracking
- **Impact:** Improved team readability of TODO.md — completed items are visually distinct

---

## Matrix Metadata, Shot Limit, and Print Card Data Changes (TODOs 89–92)

**Date:** 2026-03-26 | **Author:** Fenster | **Status:** Implemented

### TODO 89: Cell Metadata for Tooltips
- `build_club_matrix()` rows now include `oldest_date` (ISO string)
- `build_wedge_matrix()` cells include both `shot_count` and `oldest_date` in every non-null cell dict
- Frontend can render tooltips: `"{N} shot(s) · oldest {date}"`

### TODO 90: Shot Limit Parameter
- Both `build_club_matrix(shot_limit=N)` and `build_wedge_matrix(shot_limit=N)` accept optional parameter
- Truncates each group to N most recent shots before computing percentiles
- Routes read from `request.args` and pass to template context
- Print routes inherit shot_limit parameter through links

### TODO 91: Print Card Total Distance
- Wedge cell data shape extended: cells now include `total` (percentile of total distances)
- Fraction cells: `{carry, total, shot_count, oldest_date}`
- Clock cells: `{carry, total, max, shot_count, oldest_date}`
- Print template uses `cell.total` in `{carry}/{total}` display format

### TODO 92: Print Card Extra Clubs (8i, 9i) — LATER REVERSED
- ~~`build_wedge_matrix()` accepts `extra_full_clubs` list parameter~~
- ~~Full-swing shots for 8i and 9i are mapped to '3/3' row~~
- ~~Print routes automatically pass `extra_full_clubs=['8i', '9i']`~~
- ~~Template receives extended `wedge_clubs` variable; print CSS adjusted to fit new columns~~
- **See: Remove 8i/9i from Printed Wedge Matrix (2026-04-08)** — user reversed this decision; printed card returns to PW/AW/SW/LW only

**Verification:** 305 tests passing, zero regressions. Frontend (McManus) implements tooltip initialization, shot limit input UI, carry/total display, and column rendering.

---

## Remove 8i/9i from Printed Wedge Matrix

**Date:** 2026-04-08 | **Author:** McManus | **Status:** Implemented

**Context:** TODO 92 added 8i and 9i as extra columns on the printed wedge matrix. User has now reversed this decision.

**Changes:**
- `app.py`: Removed `extra_full_clubs=['8i', '9i']` from both `print_wedge_matrix` and `print_pocket_card` route calls to `build_wedge_matrix()`
- `app.py`: Removed dead `PRINT_WEDGE_CLUBS` import from `services.wedge_matrix`
- `services/wedge_matrix.py`: `PRINT_WEDGE_CLUBS` constant remains (available for future non-print use), but no longer imported or used by the app
- Version bumped to 0.6.2

**Rule Going Forward:** To add or remove iron columns from the printed wedge matrix, modify `extra_full_clubs` in `app.py` at the `print_wedge_matrix` and `print_pocket_card` routes. The template is fully data-driven from `wedge_clubs` — no template changes needed.

---

## Wedge Card Font Sizes Track Column Count

**Date:** 2026-04-08  
**Author:** McManus  
**Status:** Implemented  

### Context

The `#wedge-card` font sizes were reduced to `10pt`/`10.5pt` in TODO 92 to accommodate 7 columns (8i, 9i, PW, AW, SW, LW + label). After TODO 93 reverted the 8i/9i addition, the card returned to 5 columns (label + PW, AW, SW, LW) but the small fonts were not restored. This left the wedge matrix visibly smaller than the club matrix at print time.

### Decision

**The wedge card should always use the same font sizes as the club card when both have the same column count (≤5).** Font size reductions on the wedge card are only justified when column count exceeds 5.

### Rule

- ≤ 5 columns: use club-card sizes (`14pt` card, `14pt` table, `13pt` th, inherited `14pt` td)
- 6–7 columns: reduce — use `10pt`/`10.5pt` (or re-evaluate to fit)
- Any time wedge column count changes, reassess font sizes explicitly — do not leave stale small fonts from a prior column-count era

### Impact

- `print.css` updated: `#wedge-card` now matches `#club-card` sizing exactly
- No template changes needed
- Version bumped to 0.6.3

---

## Wedge Matrix Print Width = 3.4"

**Date:** 2026-03-28  
**Author:** McManus  
**Status:** Implemented  

`#wedge-card` print width increased from 2.91" to 3.4". `#club-card` remains at 2.91".

The wedge matrix has 5 print columns (swing-size label + PW + AW + SW + LW). The club matrix has 4 (Club + Carry + Total + Max). Wedge cell values like "67/67" and "99/101" are wider than the integer carry distances in the club card. At 2.91" the LW column was clipped on every row. 3.4" (~17% wider than club card) gives all 5 columns room without crowding. Both cards continue to fit on a single letter-size page with dashed cut guides.

**Rule:** Club card stays at 2.91". Wedge card stays at 3.4". Any future column additions to the wedge card (e.g., adding irons back) require a re-evaluation of this width upward, not downward.

**Version:** 0.6.4
