# Dispersion API Response Shape Change

**Date:** 2026-03-22 | **Author:** Fenster | **Status:** Implemented

## Decision

The `/api/analytics/dispersion` endpoint response changed from a flat array to an envelope:

**Before:** `[{carry, offline, club, club_short}, ...]`
**After:** `{shots: [{carry, offline, club, club_short}, ...], dispersion_boundary: {club_name: [{carry, offline}, ...]}}`

## Rationale

Adding P90 dispersion boundary data alongside the scatter points requires a structured envelope rather than a flat array. The boundary is computed per-club using convex hull + cubic spline smoothing.

## Impact

- **Frontend:** McManus already prepared `initDispersionChart()` to handle both formats (envelope and legacy array). No frontend changes needed.
- **Tests:** 4 dispersion tests updated to expect the new envelope format.
- **New dependency:** `scipy>=1.12` added to `requirements.txt` for ConvexHull and CubicSpline.
- **Any future consumer** of `/api/analytics/dispersion` must unwrap `data.shots` (not iterate `data` directly).
