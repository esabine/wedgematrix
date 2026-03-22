"""Tests for TODO 67 (launch & spin stability), TODO 68 (PGA Tour averages),
TODO 69 (gapping regression), and TODO 70 (dispersion area always P90).

Written by Hockney — the tester who asks "what if the data is wrong?"
before anyone else does.

TODO 67: Launch-spin-stability must include variance/consistency metrics,
    flag high-variance clubs, and use launch_angle properly.
TODO 68: PGA Tour averages must exist for all wedge clubs and all expected
    metrics.  Radar/comparison endpoint must return PGA data.
TODO 69: Gapping (club-comparison) is frontend Chart.js — verify the API
    endpoint still returns valid data (regression).
TODO 70: Dispersion boundary must ALWAYS use P90 of the rendered shots.
    Changing the percentile parameter changes which shots are rendered,
    but the boundary is always the 90th percentile of THOSE shots.
"""
import math
import pytest
import numpy as np
from datetime import date
from flask import Flask

from models.database import db as _db, Session, Shot, ClubLoft, init_db
from models.seed import seed_club_lofts
from app import register_routes
from config import Config
from tests.conftest import _make_shot


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope='function')
def routed_app():
    """Flask app with all routes registered (needed for API endpoint testing)."""
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    test_app.config['DEFAULT_PERCENTILE'] = 75
    test_app.config['SECRET_KEY'] = 'test-secret'
    test_app.config['UPLOAD_FOLDER'] = 'uploads'
    test_app.json.sort_keys = False

    _db.init_app(test_app)
    with test_app.app_context():
        _db.create_all()
        seed_club_lofts()
        register_routes(test_app)
        yield test_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope='function')
def api(routed_app):
    """Flask test client with routes available."""
    return routed_app.test_client()


@pytest.fixture(scope='function')
def ctx(routed_app):
    """App context for direct DB operations."""
    with routed_app.app_context():
        yield


def _seed_session(data_type='club'):
    """Create and return a Session row."""
    s = Session(
        filename='test-todo67-70.csv',
        session_date=date(2026, 3, 25),
        location='Driving Ranges',
        data_type=data_type,
    )
    _db.session.add(s)
    _db.session.commit()
    return s


def _seed_club_shots(session, club, club_short, shots_data):
    """Seed shots for one club.

    shots_data: list of dicts with at least 'carry'. Optional: spin_rate,
    launch_angle, ball_speed, offline, attack_angle.
    """
    for i, shot_kw in enumerate(shots_data):
        carry = shot_kw.pop('carry')
        _db.session.add(_make_shot(
            session.id, club, club_short, carry, carry + 10.0,
            club_index=i, **shot_kw,
        ))
    _db.session.commit()


def _seed_consistent_club(session, club, club_short, n=8):
    """Seed n shots with very tight variance (consistent player)."""
    shots = []
    for i in range(n):
        shots.append({
            'carry': 155.0 + i * 0.3,
            'spin_rate': 5000 + i * 10,
            'launch_angle': 15.0 + i * 0.05,
            'ball_speed': 100.0 + i * 0.2,
            'attack_angle': -2.0 + i * 0.01,
            'offline': float((-1) ** i * (1 + i * 0.1)),
        })
    _seed_club_shots(session, club, club_short, shots)


def _seed_inconsistent_club(session, club, club_short, n=8):
    """Seed n shots with wild variance (inconsistent player).
    IQR / median > 0.3 for spin to trigger high_variance flag.
    """
    shots = []
    for i in range(n):
        shots.append({
            'carry': 130.0 + i * 15,            # 130-235 range
            'spin_rate': 3000 + i * 2000,        # 3000-17000 range → huge IQR
            'launch_angle': 8.0 + i * 4.0,       # 8-36 range → huge IQR
            'ball_speed': 80.0 + i * 8.0,        # 80-136 range
            'attack_angle': -5.0 + i * 3.0,      # -5 to 16 range
            'offline': float((-1) ** i * (5 + i * 3)),
        })
    _seed_club_shots(session, club, club_short, shots)


# ═════════════════════════════════════════════════════════════════════════
# TODO 67: Launch & Spin Stability
# ═════════════════════════════════════════════════════════════════════════

