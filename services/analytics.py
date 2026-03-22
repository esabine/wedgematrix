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


def get_shots_query(session_id=None, club_short=None, swing_size=None, excluded=False, date_from=None, include_test=False):
    """Build a base shot query with common filters.

    By default excludes excluded shots unless excluded=None (return all).
    date_from: if set, only include shots from sessions on or after this date.
    club_short: single string or list of club names.
    include_test: when False and session_id is None, exclude shots from test sessions.
    """
    q = Shot.query
    needs_session_join = False

    if date_from is not None or (not include_test and session_id is None):
        needs_session_join = True

    if needs_session_join:
        q = q.join(Session)
        if date_from is not None:
            q = q.filter(Session.session_date >= date_from)
        if not include_test and session_id is None:
            q = q.filter(Session.is_test == False)

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
    """Get spin rate vs roll distance data (roll = total - carry)."""
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False, date_from=date_from
    ).all()
    return [
        {
            'roll': round(s.total - s.carry, 1),
            'spin_rate': s.spin_rate,
            'club': s.club_short,
            'club_short': s.club_short,
        }
        for s in shots
        if s.carry is not None and s.total is not None and s.spin_rate is not None
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


def detect_outliers(session_id=None, club_short=None, date_from=None, iqr_multiplier=1.5):
    """Identify statistical outliers per club using IQR method.

    Flags shots whose carry distance or offline (direction) falls outside
    Q1 - multiplier*IQR .. Q3 + multiplier*IQR for their club.

    Args:
        session_id: optional session filter.
        club_short: optional club filter (string or list).
        date_from: optional date cutoff.
        iqr_multiplier: IQR scaling factor (default 1.5).

    Returns dict keyed by club_short, each value a list of outlier dicts:
        {shot_id, reasons: [...], carry, offline, carry_bounds, direction_bounds}
    """
    shots = get_shots_query(
        session_id=session_id, club_short=club_short,
        excluded=False, date_from=date_from,
    ).all()

    by_club = {}
    for s in shots:
        by_club.setdefault(s.club_short, []).append(s)

    result = {}
    for club_name, club_shots in by_club.items():
        # Track outlier reasons per shot_id
        outlier_map = {}  # shot_id -> {shot, reasons, ...}

        # --- Carry distance IQR ---
        carries = [(s, s.carry) for s in club_shots if s.carry is not None]
        if len(carries) >= 4:
            vals = np.array([c for _, c in carries])
            q1, q3 = float(np.percentile(vals, 25)), float(np.percentile(vals, 75))
            iqr = q3 - q1
            lower, upper = q1 - iqr_multiplier * iqr, q3 + iqr_multiplier * iqr
            carry_bounds = {'lower': round(lower, 1), 'upper': round(upper, 1)}
            for s, val in carries:
                if val < lower or val > upper:
                    outlier_map[s.id] = {
                        'shot_id': s.id,
                        'reasons': ['carry distance outlier'],
                        'carry': val,
                        'offline': s.offline,
                        'carry_bounds': carry_bounds,
                        'direction_bounds': None,
                    }

        # --- Direction (offline) IQR ---
        offlines = [(s, s.offline) for s in club_shots if s.offline is not None]
        if len(offlines) >= 4:
            vals = np.array([o for _, o in offlines])
            q1, q3 = float(np.percentile(vals, 25)), float(np.percentile(vals, 75))
            iqr = q3 - q1
            lower, upper = q1 - iqr_multiplier * iqr, q3 + iqr_multiplier * iqr
            dir_bounds = {'lower': round(lower, 1), 'upper': round(upper, 1)}
            for s, val in offlines:
                if val < lower or val > upper:
                    if s.id in outlier_map:
                        outlier_map[s.id]['reasons'].append('direction outlier')
                        outlier_map[s.id]['direction_bounds'] = dir_bounds
                    else:
                        outlier_map[s.id] = {
                            'shot_id': s.id,
                            'reasons': ['direction outlier'],
                            'carry': s.carry,
                            'offline': val,
                            'carry_bounds': None,
                            'direction_bounds': dir_bounds,
                        }

        if outlier_map:
            result[club_name] = list(outlier_map.values())

    return result


def carry_distribution(session_id=None, club_short=None, date_from=None, percentile=75):
    """Get carry distances grouped by club for box plot / histogram.

    percentile: the upper percentile to include (default P75).
    Returns dict keyed by club with box plot stats and gapping data.
    """
    from services.club_matrix import CLUB_ORDER

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
            'q3': float(np.percentile(carries_arr, percentile)),
            'max': float(np.max(carries_arr)),
            'count': len(carries),
            'percentile': percentile,
            'gap': None,  # computed below
        }

    # Compute gapping: distance difference between adjacent clubs in CLUB_ORDER
    # Gap = this club's q3 carry minus the next shorter club's q3 carry
    ordered_clubs = [c for c in CLUB_ORDER if c in result]
    for i, club in enumerate(ordered_clubs):
        if i < len(ordered_clubs) - 1:
            next_club = ordered_clubs[i + 1]
            this_q3 = result[club]['q3']
            next_q3 = result[next_club]['q3']
            if this_q3 is not None and next_q3 is not None:
                result[club]['gap'] = round(this_q3 - next_q3, 1)

    return result


