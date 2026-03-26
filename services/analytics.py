import numpy as np
from scipy.spatial import ConvexHull
from scipy.interpolate import CubicSpline
from models.database import db, Session, Shot, ClubLoft


def percentile_value(values, percentile):
    """Compute a percentile from a list of numeric values.

    Returns None if the list is empty or all None.
    """
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return float(np.percentile(clean, percentile))


# PGA Tour averages by club (published reference data).
# Used by radar_comparison() and the /api/analytics/pga-averages endpoint.
PGA_AVERAGES = {
    '1W': {'carry': 275, 'spin_rate': 2686, 'launch_angle': 10.9, 'ball_speed': 171, 'dispersion': 25},
    '3W': {'carry': 243, 'spin_rate': 3655, 'launch_angle': 9.2, 'ball_speed': 158, 'dispersion': 20},
    '2H': {'carry': 227, 'spin_rate': 4437, 'launch_angle': 10.2, 'ball_speed': 152, 'dispersion': 18},
    '3H': {'carry': 220, 'spin_rate': 4630, 'launch_angle': 10.5, 'ball_speed': 148, 'dispersion': 17},
    '4i': {'carry': 210, 'spin_rate': 4836, 'launch_angle': 11.0, 'ball_speed': 143, 'dispersion': 15},
    '5i': {'carry': 200, 'spin_rate': 5361, 'launch_angle': 12.1, 'ball_speed': 137, 'dispersion': 13},
    '6i': {'carry': 189, 'spin_rate': 6231, 'launch_angle': 14.1, 'ball_speed': 132, 'dispersion': 11},
    '7i': {'carry': 172, 'spin_rate': 7097, 'launch_angle': 16.3, 'ball_speed': 120, 'dispersion': 8},
    '8i': {'carry': 160, 'spin_rate': 7998, 'launch_angle': 18.1, 'ball_speed': 115, 'dispersion': 7},
    '9i': {'carry': 148, 'spin_rate': 8647, 'launch_angle': 20.4, 'ball_speed': 109, 'dispersion': 6},
    'PW': {'carry': 136, 'spin_rate': 9316, 'launch_angle': 24.2, 'ball_speed': 102, 'dispersion': 5},
    'AW': {'carry': 118, 'spin_rate': 9900, 'launch_angle': 25.0, 'ball_speed': 93, 'dispersion': 6},
    'SW': {'carry': 97, 'spin_rate': 10200, 'launch_angle': 27.5, 'ball_speed': 82, 'dispersion': 7},
    'LW': {'carry': 82, 'spin_rate': 10400, 'launch_angle': 30.0, 'ball_speed': 72, 'dispersion': 8},
}
DEFAULT_PGA = {'carry': 172, 'spin_rate': 7097, 'launch_angle': 16.3, 'ball_speed': 120, 'dispersion': 8}


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


def _pythagorean_forward(carry, offline):
    """Correct carry distance to true forward distance via Pythagorean theorem.

    CSV carry is the hypotenuse (total ball travel distance).
    True forward = sqrt(carry² - offline²).
    Returns None for invalid data (carry <= 0 or |offline| >= carry).
    """
    if carry is None or offline is None or carry <= 0:
        return None
    if offline == 0:
        return float(carry)
    carry_sq = carry ** 2
    off_sq = offline ** 2
    if off_sq >= carry_sq:
        return None
    return float(np.sqrt(carry_sq - off_sq))


def dispersion_data(session_id=None, club_short=None, date_from=None):
    """Get offline vs corrected-carry data for dispersion chart.

    Carry from CSV is the hypotenuse (total ball travel).  The y-axis
    needs the true forward distance: sqrt(carry² - offline²).
    Each point includes tooltip fields: spin_rate, launch_angle, ball_speed, face_angle.
    """
    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False, date_from=date_from
    ).all()
    result = []
    for s in shots:
        forward = _pythagorean_forward(s.carry, s.offline)
        if forward is None:
            continue
        result.append({
            'carry': round(forward, 1),
            'offline': s.offline,
            'club': s.club_short,
            'club_short': s.club_short,
            'spin_rate': s.spin_rate,
            'launch_angle': s.launch_angle,
            'ball_speed': s.ball_speed,
            'face_angle': s.face_angle,
        })
    return result


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
    from services.club_matrix import club_sort_key
    ordered_clubs = sorted(result.keys(), key=club_sort_key)
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


