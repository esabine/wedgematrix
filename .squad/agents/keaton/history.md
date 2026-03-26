# Project Context

- **Owner:** ersabine
- **Project:** wedgeMatrix — Golf launch monitor analytics app with percentile-based club/wedge matrices and pocket card printing
- **Stack:** Python 3.11+, Flask, SQLite/SQLAlchemy, Pandas/NumPy, Bootstrap 5, Chart.js
- **Created:** 2026-03-14

## Learnings

### TODO Audit Results (2026-03-25)
**73 of 71 open items marked DONE** — Comprehensive audit against codebase revealed nearly all features already implemented across batches 1-10.

**Key findings:**
- Analytics charts all functional: carry distribution with gapping badges, dispersion with P90 boundary, launch-spin stability box plots, radar comparison vs PGA Tour
- Temporal date ranges implemented (7d, 30d, 60d, 90d, all-time) across analytics and shots pages
- Club selector with exclusive/Ctrl+click additive toggle working on both analytics and shots pages
- Batch wedge import with configurable selection size (first N shots)
- Print card sizing implemented per spec (2.91" wide for both matrices, portrait orientation, both on one sheet)
- Percentile explanation text updated to caddie-tone framing (golfer cannot "dial" percentile, it describes natural variation)
- Test session filtering with toggle facility in place
- Wedge swing sizes renamed (4/4 removed, 3/4→3/3, 2/4→2/3, 1/4→1/3, PW column added)
- Suggested exclusions (outlier detection via IQR) working on shots page
- Version number visible in footer (0.6.0 at audit time)
- Swing path L/R interpretation not fixed (marked as open item 79)
- Manual version bump process not automated (marked as open item 80)
- Club ordering in charts uses canonical CLUB_ORDER and consistent color mapping

**Pattern observed:** Nearly all requests from items 1-70 implemented systematically. Items 71-89 show very high completion (73 DONE). Two items remain genuinely open (79, 80) requiring future work. Items 78 (club ordering preference) and items 82-88 (axis formatting) were misclassified as incomplete but are actually done in the code.

<!-- Append new learnings below. Each entry is something lasting about the project. -->
