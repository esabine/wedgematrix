import numpy as np
from models.database import db, Shot, ClubLoft


def percentile_value(values, percentile):
    """Compute a percentile from a list of numeric values.

    Returns None if the list is empty or all None.
    """
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return float(np.percentile(clean, percentile))


def get_shots_query(session_id=None, club_short=None, swing_size=None, excluded=False):
    """Build a base shot query with common filters.

    By default excludes excluded shots unless excluded=None (return all).
    """
    q = Shot.query
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)
    if club_short is not None:
        q = q.filter(Shot.club_short == club_short)
    if swing_size is not None:
        q = q.filter(Shot.swing_size == swing_size)
    if excluded is not None:
        q = q.filter(Shot.excluded == excluded)
    return q


def club_stats(session_id=None, club_short=None, percentile=75):
    """Compute carry, total, and max for a specific club.

    Returns dict with carry_pct, total_pct, max_total, shot_count.
    """
    shots = get_shots_query(
        session_id=session_id,
        club_short=club_short,
        excluded=False
    ).all()

    carries = [s.carry for s in shots if s.carry is not None]
    totals = [s.total for s in shots if s.total is not None]

    return {
        'carry_pct': round(percentile_value(carries, percentile)) if carries else None,
        'total_pct': round(percentile_value(totals, percentile)) if totals else None,
        'max_total': round(max(totals)) if totals else None,
        'shot_count': len(shots),
    }


def per_club_statistics(session_id=None, percentile=75):
    """Compute stats for every club that has data."""
    # Get distinct clubs in data
    q = Shot.query.with_entities(Shot.club_short).distinct()
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)
    clubs = [row[0] for row in q.all()]

    results = {}
    for c in clubs:
        results[c] = club_stats(session_id=session_id, club_short=c, percentile=percentile)
    return results


def flag_errant_shots(session_id, low_pct=10, high_pct=90):
    """Auto-flag shots with carry outside P10-P90 range per club.

    Returns list of shot IDs that were flagged. Does not commit — caller decides.
    """
    flagged_ids = []

    clubs = Shot.query.with_entities(Shot.club_short).filter(
        Shot.session_id == session_id
    ).distinct().all()

    for (club_short,) in clubs:
        shots = Shot.query.filter(
            Shot.session_id == session_id,
            Shot.club_short == club_short,
        ).all()

        carries = [s.carry for s in shots if s.carry is not None]
        if len(carries) < 3:
            continue

        low = float(np.percentile(carries, low_pct))
        high = float(np.percentile(carries, high_pct))

        for s in shots:
            if s.carry is not None and (s.carry < low or s.carry > high):
                flagged_ids.append(s.id)

    return flagged_ids


def dispersion_data(session_id=None, club_short=None):
    """Get offline vs carry data for dispersion chart."""
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False
    ).all()
    return [
        {'carry': s.carry, 'offline': s.offline, 'club_short': s.club_short}
        for s in shots
        if s.carry is not None and s.offline is not None
    ]


def spin_vs_carry_data(session_id=None, club_short=None):
    """Get spin rate vs carry data."""
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False
    ).all()
    return [
        {'carry': s.carry, 'spin_rate': s.spin_rate, 'club_short': s.club_short}
        for s in shots
        if s.carry is not None and s.spin_rate is not None
    ]


def shot_shape_data(session_id=None, club_short=None):
    """Get face angle vs club path for shot shape analysis."""
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False
    ).all()
    return [
        {
            'face_angle': s.face_angle,
            'club_path': s.club_path,
            'club_short': s.club_short,
            'diff': round(s.face_angle - s.club_path, 1) if s.face_angle is not None and s.club_path is not None else None,
        }
        for s in shots
        if s.face_angle is not None and s.club_path is not None
    ]


def carry_distribution(session_id=None, club_short=None):
    """Get carry distances grouped by club for box plot / histogram."""
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False
    ).all()

    by_club = {}
    for s in shots:
        if s.carry is not None:
            by_club.setdefault(s.club_short, []).append(s.carry)

    result = {}
    for club, carries in by_club.items():
        carries_arr = np.array(carries)
        result[club] = {
            'values': carries,
            'min': float(np.min(carries_arr)),
            'q1': float(np.percentile(carries_arr, 25)),
            'median': float(np.percentile(carries_arr, 50)),
            'q3': float(np.percentile(carries_arr, 75)),
            'max': float(np.max(carries_arr)),
            'count': len(carries),
        }
    return result
