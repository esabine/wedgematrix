from models.database import db, Shot, ClubLoft


def analyze_loft(session_id=None, club_short=None):
    """Compare dynamic loft to standard loft for each shot.

    Good: dynamic_loft <= standard_loft (compression)
    Bad: dynamic_loft > standard_loft (scooping)

    Returns list of shot dicts with loft_status added.
    """
    lofts = {cl.club_short: cl.standard_loft for cl in ClubLoft.query.all()}

    q = Shot.query.filter(Shot.excluded == False)
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)
    if club_short is not None:
        q = q.filter(Shot.club_short == club_short)

    shots = q.all()
    results = []
    for s in shots:
        std_loft = lofts.get(s.club_short)
        if s.dynamic_loft is None or std_loft is None:
            status = 'unknown'
        elif s.dynamic_loft <= std_loft:
            status = 'good'
        else:
            status = 'bad'

        results.append({
            'id': s.id,
            'club_short': s.club_short,
            'dynamic_loft': s.dynamic_loft,
            'standard_loft': std_loft,
            'loft_diff': round(s.dynamic_loft - std_loft, 1) if s.dynamic_loft is not None and std_loft is not None else None,
            'status': status,
        })

    return results


def loft_summary(session_id=None):
    """Per-club summary: % of shots with good dynamic loft.

    Returns dict: {club_short: {'good': N, 'bad': N, 'total': N, 'pct_good': float}}
    """
    analysis = analyze_loft(session_id=session_id)

    by_club = {}
    for shot in analysis:
        club = shot['club_short']
        if club not in by_club:
            by_club[club] = {'good': 0, 'bad': 0, 'unknown': 0, 'total': 0}
        by_club[club][shot['status']] += 1
        by_club[club]['total'] += 1

    for club, data in by_club.items():
        scoreable = data['good'] + data['bad']
        data['pct_good'] = round(100.0 * data['good'] / scoreable, 1) if scoreable > 0 else None

    return by_club