def _coefficient_of_variation(values):
    """Coefficient of variation (std / mean * 100). Returns None if mean is zero."""
    arr = np.array(values, dtype=float)
    mean = float(np.mean(arr))
    if abs(mean) < 1e-10:
        return None
    return round(float(np.std(arr, ddof=1) / abs(mean) * 100), 2) if len(arr) > 1 else 0.0


def _build_stability_entry(label, group_shots):
    """Build a single stability entry for a club or club+swing_type group.

    Returns None if insufficient data (< 3 spin or launch values).
    """
    spins = [s.spin_rate for s in group_shots if s.spin_rate is not None]
    launches = [s.launch_angle for s in group_shots if s.launch_angle is not None]

    if len(spins) < 3 or len(launches) < 3:
        return None

    spin_stats = _box_plot_stats(spins)
    launch_stats = _box_plot_stats(launches)

    spin_cv = _coefficient_of_variation(spins)
    launch_cv = _coefficient_of_variation(launches)
    spin_std = round(float(np.std(spins, ddof=1)), 2) if len(spins) > 1 else 0.0
    launch_std = round(float(np.std(launches, ddof=1)), 2) if len(launches) > 1 else 0.0

    entry = {
        'club': label,
        'spin': spin_stats,
        'launch': launch_stats,
        'stability': {
            'spin_std': spin_std,
            'spin_cv': spin_cv,
            'launch_std': launch_std,
            'launch_cv': launch_cv,
        },
        'shot_count': len(group_shots),
        'high_variance': False,
        'analysis': None,
    }

    # Check for high variance: IQR > median * 0.3
    spin_high_var = spin_stats['iqr'] > spin_stats['median'] * 0.3 if spin_stats['median'] else False
    launch_high_var = launch_stats['iqr'] > launch_stats['median'] * 0.3 if launch_stats['median'] else False

    if spin_high_var or launch_high_var:
        entry['high_variance'] = True

        attacks = [s.attack_angle for s in group_shots if s.attack_angle is not None]
        speeds = [s.ball_speed for s in group_shots if s.ball_speed is not None]

        if len(attacks) >= 3:
            entry['attack_angle'] = _box_plot_stats(attacks)
        if len(speeds) >= 3:
            entry['ball_speed'] = _box_plot_stats(speeds)

        speed_var = entry.get('ball_speed', {}).get('iqr', 0)
        speed_median = entry.get('ball_speed', {}).get('median', 1)
        attack_var = entry.get('attack_angle', {}).get('iqr', 0)
        attack_median = abs(entry.get('attack_angle', {}).get('median', 1)) or 1

        speed_relative_var = speed_var / speed_median if speed_median else 0
        attack_relative_var = attack_var / attack_median if attack_median else 0

        if speed_relative_var > attack_relative_var:
            entry['analysis'] = 'Ball speed variance dominates — likely poor strike quality'
        elif attack_relative_var > 0:
            entry['analysis'] = 'Attack angle variance dominates — mechanical inconsistency'
        else:
            entry['analysis'] = 'Source undetermined — review swing video'

    return entry, spin_cv, launch_cv


