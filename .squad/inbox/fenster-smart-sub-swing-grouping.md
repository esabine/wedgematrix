# Decision Proposal: Smart Sub-Swing Grouping

**Author:** Fenster | **Date:** 2026-03-23 | **TODOs:** 74, 75

## Context

TODOs 74 and 75 require wedge clubs (PW, AW, SW, LW) to be broken down by swing size in launch-spin-stability and club-comparison charts.

## Decision

Wedge clubs are only split into sub-swing entries (e.g., `PW-3/3`, `PW-full`) when the session data contains **multiple swing types** for that club. If a wedge club has only one swing type, it keeps its plain name (e.g., `PW`).

## Rationale

- **Backward compatibility:** Existing tests and frontend code that reference `PW` continue to work when users haven't imported fractional swing data.
- **UX clarity:** Showing `PW-full` when there's only one swing type is confusing — there's nothing to differentiate it from.
- **Consistent behavior:** Non-wedge clubs always show as plain names. This makes wedge behavior match when there's no subdivision to show.

## Impact

- `app.py` club-comparison handler uses `wedge_swing_types` dict to detect multi-swing clubs
- `analytics.py` `launch_spin_stability()` uses same pattern
- Frontend: labels may be `PW` or `PW-3/3` depending on data — tooltip/legend code should handle both