def _box_plot_stats(values):
    """Compute box plot statistics: min, q1, median, q3, max, mean, outliers (IQR method)."""
    arr = np.array(values, dtype=float)
    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    median = float(np.percentile(arr, 50))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    whisker_low = float(np.min(arr[arr >= lower_fence])) if np.any(arr >= lower_fence) else float(np.min(arr))
    whisker_high = float(np.max(arr[arr <= upper_fence])) if np.any(arr <= upper_fence) else float(np.max(arr))
    outliers = [round(float(v), 2) for v in arr if v < lower_fence or v > upper_fence]

    return {
        'min': round(whisker_low, 2),
        'q1': round(q1, 2),
        'median': round(median, 2),
        'q3': round(q3, 2),
        'max': round(whisker_high, 2),
        'mean': round(float(np.mean(arr)), 2),
        'iqr': round(iqr, 2),
        'outliers': outliers,
        'count': len(values),
    }


def launch_spin_stability(session_id=None, club_short=None, date_from=None, percentile=75):
    """Compute launch-spin stability box plot data per club.

    For each club, returns box plot stats for spin and launch.
    High-variance clubs get additional attack_angle and ball_speed stats,
    plus a stability analysis.

    Returns {clubs: {club: {spin, launch, high_variance, analysis, ...}}, correlation: str}
    matching the frontend initLaunchSpinStability() contract.
    """
    from services.club_matrix import CLUB_ORDER

    shots = get_shots_query(
        session_id=session_id, club_short=club_short,
        excluded=False, date_from=date_from,
    ).all()

    by_club = {}
    for s in shots:
        by_club.setdefault(s.club_short, []).append(s)

    result = {}
    high_var_notes = []
    for club_name, club_shots in by_club.items():
        spins = [s.spin_rate for s in club_shots if s.spin_rate is not None]
        launches = [s.launch_angle for s in club_shots if s.launch_angle is not None]

        if len(spins) < 3 or len(launches) < 3:
            continue

        spin_stats = _box_plot_stats(spins)
        launch_stats = _box_plot_stats(launches)

        entry = {
            'club': club_name,
            'spin': spin_stats,
            'launch': launch_stats,
            'shot_count': len(club_shots),
            'high_variance': False,
            'analysis': None,
        }

        # Check for high variance: IQR > median * 0.3
        spin_high_var = spin_stats['iqr'] > spin_stats['median'] * 0.3 if spin_stats['median'] else False
        launch_high_var = launch_stats['iqr'] > launch_stats['median'] * 0.3 if launch_stats['median'] else False

        if spin_high_var or launch_high_var:
            entry['high_variance'] = True

            # Add attack angle and ball speed stats for diagnosis
            attacks = [s.attack_angle for s in club_shots if s.attack_angle is not None]
            speeds = [s.ball_speed for s in club_shots if s.ball_speed is not None]

            if len(attacks) >= 3:
                entry['attack_angle'] = _box_plot_stats(attacks)
            if len(speeds) >= 3:
                entry['ball_speed'] = _box_plot_stats(speeds)

            # Diagnose: high ball speed variance → poor strike quality,
            # high attack angle variance → mechanical inconsistency
            speed_var = entry.get('ball_speed', {}).get('iqr', 0)
            speed_median = entry.get('ball_speed', {}).get('median', 1)
            attack_var = entry.get('attack_angle', {}).get('iqr', 0)
            attack_median = abs(entry.get('attack_angle', {}).get('median', 1)) or 1

            speed_relative_var = speed_var / speed_median if speed_median else 0
            attack_relative_var = attack_var / attack_median if attack_median else 0

            if speed_relative_var > attack_relative_var:
                entry['analysis'] = 'Ball speed variance dominates — likely poor strike quality'
                high_var_notes.append(f'{club_name}: poor strike quality (ball speed variance)')
            elif attack_relative_var > 0:
                entry['analysis'] = 'Attack angle variance dominates — mechanical inconsistency'
                high_var_notes.append(f'{club_name}: mechanical inconsistency (attack angle variance)')
            else:
                entry['analysis'] = 'Source undetermined — review swing video'

        result[club_name] = entry

    # Sort by CLUB_ORDER
    ordered = {}
    for c in CLUB_ORDER:
        if c in result:
            ordered[c] = result[c]
    for c in result:
        if c not in ordered:
            ordered[c] = result[c]

    # Build correlation summary
    total_clubs = len(ordered)
    high_var_count = sum(1 for v in ordered.values() if v.get('high_variance'))
    if total_clubs == 0:
        correlation = ''
    elif high_var_count == 0:
        correlation = f'All {total_clubs} clubs show stable launch-spin patterns.'
    else:
        correlation = f'{high_var_count} of {total_clubs} clubs show high variance. ' + '; '.join(high_var_notes)

    return {'clubs': ordered, 'correlation': correlation}