def launch_spin_stability(session_id=None, club_short=None, date_from=None, percentile=75):
    """Compute launch-spin stability metrics per club.

    Wedge clubs (PW, AW, SW, LW) are broken down by swing_type so
    mixing full swings with partial swings doesn't falsely inflate variance.
    Non-wedge clubs are reported as-is.

    Returns:
        {
          clubs: {label: {spin, launch, stability, high_variance, analysis, ...}},
          correlation: str,
          high_variance_clusters: [{club, metric, cv, std_dev, shot_count, severity}, ...]
        }
    """
    from services.club_matrix import CLUB_ORDER
    from services.wedge_matrix import WEDGE_CLUBS

    shots = get_shots_query(
        session_id=session_id, club_short=club_short,
        excluded=False, date_from=date_from,
    ).all()

    # Group shots: non-wedge by club, wedge by club+swing_size
    groups = {}
    for s in shots:
        if s.club_short in WEDGE_CLUBS:
            label = f'{s.club_short}-{s.swing_size}'
            groups.setdefault(label, []).append(s)
        else:
            groups.setdefault(s.club_short, []).append(s)

    result = {}
    high_var_notes = []
    all_spin_cvs = {}
    all_launch_cvs = {}

    for label, group_shots in groups.items():
        built = _build_stability_entry(label, group_shots)
        if built is None:
            continue

        entry, spin_cv, launch_cv = built

        if spin_cv is not None:
            all_spin_cvs[label] = spin_cv
        if launch_cv is not None:
            all_launch_cvs[label] = launch_cv

        if entry['high_variance'] and entry['analysis']:
            high_var_notes.append(f'{label}: {entry["analysis"]}')

        result[label] = entry

    # --- High-variance cluster detection ---
    high_variance_clusters = []

    def _detect_clusters(cv_dict, metric_label):
        if len(cv_dict) < 2:
            return
        cv_vals = list(cv_dict.values())
        median_cv = float(np.median(cv_vals))
        threshold = max(median_cv * 1.5, 3.0)
        for lbl, cv in cv_dict.items():
            if cv > threshold:
                severity = 'moderate' if cv < threshold * 2 else 'high'
                entry = result.get(lbl, {})
                entry['high_variance'] = True
                high_variance_clusters.append({
                    'club': lbl,
                    'metric': metric_label,
                    'cv': cv,
                    'std_dev': entry.get('stability', {}).get(
                        f'{metric_label}_std', None),
                    'shot_count': entry.get('shot_count', 0),
                    'severity': severity,
                    'threshold_cv': round(threshold, 2),
                })

    _detect_clusters(all_spin_cvs, 'spin')
    _detect_clusters(all_launch_cvs, 'launch')

    # Sort by canonical CLUB_ORDER (handles both bare and compound labels)
    from services.club_matrix import club_sort_key
    ordered = {}
    for key in sorted(result.keys(), key=club_sort_key):
        ordered[key] = result[key]

    # Build correlation summary
    total_entries = len(ordered)
    high_var_count = sum(1 for v in ordered.values() if v.get('high_variance'))
    if total_entries == 0:
        correlation = ''
    elif high_var_count == 0:
        correlation = f'All {total_entries} entries show stable launch-spin patterns.'
    else:
        correlation = f'{high_var_count} of {total_entries} entries show high variance. ' + '; '.join(high_var_notes)

    return {
        'clubs': ordered,
        'correlation': correlation,
        'high_variance_clusters': high_variance_clusters,
    }


