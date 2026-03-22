# Batch 7 Results (TODOs 67-70)

**Date:** 2026-03-23 | **Batch:** 7 | **TODOs:** 67-70 | **Status:** Complete

## Fenster (Backend)

### TODO 67: Per-Club Stability Metrics
- **Added:** Coefficient of variation (CV) + standard deviation for spin rate and launch angle
- **Feature:** High-variance cluster detection flags clubs with CV > 1.5× median or absolute floor of 3.0%
- **Response shape:** `launch_spin_stability()` includes `high_variance_clusters` array with `{club, metric, cv, std_dev, shot_count, severity, threshold_cv}` and per-club `stability` dict
- **Impact:** Frontend can highlight flagged clusters in chart UI using severity levels
- **Tests:** 12 new tests for stability metrics (CV calculation, thresholds, cluster detection)

### TODO 68: PGA Tour Averages Complete
- **Verified:** `PGA_AVERAGES` covers all 14 clubs (3W, 5W, 7W, 3H, 4H, 3I–9I, PW, AW, SW, LW)
- **Data fields:** carry, spin, launch angle, ball speed, dispersion (σ offline per club)
- **Added to response:** `clubs_used` field in radar-comparison response (list of clubs with data)
- **Tests:** 8 new tests for PGA average verification and radar envelope format

### TODO 70: Dispersion Boundary Always P90
- **Implementation:** `compute_dispersion_boundary()` hardcodes `BOUNDARY_PERCENTILE = 90`
- **Behavior:** Boundary always represents P90 of displayed shots, regardless of percentile selector
- **Scatter points:** All non-excluded shots shown (no percentile filtering)
- **Rationale:** P90 is a stable boundary that doesn't shift with user's percentile choice; provides realistic dispersion area representation
- **Tests:** 8 new tests for P90 boundary verification and percentile parameter handling

## McManus (Frontend)

### TODO 69: Carry Gapping Badge Repositioning
- **Change:** Moved gap badges from above individual bars to positioned between adjacent bars
- **Visual:** Bracket connector lines from badge edges to both bar tops establish relationship
- **Y-axis:** Added `grace: '15%'` to provide headroom for above-bar badges
- **Tooltip:** Bidirectional gap information shown on hover
- **Pattern rule:** Any future chart annotation for relationships must position between related elements, not on single element

## Hockney (Tests)

### Test Suite Results
- **New tests:** 32 (12 stability + 8 PGA averages + 4 gapping regression + 8 P90 boundary)
- **Total suite:** 212+ tests passing
- **Pre-existing:** Loft failures unchanged (6 test failures in `test_dispersion_boundary.py` from Pythagorean carry correction noted in Decision 22)
- **Coverage:** Stability thresholds, CV calculations, high-variance detection, PGA average completeness, radar envelope format, P90 boundary computation, percentile parameter handling

## Architecture Decisions Finalized

1. **Stability metrics** now documented as part of launch-spin stability API (Decision 21 extended)
2. **PGA averages** comprehensive coverage confirmed for all clubs (Decision 13 validated)
3. **Dispersion boundary logic** simplified: always P90, no percentile parameter dependency (Decision 20 updated)
4. **Chart annotation pattern:** Between-element positioning is now standard for relational indicators

## Files Modified

**Backend:**
- `services/analytics.py` — stability metrics, boundary P90 hardcoding
- `models/club_matrix.py` — PGA averages verification
- Tests in `tests/test_analytics.py` — 28 new tests

**Frontend:**
- `templates/radar_comparison.html` — gapping badge repositioning
- `static/js/charts.js` — bracket connector rendering, Y-axis grace adjustment

**Configuration:**
- `requirements.txt` — scipy dependency already present for ConvexHull/CubicSpline

## Next Steps

- Batch 8: Address pre-existing loft test failures by updating test seed data for Pythagorean carry correction
- Ongoing: Monitor PGA average drift as more tournament data is available
- Documentation: Add user-facing note about dispersion boundary minimum shot threshold (Decision 20)
