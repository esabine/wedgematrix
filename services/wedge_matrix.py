import numpy as np
from datetime import date
from models.database import db, Session, Shot
from services.analytics import percentile_value

# Swing sizes in display order (4/4 removed; fractions renamed x/3)
SWING_SIZES = ['3/3', '2/3', '1/3', '10:2', '10:3', '9:3', '8:4']

# Fraction sizes show Carry only; clock-hand sizes show Carry/Max
FRACTION_SIZES = {'3/3', '2/3', '1/3'}
CLOCK_SIZES = {'10:2', '10:3', '9:3', '8:4'}

# Wedge matrix clubs — PW first, then AW, SW, LW
WEDGE_CLUBS = ['PW', 'AW', 'SW', 'LW']

# Extended club list for the printed pocket card
PRINT_WEDGE_CLUBS = ['8i', '9i', 'PW', 'AW', 'SW', 'LW']


def export_club_name(club_short):
    """Translate internal club_short to export-friendly name."""
    if club_short == '1W':
        return 'Dr'
    if club_short.endswith('H'):
        return club_short[:-1] + 'Hy'
    return club_short


def _session_date_lookup(shots):
    """Build {session_id: session_date} lookup from a list of shots."""
    sids = {s.session_id for s in shots}
    if not sids:
        return {}
    return {sess.id: sess.session_date
            for sess in Session.query.filter(Session.id.in_(sids)).all()}


def _limit_recent(shots, shot_limit, date_lookup):
    """Sort shots most-recent-first and return the top N."""
    shots.sort(
        key=lambda s: (date_lookup.get(s.session_id) or date.min, s.id),
        reverse=True,
    )
    return shots[:shot_limit]


def _oldest_date(shots, date_lookup):
    """Return the oldest session date (ISO string) among a list of shots."""
    dates = [date_lookup.get(s.session_id) for s in shots
             if date_lookup.get(s.session_id) is not None]
    return min(dates).isoformat() if dates else None


def build_wedge_matrix(session_id=None, percentile=75, include_test=False,
                       shot_limit=None, extra_full_clubs=None):
    """Build the wedge matrix: Swing Size × Clubs.

    Fraction sizes (3/3, 2/3, 1/3): cell = {'carry': N, 'total': T, ...}
    Clock sizes (10:2, 10:3, 9:3, 8:4): cell = {'carry': N, 'total': T, 'max': M, ...}
    Empty cell = None

    Each cell also includes shot_count and oldest_date for tooltip metadata.

    Args:
        session_id: Filter to single session, or None for all.
        percentile: Which percentile to use (default P75).
        include_test: When False and session_id is None, exclude test sessions.
        shot_limit: When set, use only the N most recent shots per cell.
        extra_full_clubs: List of clubs (e.g. ['8i', '9i']) whose full-swing
                          shots are included and mapped to the '3/3' row.

    Returns:
        {
            'swing_sizes': ['3/3', ...],
            'clubs': ['PW', 'AW', 'SW', 'LW'] (or extended list),
            'matrix': {
                '3/3': {'PW': {'carry': 100, 'total': 105, ...}, ...},
                ...
            }
        }
    """
    # Determine which clubs to include
    clubs = list(WEDGE_CLUBS)
    extra = list(extra_full_clubs) if extra_full_clubs else []
    if extra:
        clubs = extra + clubs

    # Query wedge shots (non-full swing) for standard wedge clubs
    q = Shot.query.filter(
        Shot.excluded == False,
        Shot.club_short.in_(WEDGE_CLUBS),
        Shot.swing_size != 'full',
    )
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)
    elif not include_test:
        q = q.join(Session).filter(Session.is_test == False)

    shots = q.all()

    # Query full-swing shots for extra clubs (8i, 9i, etc.)
    if extra:
        eq = Shot.query.filter(
            Shot.excluded == False,
            Shot.club_short.in_(extra),
            Shot.swing_size == 'full',
        )
        if session_id is not None:
            eq = eq.filter(Shot.session_id == session_id)
        elif not include_test:
            eq = eq.join(Session).filter(Session.is_test == False)
        shots.extend(eq.all())

    date_lookup = _session_date_lookup(shots)

    # Group by (swing_size, club_short), mapping old fraction names
    SWING_RENAME = {'3/4': '3/3', '2/4': '2/3', '1/4': '1/3'}
    grouped = {}
    for s in shots:
        size = SWING_RENAME.get(s.swing_size, s.swing_size)
        # Map extra clubs' full swing to '3/3'
        if s.club_short in extra and size == 'full':
            size = '3/3'
        key = (size, s.club_short)
        grouped.setdefault(key, []).append(s)

    matrix = {}
    for size in SWING_SIZES:
        row = {}
        for club in clubs:
            key = (size, club)
            club_shots = grouped.get(key, [])

            if not club_shots:
                row[club] = None
                continue

            if shot_limit:
                club_shots = _limit_recent(list(club_shots), shot_limit, date_lookup)

            carries = [s.carry for s in club_shots if s.carry is not None]
            totals = [s.total for s in club_shots if s.total is not None]

            if not carries:
                row[club] = None
                continue

            carry_pct = round(percentile_value(carries, percentile))
            total_pct = round(percentile_value(totals, percentile)) if totals else None
            cell_meta = {
                'carry': carry_pct,
                'total': total_pct,
                'shot_count': len(club_shots),
                'oldest_date': _oldest_date(club_shots, date_lookup),
            }

            if size not in FRACTION_SIZES:
                cell_meta['max'] = round(max(carries))

            row[club] = cell_meta

        matrix[size] = row

    return {
        'swing_sizes': SWING_SIZES,
        'clubs': clubs,
        'matrix': matrix,
    }


# Alias that returns just the matrix dict (keyed by swing_size) for simpler access
def generate_wedge_matrix(session_id=None, percentile=75, include_test=False):
    result = build_wedge_matrix(session_id=session_id, percentile=percentile, include_test=include_test)
    return result['matrix']