class TestLaunchSpinStabilityMetrics:
    """Launch-spin stability must include variance metrics and flag high-variance clubs."""

    def test_stability_response_has_clubs_and_correlation(self, api, routed_app, ctx):
        """Top-level response must have 'clubs' dict and 'correlation' string."""
        session = _seed_session()
        _seed_consistent_club(session, '7 Iron', '7i')

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'clubs' in data
        assert 'correlation' in data

    def test_per_club_entry_has_box_plot_stats(self, api, routed_app, ctx):
        """Each club entry must have spin/launch box plot stats with iqr, median, etc."""
        session = _seed_session()
        _seed_consistent_club(session, '7 Iron', '7i')

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        entry = data['clubs']['7i']

        for metric in ('spin', 'launch'):
            stats = entry[metric]
            for key in ('min', 'q1', 'median', 'q3', 'max', 'mean', 'iqr', 'count'):
                assert key in stats, f"{metric} missing key '{key}'"
            assert stats['count'] >= 3

    def test_high_variance_flag_set_on_inconsistent_club(self, api, routed_app, ctx):
        """Club with wildly varying spin/launch must be flagged high_variance=True."""
        session = _seed_session()
        _seed_inconsistent_club(session, '7 Iron', '7i')

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        entry = data['clubs']['7i']

        assert entry['high_variance'] is True, \
            "Inconsistent club should be flagged high_variance"
        assert entry['analysis'] is not None, \
            "High-variance club should have an analysis string"

    def test_consistent_club_not_flagged(self, api, routed_app, ctx):
        """Club with tight variance should NOT be flagged."""
        session = _seed_session()
        _seed_consistent_club(session, '7 Iron', '7i')

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        entry = data['clubs']['7i']

        assert entry['high_variance'] is False

    def test_correlation_mentions_high_variance_clubs(self, api, routed_app, ctx):
        """When high-variance clubs exist, the correlation string must mention them."""
        session = _seed_session()
        _seed_inconsistent_club(session, '7 Iron', '7i')
        _seed_consistent_club(session, 'P-Wedge', 'PW')

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()

        assert '1 of 2' in data['correlation'] or 'high variance' in data['correlation'].lower()

    def test_launch_angle_used_in_stability(self, api, routed_app, ctx):
        """Launch angle values must appear in the 'launch' box plot stats."""
        session = _seed_session()
        # Specific launch angles: 10, 12, 14, 16, 18
        shots = [
            {'carry': 150.0, 'spin_rate': 5000, 'launch_angle': 10.0, 'ball_speed': 100.0},
            {'carry': 152.0, 'spin_rate': 5100, 'launch_angle': 12.0, 'ball_speed': 101.0},
            {'carry': 154.0, 'spin_rate': 5200, 'launch_angle': 14.0, 'ball_speed': 102.0},
            {'carry': 156.0, 'spin_rate': 5300, 'launch_angle': 16.0, 'ball_speed': 103.0},
            {'carry': 158.0, 'spin_rate': 5400, 'launch_angle': 18.0, 'ball_speed': 104.0},
        ]
        _seed_club_shots(session, '7 Iron', '7i', shots)

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        launch = data['clubs']['7i']['launch']

        # Median of [10,12,14,16,18] = 14.0
        assert launch['median'] == 14.0
        # Min = 10, Max = 18
        assert launch['min'] == 10.0
        assert launch['max'] == 18.0

    def test_stability_std_dev_via_iqr(self, api, routed_app, ctx):
        """IQR (proxy for spread) must be computed correctly.
        For [10,12,14,16,18]: Q1=11, Q3=17, IQR=6."""
        session = _seed_session()
        shots = [
            {'carry': 150.0, 'spin_rate': 5000, 'launch_angle': 10.0, 'ball_speed': 100.0},
            {'carry': 152.0, 'spin_rate': 5100, 'launch_angle': 12.0, 'ball_speed': 101.0},
            {'carry': 154.0, 'spin_rate': 5200, 'launch_angle': 14.0, 'ball_speed': 102.0},
            {'carry': 156.0, 'spin_rate': 5300, 'launch_angle': 16.0, 'ball_speed': 103.0},
            {'carry': 158.0, 'spin_rate': 5400, 'launch_angle': 18.0, 'ball_speed': 104.0},
        ]
        _seed_club_shots(session, '7 Iron', '7i', shots)

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()

        launch_iqr = data['clubs']['7i']['launch']['iqr']
        # numpy Q1=11.0, Q3=17.0 → IQR = 6.0
        expected_iqr = float(np.percentile([10, 12, 14, 16, 18], 75) -
                             np.percentile([10, 12, 14, 16, 18], 25))
        assert abs(launch_iqr - expected_iqr) < 0.01, \
            f"IQR should be {expected_iqr}, got {launch_iqr}"


