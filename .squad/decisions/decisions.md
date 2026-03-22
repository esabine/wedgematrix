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
