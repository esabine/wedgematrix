import numpy as np
from datetime import date
from models.database import db, Session, Shot, ClubLoft
from services.analytics import percentile_value

# Canonical club ordering: Woods → Hybrids → Irons → Wedge(bare) → Wedge(compound).
# Bare names (PW, AW, SW, LW) are used by endpoints that don't split by swing type.
# Compound names (PW-full, AW-3/3, etc.) are used by club-comparison & launch-spin.
# Clubs not in this list appear at the end in alphabetical order.
CLUB_ORDER = [
    # Woods
    '1W', '3W',
    # Hybrids
    '2H', '3H', '4H',
    # Irons
    '3i', '4i', '5i', '6i', '7i', '8i', '9i',
    # Bare wedge names (carry-distribution, loft-summary, club-matrix, etc.)
    'PW', 'AW', 'SW', 'LW',
    # Wedge full swings
    'PW-full', 'AW-full', 'SW-full', 'LW-full',
    # Wedge 3/3
    'PW-3/3', 'AW-3/3', 'SW-3/3', 'LW-3/3',
    # Wedge 2/3
    'PW-2/3', 'AW-2/3', 'SW-2/3', 'LW-2/3',
    # Wedge 1/3
    'PW-1/3', 'AW-1/3', 'SW-1/3', 'LW-1/3',
    # Wedge clock positions
    'PW-10:2', 'AW-10:2', 'SW-10:2', 'LW-10:2',
    'PW-10:3', 'AW-10:3', 'SW-10:3', 'LW-10:3',
    'PW-9:3', 'AW-9:3', 'SW-9:3', 'LW-9:3',
    'PW-8:4', 'AW-8:4', 'SW-8:4', 'LW-8:4',
]

# Lookup for O(1) sort: maps label → position index
_CLUB_ORDER_MAP = {k: i for i, k in enumerate(CLUB_ORDER)}


def club_sort_key(label):
    """Sort key function: CLUB_ORDER position first, then alphabetical for unknowns."""
    idx = _CLUB_ORDER_MAP.get(label)
    if idx is not None:
        return (0, idx, label)
    return (1, 0, label)


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


def build_club_matrix(session_id=None, percentile=75, include_test=False,
                      shot_limit=None):
    """Build the club matrix: Club | Carry | Total | Max.

    Args:
        session_id: Filter to single session, or None for all sessions.
        percentile: Which percentile to use (default P75).
        include_test: When False and session_id is None, exclude test sessions.
        shot_limit: When set, use only the N most recent shots per club.

    Returns list of dicts ordered by standard loft (Driver → LW).
    Each row includes shot_count and oldest_date for tooltip metadata.
    """
    q = Shot.query.filter(Shot.excluded == False)
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)
    elif not include_test:
        q = q.join(Session).filter(Session.is_test == False)

    shots = q.all()

    date_lookup = _session_date_lookup(shots)

    # Group by club_short
    by_club = {}
    for s in shots:
        by_club.setdefault(s.club_short, []).append(s)

    lofts = {cl.club_short: cl.standard_loft for cl in ClubLoft.query.all()}

    matrix = []
    for club in CLUB_ORDER:
        if club not in by_club:
            continue

        club_shots = by_club[club]
        if shot_limit:
            club_shots = _limit_recent(club_shots, shot_limit, date_lookup)

        carries = [s.carry for s in club_shots if s.carry is not None]
        totals = [s.total for s in club_shots if s.total is not None]

        carry_pct = round(percentile_value(carries, percentile)) if carries else None
        total_pct = round(percentile_value(totals, percentile)) if totals else None
        max_total = round(max(totals)) if totals else None

        matrix.append({
            'club': club,
            'club_short': club,
            'standard_loft': lofts.get(club),
            'carry': carry_pct,
            'total': total_pct,
            'max': max_total,
            'shot_count': len(club_shots),
            'oldest_date': _oldest_date(club_shots, date_lookup),
        })

    return matrix


# Alias for test compatibility
generate_club_matrix = build_club_matrix
