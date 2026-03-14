import numpy as np
from models.database import db, Shot, ClubLoft
from services.analytics import percentile_value

# Club ordering by standard loft (ascending = Driver first → LW last)
CLUB_ORDER = ['1W', '3W', '2H', '3H', '4i', '5i', '6i', '7i', '8i', '9i', 'PW', 'AW', 'SW', 'LW']


def build_club_matrix(session_id=None, percentile=75):
    """Build the club matrix: Club | Carry | Total | Max.

    Args:
        session_id: Filter to single session, or None for all sessions.
        percentile: Which percentile to use (default P75).

    Returns list of dicts ordered by standard loft (Driver → LW).
    Only includes clubs that have non-excluded shot data.
    """
    # Build base query — only non-excluded shots with swing_size='full' or any swing_size
    q = Shot.query.filter(Shot.excluded == False)
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)

    shots = q.all()

    # Group by club_short
    by_club = {}
    for s in shots:
        by_club.setdefault(s.club_short, []).append(s)

    # Get loft data for ordering
    lofts = {cl.club_short: cl.standard_loft for cl in ClubLoft.query.all()}

    matrix = []
    for club in CLUB_ORDER:
        if club not in by_club:
            continue

        club_shots = by_club[club]
        carries = [s.carry for s in club_shots if s.carry is not None]
        totals = [s.total for s in club_shots if s.total is not None]

        carry_pct = round(percentile_value(carries, percentile)) if carries else None
        total_pct = round(percentile_value(totals, percentile)) if totals else None
        max_total = round(max(totals)) if totals else None

        matrix.append({
            'club': club,
            'standard_loft': lofts.get(club),
            'carry': carry_pct,
            'total': total_pct,
            'max': max_total,
            'shot_count': len(club_shots),
        })

    return matrix
