import numpy as np
from models.database import db, Session, Shot, ClubLoft


def percentile_value(values, percentile):
    """Compute a percentile from a list of numeric values.

    Returns None if the list is empty or all None.
    """
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return float(np.percentile(clean, percentile))


# Alias used by tests
compute_percentile = percentile_value


def compute_percentile_for_club(session_id, club_short, percentile):
    """Compute a carry percentile for a specific club, excluding excluded shots."""
    shots = Shot.query.filter(
        Shot.session_id == session_id,
        Shot.club_short == club_short,
        Shot.excluded == False,
    ).all()
    carries = [s.carry for s in shots if s.carry is not None]
    return percentile_value(carries, percentile)


def get_shots_query(session_id=None, club_short=None, swing_size=None, excluded=False, date_from=None):
    """Build a base shot query with common filters.

    By default excludes excluded shots unless excluded=None (return all).
    date_from: if set, only include shots from sessions on or after this date.
    club_short: single string or list of club names.
    """
    q = Shot.query
    if date_from is not None:
        q = q.join(Session).filter(Session.session_date >= date_from)
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)
    if club_short is not None:
        if isinstance(club_short, (list, tuple)):
            q = q.filter(Shot.club_short.in_(club_short))
        else:
            q = q.filter(Shot.club_short == club_short)
    if swing_size is not None:
        q = q.filter(Shot.swing_size == swing_size)
    if excluded is not None:
        q = q.filter(Shot.excluded == excluded)
    return q


def club_stats(session_id=None, club_short=None, percentile=75, date_from=None):
    """Compute carry, total, and max for a specific club.

    Returns dict with carry_pct, total_pct, max_total, shot_count.
    """
    shots = get_shots_query(
        session_id=session_id,
        club_short=club_short,
        excluded=False,
        date_from=date_from,
    ).all()

    carries = [s.carry for s in shots if s.carry is not None]
    totals = [s.total for s in shots if s.total is not None]

    return {
        'carry_pct': round(percentile_value(carries, percentile)) if carries else None,
        'total_pct': round(percentile_value(totals, percentile)) if totals else None,
        'max_total': round(max(totals)) if totals else None,
        'shot_count': len(shots),
    }


def per_club_statistics(session_id=None, percentile=75, date_from=None, clubs=None):
    """Compute stats for every club that has data.

    clubs: optional list of club_short names to limit to.
    """
    # Get distinct clubs in data
    q = Shot.query.with_entities(Shot.club_short).distinct()
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)
    if date_from is not None:
        q = q.join(Session).filter(Session.session_date >= date_from)
    if clubs is not None:
        q = q.filter(Shot.club_short.in_(clubs))
    all_clubs = [row[0] for row in q.all()]

    results = {}
    for c in all_clubs:
        results[c] = club_stats(session_id=session_id, club_short=c, percentile=percentile, date_from=date_from)
    return results


def flag_errant_shots(session_id, club_short=None, low_pct=10, high_pct=90):
    """Auto-flag shots with carry outside P10-P90 range per club.

    If club_short is provided, only flag shots for that club.
    Returns list of shot IDs that were flagged. Does not commit.
    """
    flagged_ids = []

    if club_short:
        club_list = [club_short]
    else:
        club_list = [
            row[0] for row in Shot.query.with_entities(Shot.club_short).filter(
                Shot.session_id == session_id
            ).distinct().all()
        ]

    for cs in club_list:
        shots = Shot.query.filter(
            Shot.session_id == session_id,
            Shot.club_short == cs,
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


def dispersion_data(session_id=None, club_short=None, date_from=None):
    """Get offline vs carry data for dispersion chart."""
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False, date_from=date_from
    ).all()
    return [
        {'carry': s.carry, 'offline': s.offline, 'club': s.club_short, 'club_short': s.club_short}
        for s in shots
        if s.carry is not None and s.offline is not None
    ]


def spin_vs_carry_data(session_id=None, club_short=None, date_from=None):
    """Get spin rate vs carry data."""
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False, date_from=date_from
    ).all()
    return [
        {'carry': s.carry, 'spin_rate': s.spin_rate, 'club': s.club_short, 'club_short': s.club_short}
        for s in shots
        if s.carry is not None and s.spin_rate is not None
    ]


def shot_shape_data(session_id=None, club_short=None, date_from=None):
    """Get face angle vs club path for shot shape analysis."""
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False, date_from=date_from
    ).all()
    return [
        {
            'face_angle': s.face_angle,
            'club_path': s.club_path,
            'club': s.club_short,
            'club_short': s.club_short,
            'diff': round(s.face_angle - s.club_path, 1) if s.face_angle is not None and s.club_path is not None else None,
        }
        for s in shots
        if s.face_angle is not None and s.club_path is not None
    ]


def per_club_stats(session_id, club_short):
    """Aggregate stats for a specific club in a session.

    Returns dict with count, min_carry, max_carry, mean_carry.
    """
    shots = Shot.query.filter(
        Shot.session_id == session_id,
        Shot.club_short == club_short,
        Shot.excluded == False,
    ).all()

    carries = [s.carry for s in shots if s.carry is not None]
    if not carries:
        return {'count': 0, 'min_carry': None, 'max_carry': None, 'mean_carry': None}

    return {
        'count': len(carries),
        'min_carry': min(carries),
        'max_carry': max(carries),
        'mean_carry': float(np.mean(carries)),
    }


def carry_distribution(session_id=None, club_short=None, date_from=None):
    """Get carry distances grouped by club for box plot / histogram."""
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False, date_from=date_from
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
