### Launch-Spin Stability Response Shape Extended
**Date:** 2026-03-23 | **Author:** Fenster | **Status:** Implemented

- `launch_spin_stability()` response now includes two additional top-level fields:
  - `high_variance_clusters`: array of `{club, metric, cv, std_dev, shot_count, severity, threshold_cv}` objects identifying clubs with unusually high variance relative to other clubs.
  - Per-club entries now include `stability: {spin_std, spin_cv, launch_std, launch_cv}` alongside existing `spin`/`launch` box plot stats.
- **Backward compatible:** Existing `clubs`, `correlation` keys unchanged. Frontend can optionally consume the new fields.
- **Detection algorithm:** CV (coefficient of variation) compared against median CV across all clubs. Threshold: max(1.5× median, floor of 3.0%).
- **Impact:** McManus can highlight flagged clusters in the chart UI using the `high_variance_clusters` array and `severity` field.