def radar_comparison(session_id=None, club_short=None, date_from=None, percentile=75):
    """Compute per-club comparison of user data vs PGA Tour averages.

    Returns per-club breakdown AND an aggregated radar so the frontend
    can show both a summary radar and a per-club side-by-side comparison.

    Response:
        {
          axes: ['Carry', 'Dispersion', 'Spin Rate', 'Launch Angle', 'Ball Speed'],
          per_club: {club: {user: {...}, pga: {...}, scores: {...}, shot_count}},
          user: {values: [...], raw: {...}},
          pga:  {values: [...], raw: {...}},
          clubs_used: [...]
        }
    """
    from services.club_matrix import CLUB_ORDER

    shots = get_shots_query(
        session_id=session_id, club_short=club_short,
        excluded=False, date_from=date_from,
    ).all()

    by_club = {}
    for s in shots:
        by_club.setdefault(s.club_short, []).append(s)

    if not by_club:
        return {}

    metric_keys = ['carry', 'dispersion', 'spin_rate', 'launch_angle', 'ball_speed']
    axis_labels = {'carry': 'Carry', 'dispersion': 'Dispersion',
                   'spin_rate': 'Spin Rate', 'launch_angle': 'Launch Angle',
                   'ball_speed': 'Ball Speed'}
    higher_better = {'carry': True, 'dispersion': False,
                     'spin_rate': False, 'launch_angle': True, 'ball_speed': True}

    def normalize(user_val, pga_val, hib=True):
        if user_val is None or pga_val is None or pga_val == 0:
            return None
        ratio = user_val / pga_val
        score = ratio * 100
        if not hib:
            score = (2 - ratio) * 100 if ratio <= 2 else 0
        return round(min(max(score, 0), 150), 1)

    per_club = {}
    agg_scores = {k: [] for k in metric_keys}
    agg_user_raw = {k: [] for k in metric_keys}
    agg_pga_raw = {k: [] for k in metric_keys}

    for club_name, club_shots in by_club.items():
        carries = [s.carry for s in club_shots if s.carry is not None]
        offlines = [abs(s.offline) for s in club_shots if s.offline is not None]
        spins = [s.spin_rate for s in club_shots if s.spin_rate is not None]
        launches = [s.launch_angle for s in club_shots if s.launch_angle is not None]
        speeds = [s.ball_speed for s in club_shots if s.ball_speed is not None]

        if not carries:
            continue

        pga = PGA_AVERAGES.get(club_name, DEFAULT_PGA)

        user_vals = {
            'carry': round(float(np.percentile(carries, percentile)), 1) if carries else None,
            'dispersion': round(float(np.percentile(offlines, 50)), 1) if offlines else None,
            'spin_rate': round(float(np.median(spins)), 1) if spins else None,
            'launch_angle': round(float(np.median(launches)), 1) if launches else None,
            'ball_speed': round(float(np.percentile(speeds, percentile)), 1) if speeds else None,
        }

        scores = {}
        for k in metric_keys:
            scores[k] = normalize(user_vals[k], pga[k], higher_better[k])
            if scores[k] is not None:
                agg_scores[k].append(scores[k])
            if user_vals[k] is not None:
                agg_user_raw[k].append(user_vals[k])
            agg_pga_raw[k].append(pga[k])

        per_club[club_name] = {
            'user': user_vals,
            'pga': {k: pga[k] for k in metric_keys},
            'scores': scores,
            'shot_count': len(club_shots),
        }

    # Sort per_club by CLUB_ORDER
    from services.club_matrix import club_sort_key
    ordered_per_club = {c: per_club[c] for c in sorted(per_club.keys(), key=club_sort_key)}

    # Build aggregated summary
    axes = [axis_labels[k] for k in metric_keys]
    user_values = []
    user_raw = {}
    pga_values = []
    pga_raw = {}

    for k in metric_keys:
        label = axis_labels[k]
        user_values.append(round(float(np.mean(agg_scores[k])), 1) if agg_scores[k] else None)
        user_raw[label] = round(float(np.mean(agg_user_raw[k])), 1) if agg_user_raw[k] else None
        pga_values.append(100)
        pga_raw[label] = round(float(np.mean(agg_pga_raw[k])), 1) if agg_pga_raw[k] else None

    return {
        'axes': axes,
        'per_club': ordered_per_club,
        'user': {'values': user_values, 'raw': user_raw},
        'pga': {'values': pga_values, 'raw': pga_raw},
        'clubs_used': list(ordered_per_club.keys()),
    }


