"""Tests for chart data API endpoints and percentile parameter flow.

Written by Hockney — the skeptic who makes sure the numbers don't lie.

Covers:
  - /api/analytics/<chart_type> endpoints return valid JSON with data
  - /api/club-matrix and /api/wedge-matrix accept percentile
  - Percentile parameter flows through and changes output
  - Edge cases: no shots, single shot, percentile=0, percentile=100
"""
import pytest
import numpy as np
from datetime import date
from flask import Flask

from models.database import db as _db, Session, Shot, ClubLoft, init_db
from models.seed import seed_club_lofts
from app import register_routes
from config import Config


# ── Fixtures: Flask app WITH routes registered ──────────────────────────

@pytest.fixture(scope='function')
def routed_app():
    """Flask app with all routes registered (needed for endpoint testing)."""
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
    """App context for DB operations."""
    with routed_app.app_context():
        yield


def _make_shot(session_id, club, club_short, carry, total, **kwargs):
    """Helper: create a Shot with sensible defaults."""
    return Shot(
        session_id=session_id,
        club=club,
        club_short=club_short,
        club_index=kwargs.get('club_index', 0),
        swing_size=kwargs.get('swing_size', 'full'),
        ball_speed=kwargs.get('ball_speed', 100.0),
        launch_direction=kwargs.get('launch_direction', 'R5.0'),
        launch_direction_deg=kwargs.get('launch_direction_deg', 5.0),
        launch_angle=kwargs.get('launch_angle', 15.0),
        spin_rate=kwargs.get('spin_rate', 5000),
        spin_axis=kwargs.get('spin_axis', 'L10.0'),
        spin_axis_deg=kwargs.get('spin_axis_deg', -10.0),
        back_spin=kwargs.get('back_spin', 4800),
        side_spin=kwargs.get('side_spin', -870),
        apex=kwargs.get('apex', 25.0),
        carry=carry,
        total=total,
        offline=kwargs.get('offline', 5.0),
        landing_angle=kwargs.get('landing_angle', 45.0),
        club_path=kwargs.get('club_path', 5.0),
        face_angle=kwargs.get('face_angle', 3.0),
        attack_angle=kwargs.get('attack_angle', 1.0),
        dynamic_loft=kwargs.get('dynamic_loft', 28.0),
        excluded=kwargs.get('excluded', False),
    )


def _seed_session(data_type='club'):
    """Create and return a Session row."""
    s = Session(
        filename='test-session.csv',
        session_date=date(2026, 3, 12),
        location='Driving Ranges',
        data_type=data_type,
    )
    _db.session.add(s)
    _db.session.commit()
    return s


def _seed_multi_club_shots(session):
    """Seed 5 shots per club for 7i, PW, and Driver — enough for box plots."""
    clubs = {
        '7 Iron': ('7i', [148, 153, 158, 163, 168]),
        'P-Wedge': ('PW', [108, 112, 116, 120, 124]),
        'Driver':  ('1W', [215, 220, 225, 230, 235]),
    }
    for club, (short, carries) in clubs.items():
        for i, c in enumerate(carries):
            _db.session.add(_make_shot(
                session.id, club, short, float(c), float(c + 10),
                club_index=i,
                spin_rate=5000 + i * 200,
                launch_angle=12.0 + i * 0.5,
                ball_speed=100.0 + i * 3.0,
                offline=float((-1) ** i * (2 + i)),
            ))
    _db.session.commit()


def _seed_wedge_shots(session):
    """Seed wedge shots across AW/SW/LW with varying swing sizes."""
    entries = [
        ('G-Wedge', 'AW', '3/3', 90.0),
        ('G-Wedge', 'AW', '3/3', 88.0),
        ('G-Wedge', 'AW', '2/3', 72.0),
        ('G-Wedge', 'AW', '2/3', 70.0),
        ('S-Wedge', 'SW', '3/3', 80.0),
        ('S-Wedge', 'SW', '3/3', 78.0),
        ('S-Wedge', 'SW', '2/3', 62.0),
        ('L-Wedge', 'LW', '3/3', 70.0),
        ('L-Wedge', 'LW', '3/3', 68.0),
    ]
    for i, (club, short, swing, carry) in enumerate(entries):
        _db.session.add(_make_shot(
            session.id, club, short, carry, carry + 2.0,
            swing_size=swing, club_index=i,
        ))
    _db.session.commit()


# ═════════════════════════════════════════════════════════════════════════
# 1. Chart API endpoints return valid JSON with data
# ═════════════════════════════════════════════════════════════════════════

