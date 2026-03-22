### Dispersion Boundary Always Uses P90 Regardless of Percentile Selector
**Date:** 2026-03-23 | **Author:** Fenster | **Status:** Implemented

- `compute_dispersion_boundary()` now hardcodes `BOUNDARY_PERCENTILE = 90` internally.
- The `percentile` query parameter is accepted for API compatibility but does not change the boundary hull computation.
- Scatter dots (`dispersion_data()`) always show ALL non-excluded shots with no percentile filtering.
- Boundary = P90 of all displayed shots, always.
- **Impact:** Frontend sees the same API shape. Boundary is now wider (P90 vs old P75 default), which better represents the true dispersion area.
- **Supersedes behavior from Decision 19:** The old code used the `percentile` param to filter shots before hull. Now boundary is always P90.