def compute_dispersion_boundary(session_id=None, club_short=None, date_from=None,
                                percentile=75, num_smooth_points=60):
    """Compute a smoothed convex hull boundary for P90 dispersion per club.

    The boundary always represents the 90th percentile of all displayed shots,
    regardless of what `percentile` value the user has selected in the UI.
    The percentile parameter is accepted for API compatibility but does not
    affect the boundary computation.

    Returns dict keyed by club_short: list of {carry, offline} boundary points.
    Clubs with fewer than 3 valid shots or collinear points are omitted.
    """
    BOUNDARY_PERCENTILE = 90  # Always P90 for the dispersion boundary

    shots = get_shots_query(
        session_id=session_id, club_short=club_short, excluded=False, date_from=date_from
    ).all()

    # Group shots by club, applying Pythagorean correction to carry
    by_club = {}
    for s in shots:
        forward = _pythagorean_forward(s.carry, s.offline)
        if forward is not None:
            by_club.setdefault(s.club_short, []).append((forward, s.offline))

    boundaries = {}
    for club, points in by_club.items():
        carries = [p[0] for p in points]
        if len(carries) < 3:
            continue

        # Filter to shots within the P90 range (symmetric around median)
        low_pct = (100 - BOUNDARY_PERCENTILE) / 2
        high_pct = 100 - low_pct
        carry_low = float(np.percentile(carries, low_pct))
        carry_high = float(np.percentile(carries, high_pct))

        filtered = [(c, o) for c, o in points if carry_low <= c <= carry_high]
        if len(filtered) < 3:
            continue

        # Also filter offline to P90 range
        offlines = [p[1] for p in filtered]
        off_low = float(np.percentile(offlines, low_pct))
        off_high = float(np.percentile(offlines, high_pct))
        filtered = [(c, o) for c, o in filtered if off_low <= o <= off_high]
        if len(filtered) < 3:
            continue

        pts = np.array(filtered)

        # Check for collinearity: if all points lie on a line, skip
        if pts.shape[0] >= 3:
            centered = pts - pts.mean(axis=0)
            # Singular value decomposition — if smallest SV ≈ 0, points are collinear
            _, sv, _ = np.linalg.svd(centered, full_matrices=False)
            if sv[-1] < 1e-10:
                continue

        try:
            hull = ConvexHull(pts)
        except Exception:
            continue

        # Extract hull vertices in order and close the loop
        hull_indices = list(hull.vertices)
        hull_pts = pts[hull_indices]

        # Sort hull points by angle from centroid for proper polygon ordering
        centroid = hull_pts.mean(axis=0)
        angles = np.arctan2(hull_pts[:, 1] - centroid[1],
                            hull_pts[:, 0] - centroid[0])
        order = np.argsort(angles)
        hull_pts = hull_pts[order]

        # Close the loop
        hull_closed = np.vstack([hull_pts, hull_pts[0:1]])

        if len(hull_pts) < 3:
            # Not enough unique hull vertices for spline smoothing
            boundary = [
                {'carry': round(float(p[0]), 1), 'offline': round(float(p[1]), 1)}
                for p in hull_closed
            ]
            boundaries[club] = boundary
            continue

        # Parameterize by cumulative chord length
        diffs = np.diff(hull_closed, axis=0)
        seg_lengths = np.sqrt((diffs ** 2).sum(axis=1))
        t = np.zeros(len(hull_closed))
        t[1:] = np.cumsum(seg_lengths)
        t_max = t[-1]
        if t_max < 1e-10:
            continue

        # Cubic spline (periodic) on carry and offline separately
        cs_carry = CubicSpline(t, hull_closed[:, 0], bc_type='periodic')
        cs_offline = CubicSpline(t, hull_closed[:, 1], bc_type='periodic')

        t_smooth = np.linspace(0, t_max, num_smooth_points, endpoint=False)
        smooth_carry = cs_carry(t_smooth)
        smooth_offline = cs_offline(t_smooth)

        # Close the smoothed loop
        boundary = [
            {'carry': round(float(smooth_carry[i]), 1),
             'offline': round(float(smooth_offline[i]), 1)}
            for i in range(len(t_smooth))
        ]
        # Close the loop by appending the first point
        boundary.append(boundary[0].copy())
        boundaries[club] = boundary

    return boundaries
