# Skill: SQLite Index Strategy for SQLAlchemy Models

## When to Use
When a SQLAlchemy model backs a table that's queried with filters on multiple columns, especially in paginated or analytics contexts.

## Pattern
Define indexes in the model's `__table_args__` tuple. Use single-column indexes for FK and frequently filtered columns. Use composite indexes for common multi-column filter combinations.

```python
class Shot(db.Model):
    __tablename__ = 'shots'
    __table_args__ = (
        db.Index('ix_shots_session_club', 'session_id', 'club_short'),
        db.Index('ix_shots_club_excluded', 'club_short', 'excluded'),
    )
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), index=True)
    club_short = db.Column(db.Text, index=True)
    excluded = db.Column(db.Boolean, default=False, index=True)
```

## Applying to Existing DB
SQLAlchemy `db.create_all()` creates new indexes on new tables but won't retroactively add indexes to existing tables. Use raw SQL:
```python
conn.execute(text('CREATE INDEX IF NOT EXISTS ix_name ON table (col1, col2)'))
conn.commit()
```

## Rules
- Column order in composite indexes matters: put the most selective column first
- Don't index columns only used in SELECT (not WHERE/JOIN/ORDER BY)
- SQLite allows at most one index per column combo per table
- Boolean columns (like `excluded`) benefit from index when combined with other columns in composite
