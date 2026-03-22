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