class TestChartEndpointsReturnData:
    """Each analytics endpoint must return 200 with non-empty JSON."""

    def test_launch_spin_stability_returns_data(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        # Response wraps clubs in a 'clubs' key
        clubs = data.get('clubs', data)
        assert len(clubs) > 0
        for club, entry in clubs.items():
            assert 'spin' in entry
            assert 'launch' in entry
            assert 'shot_count' in entry
            assert entry['spin']['count'] >= 3

    def test_radar_comparison_returns_data(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        # Radar response: {axes: [...], user: {values, raw}, pga: {values, raw}}
        assert 'axes' in data
        assert 'user' in data
        assert 'pga' in data
        assert len(data['axes']) >= 3
        # PGA baseline should always be present
        assert 'values' in data['pga']
        # User data should have values matching axes count
        assert len(data['user']['values']) == len(data['axes'])

    def test_carry_distribution_returns_data(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert len(data) > 0
        for club, entry in data.items():
            assert 'min' in entry
            assert 'median' in entry
            assert 'max' in entry
            assert 'count' in entry
            assert entry['count'] >= 1

    def test_dispersion_returns_data(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert 'shots' in data
        assert 'dispersion_boundary' in data
        shots = data['shots']
        assert isinstance(shots, list)
        assert len(shots) > 0
        assert 'carry' in shots[0]
        assert 'offline' in shots[0]

    def test_spin_carry_returns_data(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/spin-carry?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert 'roll' in data[0]
        assert 'spin_rate' in data[0]

    def test_shot_shape_returns_data(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/shot-shape?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert 'face_angle' in data[0]
        assert 'club_path' in data[0]

    def test_club_comparison_returns_data(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert 'club' in data[0]
        assert 'carry_p75' in data[0]

    def test_unknown_chart_type_returns_404(self, api, routed_app, ctx):
        resp = api.get('/api/analytics/nonexistent-chart')
        assert resp.status_code == 404
        data = resp.get_json()
        assert 'error' in data


# ═════════════════════════════════════════════════════════════════════════
# 2. Percentile parameter flows through and changes output
# ═════════════════════════════════════════════════════════════════════════

class TestPercentileParameterFlow:
    """Percentile param must be accepted and must change results."""

    def test_carry_distribution_different_at_p50_vs_p90(self, api, routed_app, ctx):
        """P50 and P90 must produce different q3 values (the upper box boundary)."""
        session = _seed_session()
        _seed_multi_club_shots(session)

        r50 = api.get(f'/api/analytics/carry-distribution?session_id={session.id}&percentile=50')
        r90 = api.get(f'/api/analytics/carry-distribution?session_id={session.id}&percentile=90')
        d50 = r50.get_json()
        d90 = r90.get_json()

        # The q3 field uses the percentile param — P50 and P90 should differ
        for club in d50:
            if club in d90:
                assert d50[club]['q3'] != d90[club]['q3'], \
                    f"P50 and P90 should produce different q3 for {club}"

    def test_club_matrix_accepts_percentile(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/club-matrix?session_id={session.id}&percentile=50')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['percentile'] == 50

    def test_club_matrix_percentile_changes_output(self, api, routed_app, ctx):
        """P50 and P90 club matrices should have different carry values."""
        session = _seed_session()
        _seed_multi_club_shots(session)

        r50 = api.get(f'/api/club-matrix?session_id={session.id}&percentile=50')
        r90 = api.get(f'/api/club-matrix?session_id={session.id}&percentile=90')
        m50 = r50.get_json()['matrix']
        m90 = r90.get_json()['matrix']

        # Matrix is a list of dicts: [{club, carry, total, ...}, ...]
        carries_50 = {row['club_short']: row['carry'] for row in m50}
        carries_90 = {row['club_short']: row['carry'] for row in m90}

        any_different = False
        for club in carries_50:
            if club in carries_90 and carries_50[club] != carries_90[club]:
                any_different = True
                break
        assert any_different, "P50 and P90 should produce different matrix values"

    def test_wedge_matrix_accepts_percentile(self, api, routed_app, ctx):
        session = _seed_session(data_type='wedge')
        _seed_wedge_shots(session)

        resp = api.get(f'/api/wedge-matrix?session_id={session.id}&percentile=50')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['percentile'] == 50

    def test_default_percentile_is_p75(self, api, routed_app, ctx):
        """When no percentile param is given, default should be 75."""
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/club-matrix?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['percentile'] == 75

    def test_launch_spin_accepts_percentile(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}&percentile=90')
        assert resp.status_code == 200
        # Should not crash — percentile is accepted
        data = resp.get_json()
        assert isinstance(data, dict)

    def test_radar_accepts_percentile(self, api, routed_app, ctx):
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}&percentile=25')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)


# ═════════════════════════════════════════════════════════════════════════
# 3. Edge cases — the part I live for
# ═════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """What breaks when the data is wrong, missing, or lonely?"""

    def test_no_shots_for_club_returns_empty(self, api, routed_app, ctx):
        """Endpoints shouldn't crash when a club has zero shots."""
        session = _seed_session()
        # No shots seeded — every endpoint should return empty, not 500

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {} or data == []

    def test_dispersion_no_shots_returns_empty(self, api, routed_app, ctx):
        session = _seed_session()

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['shots'] == []
        assert data['dispersion_boundary'] == {}

    def test_radar_no_shots_returns_empty(self, api, routed_app, ctx):
        session = _seed_session()

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # Radar may return structure with empty user data or empty dict
        if 'user' in data:
            # User values should be empty or all None
            assert data['user'].get('values', []) == [] or all(v is None for v in data['user'].get('values', []))
        else:
            assert data == {} or data == []

    def test_launch_spin_no_shots_returns_empty(self, api, routed_app, ctx):
        session = _seed_session()

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # Response may be wrapped: {'clubs': {}, 'correlation': ''}
        clubs = data.get('clubs', data) if isinstance(data, dict) else data
        assert clubs == {} or clubs == []

    def test_single_shot_carry_distribution(self, api, routed_app, ctx):
        """One shot shouldn't crash box-plot stats."""
        session = _seed_session()
        _db.session.add(_make_shot(session.id, '7 Iron', '7i', 160.0, 170.0))
        _db.session.commit()

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert '7i' in data
        assert data['7i']['count'] == 1
        assert data['7i']['min'] == pytest.approx(160.0)
        assert data['7i']['max'] == pytest.approx(160.0)

    def test_single_shot_dispersion(self, api, routed_app, ctx):
        """One shot should still return a dispersion point."""
        session = _seed_session()
        _db.session.add(_make_shot(session.id, '7 Iron', '7i', 160.0, 170.0, offline=3.5))
        _db.session.commit()

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        shots = data['shots']
        assert len(shots) == 1
        assert shots[0]['carry'] == pytest.approx(160.0)
        assert shots[0]['offline'] == pytest.approx(3.5)
        # Single shot = no boundary (need >= 3)
        assert data['dispersion_boundary'] == {}

    def test_launch_spin_needs_3_shots_minimum(self, api, routed_app, ctx):
        """Launch-spin stability requires >= 3 shots per club to render."""
        session = _seed_session()
        # Only 2 shots — below the 3-shot threshold
        _db.session.add(_make_shot(session.id, '7 Iron', '7i', 160.0, 170.0, club_index=0))
        _db.session.add(_make_shot(session.id, '7 Iron', '7i', 165.0, 175.0, club_index=1))
        _db.session.commit()

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # 7i should NOT appear because only 2 shots
        assert '7i' not in data

    def test_percentile_zero(self, api, routed_app, ctx):
        """Percentile=0 should return the minimum carry, not crash."""
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}&percentile=0')
        assert resp.status_code == 200
        data = resp.get_json()
        # q3 at P0 should be the minimum value
        for club, entry in data.items():
            assert entry['q3'] == pytest.approx(entry['min'], abs=0.5)

    def test_percentile_100(self, api, routed_app, ctx):
        """Percentile=100 should return the maximum carry, not crash."""
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}&percentile=100')
        assert resp.status_code == 200
        data = resp.get_json()
        for club, entry in data.items():
            assert entry['q3'] == pytest.approx(entry['max'], abs=0.5)

    def test_multi_club_selection_returns_all_selected(self, api, routed_app, ctx):
        """Comma-separated club param should return data for each selected club."""
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}&club=7i,PW')
        assert resp.status_code == 200
        data = resp.get_json()
        assert '7i' in data
        assert 'PW' in data
        # Driver should NOT be present
        assert '1W' not in data

    def test_multi_club_dispersion(self, api, routed_app, ctx):
        """Multi-club dispersion should include shots from all selected clubs."""
        session = _seed_session()
        _seed_multi_club_shots(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}&club=7i,1W')
        assert resp.status_code == 200
        data = resp.get_json()
        shots = data['shots']
        clubs_in_response = {d['club_short'] for d in shots}
        assert '7i' in clubs_in_response
        assert '1W' in clubs_in_response

    def test_club_matrix_empty_session(self, api, routed_app, ctx):
        """Club matrix with no shots should return empty matrix, not crash."""
        session = _seed_session()

        resp = api.get(f'/api/club-matrix?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        matrix = data['matrix']
        assert matrix == {} or matrix == [] or len(matrix) == 0

    def test_wedge_matrix_empty_session(self, api, routed_app, ctx):
        """Wedge matrix with no shots should return without crashing."""
        session = _seed_session(data_type='wedge')

        resp = api.get(f'/api/wedge-matrix?session_id={session.id}')
        assert resp.status_code == 200

    def test_all_excluded_shots_returns_empty(self, api, routed_app, ctx):
        """If every shot is excluded, endpoints should return empty data."""
        session = _seed_session()
        for i in range(5):
            _db.session.add(_make_shot(
                session.id, '7 Iron', '7i', 160.0 + i, 170.0 + i,
                excluded=True, club_index=i,
            ))
        _db.session.commit()

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {} or len(data) == 0