def radar_comparison(session_id=None, club_short=None, date_from=None, percentile=75):
    """Compute radar chart metrics for user data vs PGA Tour averages.

    Aggregates across all matching clubs and returns the format expected by
    initRadarComparison(): {axes, user: {values, raw}, pga: {values, raw}}.
    Uses the percentile parameter for user carry/speed calculations.
    """

    # PGA Tour averages by club (published reference data)
    PGA_AVERAGES = {
        '1W': {'carry': 275, 'smash_factor': 1.49, 'spin_rate': 2686, 'launch_angle': 10.9, 'ball_speed': 171, 'dispersion': 25},
        '3W': {'carry': 243, 'smash_factor': 1.47, 'spin_rate': 3655, 'launch_angle': 9.2, 'ball_speed': 158, 'dispersion': 20},
        '2H': {'carry': 227, 'smash_factor': 1.44, 'spin_rate': 4437, 'launch_angle': 10.2, 'ball_speed': 152, 'dispersion': 18},
        '3H': {'carry': 220, 'smash_factor': 1.43, 'spin_rate': 4630, 'launch_angle': 10.5, 'ball_speed': 148, 'dispersion': 17},
        '4i': {'carry': 210, 'smash_factor': 1.41, 'spin_rate': 4836, 'launch_angle': 11.0, 'ball_speed': 143, 'dispersion': 15},
        '5i': {'carry': 200, 'smash_factor': 1.39, 'spin_rate': 5361, 'launch_angle': 12.1, 'ball_speed': 137, 'dispersion': 13},
        '6i': {'carry': 189, 'smash_factor': 1.37, 'spin_rate': 6231, 'launch_angle': 14.1, 'ball_speed': 132, 'dispersion': 11},
        '7i': {'carry': 172, 'smash_factor': 1.33, 'spin_rate': 7097, 'launch_angle': 16.3, 'ball_speed': 120, 'dispersion': 8},
        '8i': {'carry': 160, 'smash_factor': 1.31, 'spin_rate': 7998, 'launch_angle': 18.1, 'ball_speed': 115, 'dispersion': 7},
        '9i': {'carry': 148, 'smash_factor': 1.29, 'spin_rate': 8647, 'launch_angle': 20.4, 'ball_speed': 109, 'dispersion': 6},
        'PW': {'carry': 136, 'smash_factor': 1.27, 'spin_rate': 9316, 'launch_angle': 24.2, 'ball_speed': 102, 'dispersion': 5},
        'AW': {'carry': 118, 'smash_factor': 1.25, 'spin_rate': 9900, 'launch_angle': 25.0, 'ball_speed': 93, 'dispersion': 6},
        'SW': {'carry': 97, 'smash_factor': 1.22, 'spin_rate': 10200, 'launch_angle': 27.5, 'ball_speed': 82, 'dispersion': 7},
        'LW': {'carry': 82, 'smash_factor': 1.19, 'spin_rate': 10400, 'launch_angle': 30.0, 'ball_speed': 72, 'dispersion': 8},
    }
    DEFAULT_PGA = {'carry': 172, 'smash_factor': 1.33, 'spin_rate': 7097, 'launch_angle': 16.3, 'ball_speed': 120, 'dispersion': 8}

    shots = get_shots_query(
        session_id=session_id, club_short=club_short,
        excluded=False, date_from=date_from,
    ).all()

    by_club = {}
    for s in shots:
        by_club.setdefault(s.club_short, []).append(s)

    if not by_club:
        return {}

    # Collect per-club scores and raw values, then average across clubs
    metric_keys = ['carry', 'dispersion', 'spin_rate', 'launch_angle', 'ball_speed']
    axis_labels = {'carry': 'Carry', 'dispersion': 'Dispersion',
                   'spin_rate': 'Spin Rate', 'launch_angle': 'Launch Angle',
                   'ball_speed': 'Ball Speed'}
    # higher_is_better flags per metric
    higher_better = {'carry': True, 'dispersion': False,
                     'spin_rate': False, 'launch_angle': True, 'ball_speed': True}

    per_club_scores = {k: [] for k in metric_keys}
    per_club_raw = {k: [] for k in metric_keys}
    per_club_pga = {k: [] for k in metric_keys}

    def normalize(user_val, pga_val, higher_is_better=True):
        if user_val is None or pga_val is None or pga_val == 0:
            return None
        ratio = user_val / pga_val
        score = ratio * 100
        if not higher_is_better:
            score = (2 - ratio) * 100 if ratio <= 2 else 0
        return round(min(max(score, 0), 150), 1)

    for club_name, club_shots in by_club.items():
        carries = [s.carry for s in club_shots if s.carry is not None]
        offlines = [abs(s.offline) for s in club_shots if s.offline is not None]
        spins = [s.spin_rate for s in club_shots if s.spin_rate is not None]
        launches = [s.launch_angle for s in club_shots if s.launch_angle is not None]
        speeds = [s.ball_speed for s in club_shots if s.ball_speed is not None]

        if not carries:
            continue

        pga = PGA_AVERAGES.get(club_name, DEFAULT_PGA)

        # Use percentile for carry and speed; median for angle/spin/dispersion
        user_carry = float(np.percentile(carries, percentile)) if carries else None
        user_dispersion = float(np.percentile(offlines, 50)) if offlines else None
        user_spin = float(np.percentile(spins, 50)) if spins else None
        user_launch = float(np.percentile(launches, 50)) if launches else None
        user_speed = float(np.percentile(speeds, percentile)) if speeds else None

        vals = {'carry': user_carry, 'dispersion': user_dispersion,
                'spin_rate': user_spin, 'launch_angle': user_launch,
                'ball_speed': user_speed}

        for k in metric_keys:
            score = normalize(vals[k], pga[k], higher_better[k])
            if score is not None:
                per_club_scores[k].append(score)
            if vals[k] is not None:
                per_club_raw[k].append(vals[k])
            per_club_pga[k].append(pga[k])

    # Build aggregated axes, user values, and PGA values
    axes = []
    user_values = []
    user_raw = {}
    pga_values = []
    pga_raw = {}

    for k in metric_keys:
        label = axis_labels[k]
        axes.append(label)

        if per_club_scores[k]:
            avg_score = round(float(np.mean(per_club_scores[k])), 1)
            user_values.append(avg_score)
        else:
            user_values.append(None)

        if per_club_raw[k]:
            avg_raw = round(float(np.mean(per_club_raw[k])), 1)
            user_raw[label] = avg_raw
        else:
            user_raw[label] = None

        if per_club_pga[k]:
            pga_values.append(100)  # PGA is always the 100 reference
            pga_raw[label] = round(float(np.mean(per_club_pga[k])), 1)
        else:
            pga_values.append(100)
            pga_raw[label] = None

    return {
        'axes': axes,
        'user': {'values': user_values, 'raw': user_raw},
        'pga': {'values': pga_values, 'raw': pga_raw},
    }
