# Project Context

- **Owner:** ersabine
- **Project:** wedgeMatrix — Golf launch monitor analytics app with percentile-based club/wedge matrices and pocket card printing
- **Stack:** Python 3.11+, Flask, SQLite/SQLAlchemy, Pandas/NumPy, Bootstrap 5, Chart.js
- **Created:** 2026-03-14

## Core Context

Agent Scribe maintains orchestration logs, session logs, decision archives, and team history. Responsibilities include:
- Write orchestration logs per agent spawn (template + outcome summary)
- Maintain session logs for batch work
- Merge inbox decisions into canonical decisions.md, deduplicating
- Archive old decisions when decisions.md exceeds ~20KB
- Append team updates to affected agents' history.md
- Manage git commits for .squad/ directory changes

## Recent Updates

📌 Team initialized on 2026-03-14
📌 Team cast from The Usual Suspects: Keaton (Lead), Fenster (Backend), McManus (Frontend), Hockney (Tester)
📌 Batch 11 completed (2026-03-26): Fenster + McManus implemented TODOs 89–92 (matrix metadata, shot limit, print enhancements, 8i/9i columns)
📌 2026-04-08: McManus reverted 8i/9i column addition from printed wedge matrix per user request

## Learnings

- Initial setup complete — standard orchestration workflow established
- Decision merging: identify duplicates by date/author, preserve implementation status, add cross-agent notes where relevant
- Orchestration logs: brief outcome summary, metrics (tests passing), technical impact, commit reference
- History updates: append to existing learnings, reference cross-agent dependencies, note verification status

### 2026-04-11 — Fenster Shotpattern Export Row Limit Documentation
- **Task:** Orchestrate completion of Fenster's shotpattern CSV export row-limiting feature
- **Actions:** Wrote orchestration log (2026-04-11T034913Z-fenster.md), session log (2026-04-11T034913Z-shotpattern-row-limit.md), merged decision inbox into decisions.md (new "Shotpattern CSV Export Row Limit" entry), updated Fenster's history.md with learnings
- **Outcome:** All squad documentation synchronized. Decision archived. No manual edits or conflicts.
