from models.database import db, Shot, ClubLoft


def assess_loft(dynamic_loft, club_short):
    """Assess a single shot's dynamic loft against the standard loft for the club.

    Returns dict with 'is_good', 'difference', 'dynamic_loft', 'standard_loft'.
    """
    club_loft = ClubLoft.query.filter_by(club_short=club_short).first()
    std_loft = club_loft.standard_loft if club_loft else None

    if dynamic_loft is None or std_loft is None:
        return {
            'is_good': None,
            'difference': None,
            'dynamic_loft': dynamic_loft,
            'standard_loft': std_loft,
        }

    diff = round(dynamic_loft - std_loft, 1)
    return {
        'is_good': dynamic_loft <= std_loft,
        'difference': diff,
        'dynamic_loft': dynamic_loft,
        'standard_loft': std_loft,
    }


def club_loft_summary(session_id, club_short):
    """Per-club loft summary for a specific session and club.

    Returns dict with 'total_shots', 'good_shots', 'bad_shots', 'good_pct'.
    """
    club_loft = ClubLoft.query.filter_by(club_short=club_short).first()
    std_loft = club_loft.standard_loft if club_loft else None

    q = Shot.query.filter(
        Shot.excluded == False,
        Shot.session_id == session_id,
        Shot.club_short == club_short,
        Shot.dynamic_loft.isnot(None),
    )
    shots = q.all()

    good = 0
    bad = 0
    for s in shots:
        if std_loft is not None and s.dynamic_loft <= std_loft:
            good += 1
        else:
            bad += 1

    total = good + bad
    pct = round(100.0 * good / total, 1) if total > 0 else 0.0

    return {
        'total_shots': total,
        'good_shots': good,
        'bad_shots': bad,
        'good_pct': pct,
    }


def analyze_loft(session_id=None, club_short=None, date_from=None):
    """Compare dynamic loft to standard loft for each shot.

    Good: dynamic_loft <= standard_loft (compression)
    Bad: dynamic_loft > standard_loft (scooping)

    Returns list of shot dicts with loft_status added.
    """
    from models.database import Session as SessionModel
    lofts = {cl.club_short: cl.standard_loft for cl in ClubLoft.query.all()}

    q = Shot.query.filter(Shot.excluded == False)
    if date_from is not None:
        q = q.join(SessionModel).filter(SessionModel.session_date >= date_from)
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)
    if club_short is not None:
        if isinstance(club_short, (list, tuple)):
            q = q.filter(Shot.club_short.in_(club_short))
        else:
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


def loft_summary(session_id=None, date_from=None):
    """Per-club summary: % of shots with good dynamic loft.

    Returns dict: {club_short: {'good': N, 'bad': N, 'total': N, 'pct_good': float}}
    """
    analysis = analyze_loft(session_id=session_id, date_from=date_from)

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