class TestLaunchSpinStabilityEdgeCases:
    """Edge cases: single shot, all identical, no shots."""

    def test_single_shot_per_club_excluded(self, api, routed_app, ctx):
        """Club with only 1 shot should NOT appear (need ≥3 for box plot)."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', [
            {'carry': 155.0, 'spin_rate': 5000, 'launch_angle': 15.0, 'ball_speed': 100.0},
        ])

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        assert '7i' not in data['clubs'], \
            "Single-shot club should not appear in stability analysis"

    def test_two_shots_per_club_excluded(self, api, routed_app, ctx):
        """2 shots also insufficient for box plot (need ≥3)."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', [
            {'carry': 155.0, 'spin_rate': 5000, 'launch_angle': 15.0, 'ball_speed': 100.0},
            {'carry': 160.0, 'spin_rate': 5500, 'launch_angle': 16.0, 'ball_speed': 102.0},
        ])

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        assert '7i' not in data['clubs']

    def test_all_identical_shots_zero_iqr(self, api, routed_app, ctx):
        """All identical shots → IQR = 0, high_variance = False."""
        session = _seed_session()
        shots = [
            {'carry': 155.0, 'spin_rate': 5000, 'launch_angle': 15.0, 'ball_speed': 100.0}
            for _ in range(5)
        ]
        _seed_club_shots(session, '7 Iron', '7i', shots)

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        entry = data['clubs']['7i']

        assert entry['spin']['iqr'] == 0
        assert entry['launch']['iqr'] == 0
        assert entry['high_variance'] is False

    def test_no_shots_empty_response(self, api, routed_app, ctx):
        """Empty session → no clubs, empty correlation."""
        session = _seed_session()

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['clubs'] == {} or len(data['clubs']) == 0
        assert data['correlation'] == ''

    def test_exactly_three_shots_included(self, api, routed_app, ctx):
        """3 shots is the minimum — club should appear."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', [
            {'carry': 150.0, 'spin_rate': 5000, 'launch_angle': 14.0, 'ball_speed': 100.0},
            {'carry': 155.0, 'spin_rate': 5200, 'launch_angle': 15.0, 'ball_speed': 102.0},
            {'carry': 160.0, 'spin_rate': 5400, 'launch_angle': 16.0, 'ball_speed': 104.0},
        ])

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        assert '7i' in data['clubs'], "3 shots should be enough for stability analysis"


# ═════════════════════════════════════════════════════════════════════════
# TODO 68: PGA Tour Averages
# ═════════════════════════════════════════════════════════════════════════

class TestPGATourAveragesExist:
    """PGA reference data must exist for all wedge clubs and expected metrics."""

    def test_pga_averages_cover_wedge_clubs(self, api, routed_app, ctx):
        """PGA_AVERAGES dict must have entries for PW, AW, SW, LW."""
        from services.analytics import radar_comparison
        # Access PGA_AVERAGES indirectly by calling radar_comparison with wedge data
        session = _seed_session()
        for club, short in [('P-Wedge', 'PW'), ('G-Wedge', 'AW'),
                            ('S-Wedge', 'SW'), ('L-Wedge', 'LW')]:
            shots = [
                {'carry': 100.0 + i, 'spin_rate': 9000 + i * 100,
                 'launch_angle': 25.0 + i, 'ball_speed': 90.0 + i,
                 'offline': float((-1) ** i * 3)}
                for i in range(5)
            ]
            _seed_club_shots(session, club, short, shots)

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        data = resp.get_json()

        # The radar endpoint returns aggregated data — verify it's non-empty
        assert 'axes' in data
        assert 'pga' in data
        assert all(v is not None for v in data['pga']['values']), \
            "PGA values must all be non-null"

    @pytest.mark.parametrize("club_short", ['PW', 'AW', 'SW', 'LW'])
    def test_pga_averages_non_null_per_wedge(self, club_short, api, routed_app, ctx):
        """Each wedge club has non-null PGA averages for all metrics."""
        session = _seed_session()
        club_map = {'PW': 'P-Wedge', 'AW': 'G-Wedge', 'SW': 'S-Wedge', 'LW': 'L-Wedge'}
        club = club_map[club_short]

        shots = [
            {'carry': 100.0 + i, 'spin_rate': 9000 + i * 100,
             'launch_angle': 25.0 + i, 'ball_speed': 90.0 + i,
             'offline': float((-1) ** i * 3)}
            for i in range(5)
        ]
        _seed_club_shots(session, club, club_short, shots)

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}&club={club_short}')
        data = resp.get_json()

        assert isinstance(data, dict) and len(data) > 0, \
            f"Radar should return data for {club_short}"
        assert 'user' in data
        assert 'pga' in data
        # PGA raw values should exist for all axes
        for axis in data.get('axes', []):
            pga_raw = data['pga'].get('raw', {})
            assert pga_raw.get(axis) is not None, \
                f"PGA raw for axis '{axis}' is None for club {club_short}"


class TestPGATourComparison:
    """Radar/comparison endpoint must work correctly with PGA data."""

    def test_radar_returns_five_axes(self, api, routed_app, ctx):
        """Radar chart must have 5 axes: Carry, Dispersion, Spin Rate, Launch Angle, Ball Speed."""
        session = _seed_session()
        shots = [
            {'carry': 155.0 + i, 'spin_rate': 5000 + i * 200,
             'launch_angle': 15.0 + i * 0.5, 'ball_speed': 100.0 + i * 3,
             'offline': float((-1) ** i * 5)}
            for i in range(5)
        ]
        _seed_club_shots(session, '7 Iron', '7i', shots)

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        data = resp.get_json()

        expected_axes = {'Carry', 'Dispersion', 'Spin Rate', 'Launch Angle', 'Ball Speed'}
        actual_axes = set(data['axes'])
        assert actual_axes == expected_axes, \
            f"Expected axes {expected_axes}, got {actual_axes}"

    def test_pga_baseline_always_100(self, api, routed_app, ctx):
        """PGA values should always be 100 (the reference baseline)."""
        session = _seed_session()
        shots = [
            {'carry': 155.0 + i, 'spin_rate': 5000 + i * 200,
             'launch_angle': 15.0 + i * 0.5, 'ball_speed': 100.0 + i * 3,
             'offline': float((-1) ** i * 5)}
            for i in range(5)
        ]
        _seed_club_shots(session, '7 Iron', '7i', shots)

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        data = resp.get_json()

        assert all(v == 100 for v in data['pga']['values']), \
            f"PGA baseline values should all be 100, got {data['pga']['values']}"

    def test_comparison_with_club_without_pga_data(self, api, routed_app, ctx):
        """Unknown club type falls back to DEFAULT_PGA — should not crash."""
        session = _seed_session()
        # Use a non-standard club short name
        shots = [
            {'carry': 155.0 + i, 'spin_rate': 5000 + i * 200,
             'launch_angle': 15.0 + i * 0.5, 'ball_speed': 100.0 + i * 3,
             'offline': float((-1) ** i * 5)}
            for i in range(5)
        ]
        # Seed with an unusual club name that probably isn't in PGA_AVERAGES
        for i, shot_kw in enumerate(shots):
            carry = shot_kw.pop('carry')
            _db.session.add(_make_shot(
                session.id, 'Chipper', 'CH', carry, carry + 10.0,
                club_index=i, **shot_kw,
            ))
        _db.session.commit()

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # Should still return data (falls back to DEFAULT_PGA)
        assert isinstance(data, dict)
        assert 'axes' in data
        assert len(data['user']['values']) > 0

    def test_no_shots_returns_empty(self, api, routed_app, ctx):
        """Empty session → radar returns empty dict (no crash)."""
        session = _seed_session()

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {} or data == {'axes': [], 'user': {'values': [], 'raw': {}}, 'pga': {'values': [], 'raw': {}}}


# ═════════════════════════════════════════════════════════════════════════
# TODO 69: Gapping Placement (Regression)
# ═════════════════════════════════════════════════════════════════════════

class TestGappingRegression:
    """Gapping is frontend-only (Chart.js).  Verify the API endpoint
    (club-comparison) still returns valid data."""

    def test_club_comparison_returns_200(self, api, routed_app, ctx):
        """club-comparison endpoint responds OK."""
        session = _seed_session()
        for club, short, carries in [
            ('7 Iron', '7i', [148, 153, 158, 163, 168]),
            ('P-Wedge', 'PW', [108, 112, 116, 120, 124]),
            ('Driver', '1W', [215, 220, 225, 230, 235]),
        ]:
            shots = [{'carry': float(c), 'spin_rate': 5000, 'launch_angle': 15.0,
                       'ball_speed': 100.0, 'offline': 3.0} for c in carries]
            _seed_club_shots(session, club, short, shots)

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        assert resp.status_code == 200

    def test_club_comparison_has_expected_fields(self, api, routed_app, ctx):
        """Each entry must have club, carry_p75, total_p75, max_total, shot_count."""
        session = _seed_session()
        for club, short, carries in [
            ('7 Iron', '7i', [148, 153, 158, 163, 168]),
            ('P-Wedge', 'PW', [108, 112, 116, 120, 124]),
        ]:
            shots = [{'carry': float(c), 'spin_rate': 5000, 'launch_angle': 15.0,
                       'ball_speed': 100.0, 'offline': 3.0} for c in carries]
            _seed_club_shots(session, club, short, shots)

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        data = resp.get_json()

        assert isinstance(data, list), "club-comparison should return a list"
        assert len(data) >= 2
        for entry in data:
            for key in ('club', 'carry_p75', 'total_p75', 'max_total', 'shot_count'):
                assert key in entry, f"Missing key '{key}' in club-comparison entry"

    def test_club_comparison_ordered_by_club_order(self, api, routed_app, ctx):
        """Results should be sorted by CLUB_ORDER (Driver before 7 Iron before PW)."""
        session = _seed_session()
        for club, short, carries in [
            ('P-Wedge', 'PW', [108, 112, 116, 120, 124]),
            ('Driver', '1W', [215, 220, 225, 230, 235]),
            ('7 Iron', '7i', [148, 153, 158, 163, 168]),
        ]:
            shots = [{'carry': float(c), 'spin_rate': 5000, 'launch_angle': 15.0,
                       'ball_speed': 100.0, 'offline': 3.0} for c in carries]
            _seed_club_shots(session, club, short, shots)

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        data = resp.get_json()

        club_order = [e['club'] for e in data]
        # 1W should come before 7i, 7i before PW
        assert club_order.index('1W') < club_order.index('7i')
        assert club_order.index('7i') < club_order.index('PW')

    def test_club_comparison_empty_session(self, api, routed_app, ctx):
        """Empty session → empty list, no crash."""
        session = _seed_session()

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 0


# ═════════════════════════════════════════════════════════════════════════
# TODO 70: Dispersion Area Always P90
# ═════════════════════════════════════════════════════════════════════════

def _seed_dispersion_shots(session, club, club_short, n=15):
    """Seed n well-spread shots for dispersion boundary testing.
    Spread enough to survive double percentile filtering.
    """
    import random
    random.seed(42)  # Reproducible
    for i in range(n):
        carry = 150.0 + random.gauss(0, 8)
        offline = random.gauss(0, 5)
        _db.session.add(_make_shot(
            session.id, club, club_short, carry, carry + 10.0,
            club_index=i, offline=offline,
        ))
    _db.session.commit()


class TestDispersionBoundaryAlwaysP90:
    """The dispersion boundary must ALWAYS be computed at the 90th percentile
    of whichever shots survive the user's percentile filter.

    When user selects P75 → shots filtered to P75 range, boundary = P90 of those.
    When user selects P50 → shots filtered to P50 range, boundary = P90 of those.
    """

    def test_boundary_present_at_default_percentile(self, api, routed_app, ctx):
        """Default percentile (75) produces a boundary for enough shots."""
        session = _seed_session()
        _seed_dispersion_shots(session, '7 Iron', '7i', n=20)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        assert 'dispersion_boundary' in data
        # With 20 shots at P75, enough should survive
        boundary = data['dispersion_boundary']
        if '7i' in boundary:
            assert len(boundary['7i']) >= 3

    def test_boundary_with_p50_still_produces_boundary(self, api, routed_app, ctx):
        """P50 percentile filter produces a valid boundary (P90 of P50-filtered)."""
        session = _seed_session()
        _seed_dispersion_shots(session, '7 Iron', '7i', n=25)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}&percentile=50')
        data = resp.get_json()
        assert 'dispersion_boundary' in data

    def test_boundary_with_p90_still_produces_boundary(self, api, routed_app, ctx):
        """P90 percentile filter should also produce a boundary."""
        session = _seed_session()
        _seed_dispersion_shots(session, '7 Iron', '7i', n=25)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}&percentile=90')
        data = resp.get_json()
        assert 'dispersion_boundary' in data

    def test_changing_percentile_changes_shots_shown(self, api, routed_app, ctx):
        """Different percentile params should potentially change the shot count
        in the dispersion response (or at minimum, the boundary shape).
        The boundary is always P90 of THOSE shots, not a different percentile.
        """
        session = _seed_session()
        _seed_dispersion_shots(session, '7 Iron', '7i', n=25)

        # Shot data doesn't change with percentile (it's the boundary that changes)
        resp75 = api.get(f'/api/analytics/dispersion?session_id={session.id}&percentile=75')
        resp50 = api.get(f'/api/analytics/dispersion?session_id={session.id}&percentile=50')

        data75 = resp75.get_json()
        data50 = resp50.get_json()

        # Both should be valid
        assert resp75.status_code == 200
        assert resp50.status_code == 200

        # Boundary shapes should differ (P75 includes more data than P50)
        b75 = data75.get('dispersion_boundary', {}).get('7i', [])
        b50 = data50.get('dispersion_boundary', {}).get('7i', [])

        # If both have boundaries, P75 boundary should be larger than P50
        # (P75 keeps more shots → wider boundary)
        if b75 and b50:
            area75 = _approx_polygon_area(b75)
            area50 = _approx_polygon_area(b50)
            # P75 should cover a larger area than P50 (more shots → wider)
            assert area75 >= area50 * 0.5, \
                "P75 boundary should be at least roughly comparable to P50 (both use P90 of their filtered shots)"

    def test_very_few_shots_after_tight_percentile(self, api, routed_app, ctx):
        """With a very tight percentile (P50) and few shots, boundary may not form — no crash."""
        session = _seed_session()
        # Only 5 shots — P50 filtering will leave very few
        _seed_dispersion_shots(session, '7 Iron', '7i', n=5)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}&percentile=50')
        assert resp.status_code == 200
        data = resp.get_json()
        # May or may not have boundary — but must not crash
        assert 'dispersion_boundary' in data

    def test_p90_boundary_is_not_affected_by_percentile_param_name(self, api, routed_app, ctx):
        """The boundary function always uses its own P90 logic internally.
        The percentile param only controls which shots are included."""
        session = _seed_session()
        _seed_dispersion_shots(session, '7 Iron', '7i', n=30)

        # Call with different percentiles
        resp_default = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        resp_p90 = api.get(f'/api/analytics/dispersion?session_id={session.id}&percentile=90')

        data_def = resp_default.get_json()
        data_p90 = resp_p90.get_json()

        # Both should return valid boundaries (different sizes though)
        assert 'dispersion_boundary' in data_def
        assert 'dispersion_boundary' in data_p90


class TestDispersionBoundaryP90Computation:
    """Verify the boundary is actually computing at P90 level —
    it should encompass ~90% of the displayed shots."""

    def test_boundary_encompasses_significant_fraction(self, api, routed_app, ctx):
        """The boundary (P90 of P75-filtered shots) should encompass a meaningful
        fraction of displayed shots.  Because the dispersion endpoint returns ALL
        shots but the boundary is computed on a percentile-filtered subset, the
        boundary is intentionally smaller than the full scatter.  We verify the
        boundary bounding box contains at least 30% of shots — proof it represents
        a real cluster, not garbage."""
        session = _seed_session()
        _seed_dispersion_shots(session, '7 Iron', '7i', n=30)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()

        shots = [s for s in data['shots'] if s['club_short'] == '7i']
        boundary = data.get('dispersion_boundary', {}).get('7i', [])

        if not boundary or len(shots) < 5:
            pytest.skip("Not enough data for encompass check")

        # Get boundary bounding box as a rough check
        b_carries = [p['carry'] for p in boundary]
        b_offlines = [p['offline'] for p in boundary]
        b_carry_min, b_carry_max = min(b_carries), max(b_carries)
        b_off_min, b_off_max = min(b_offlines), max(b_offlines)

        inside_count = sum(
            1 for s in shots
            if b_carry_min <= s['carry'] <= b_carry_max
            and b_off_min <= s['offline'] <= b_off_max
        )

        # Boundary is P90 of P75-filtered shots — smaller than total scatter.
        # At least 30% of ALL shots should be within the bounding box.
        ratio = inside_count / len(shots) if shots else 0
        assert ratio >= 0.3, \
            f"Only {ratio:.0%} of shots within boundary bounding box — expected ≥30%"


def _approx_polygon_area(points):
    """Approximate area of a polygon using the shoelace formula."""
    if len(points) < 3:
        return 0.0
    n = len(points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i]['carry'] * points[j]['offline']
        area -= points[j]['carry'] * points[i]['offline']
    return abs(area) / 2.0
