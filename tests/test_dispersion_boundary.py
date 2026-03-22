"""Tests for TODO 64 (target line) and TODO 65 (P90 dispersion boundary).

Written by Hockney — the tester who asks "what if the data is wrong?"
before anyone else does.

TODO 64 is frontend-only (Chart.js dotted target line at offline=0).
We verify the dispersion endpoint still returns valid data (regression).

TODO 65 adds a `dispersion_boundary` field to the dispersion API response:
  - Dict keyed by club_short
  - Values are arrays of {carry, offline} coordinate objects
  - Forms a closed loop (first point ≈ last point)
  - At least 3 points per club (minimum polygon)
  - Only computed for clubs with >= 3 shots
"""
import math
import pytest
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
        filename='test-dispersion.csv',
        session_date=date(2026, 3, 12),
        location='Driving Ranges',
        data_type=data_type,
    )
    _db.session.add(s)
    _db.session.commit()
    return s


def _seed_club_shots(session, club, club_short, carries_offlines):
    """Seed shots for one club with specific carry/offline pairs.

    carries_offlines: list of (carry, offline) tuples
    """
    for i, (carry, offline) in enumerate(carries_offlines):
        _db.session.add(_make_shot(
            session.id, club, club_short, carry, carry + 10.0,
            club_index=i, offline=offline,
        ))
    _db.session.commit()


def _seed_multi_club_dispersion(session):
    """Seed 7+ shots per club for 7i and PW — enough for meaningful boundary."""
    # 7i: spread around carry=160, offline varies ±10
    _seed_club_shots(session, '7 Iron', '7i', [
        (155.0, -8.0), (158.0, -3.0), (160.0, 1.0),
        (162.0, 5.0), (165.0, 2.0), (157.0, -5.0),
        (163.0, 7.0), (159.0, -1.0), (161.0, 4.0),
        (164.0, 0.0),
    ])
    # PW: spread around carry=115, offline varies ±6
    _seed_club_shots(session, 'P-Wedge', 'PW', [
        (112.0, -4.0), (114.0, -1.0), (116.0, 2.0),
        (118.0, 5.0), (113.0, -3.0), (117.0, 3.0),
        (115.0, 0.0), (119.0, 1.0), (111.0, -6.0),
        (120.0, 4.0),
    ])


# ═════════════════════════════════════════════════════════════════════════
# Regression: Dispersion endpoint still returns valid shot data (TODO 64)
# ═════════════════════════════════════════════════════════════════════════

class TestDispersionRegression:
    """The dispersion endpoint must keep returning valid shot data
    regardless of new boundary features."""

    def test_dispersion_returns_200(self, api, routed_app, ctx):
        """Endpoint responds OK with seeded data."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200

    def test_dispersion_shot_data_present(self, api, routed_app, ctx):
        """Response contains shot-level carry/offline/club data."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()

        # Response may be a list (old) or dict with 'shots' key (new)
        shots = data if isinstance(data, list) else data.get('shots', [])
        assert len(shots) > 0, "Dispersion must return shot data"
        for shot in shots:
            assert 'carry' in shot
            assert 'offline' in shot
            assert 'club_short' in shot

    def test_dispersion_empty_session(self, api, routed_app, ctx):
        """Empty session: 200, no crash, empty or trivial response."""
        session = _seed_session()

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        shots = data if isinstance(data, list) else data.get('shots', [])
        assert len(shots) == 0

    def test_dispersion_club_filter(self, api, routed_app, ctx):
        """Club filter returns only the requested club's shots."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}&club=7i')
        data = resp.get_json()
        shots = data if isinstance(data, list) else data.get('shots', [])
        clubs_in_response = {s['club_short'] for s in shots}
        assert clubs_in_response == {'7i'}, f"Expected only 7i, got {clubs_in_response}"


# ═════════════════════════════════════════════════════════════════════════
# P90 Dispersion Boundary (TODO 65)
# ═════════════════════════════════════════════════════════════════════════

class TestDispersionBoundaryPresence:
    """The dispersion API must return a `dispersion_boundary` field."""

    def test_boundary_field_exists(self, api, routed_app, ctx):
        """Response includes `dispersion_boundary` key."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        assert isinstance(data, dict), "Dispersion response must be a dict (not flat list)"
        assert 'dispersion_boundary' in data, "Response must include 'dispersion_boundary'"

    def test_boundary_is_dict_keyed_by_club(self, api, routed_app, ctx):
        """Boundary data is a dict keyed by club_short strings."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        boundary = data['dispersion_boundary']
        assert isinstance(boundary, dict)
        # With 10 shots each, both clubs should have boundaries
        assert '7i' in boundary
        assert 'PW' in boundary


class TestDispersionBoundaryShape:
    """Each club's boundary must form a valid closed polygon."""

    def test_boundary_minimum_3_points(self, api, routed_app, ctx):
        """Each club boundary has >= 3 points (minimum for a polygon)."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        boundary = resp.get_json()['dispersion_boundary']

        for club, points in boundary.items():
            assert len(points) >= 3, f"{club}: boundary has {len(points)} points, need ≥3"

    def test_boundary_is_closed_loop(self, api, routed_app, ctx):
        """First point ≈ last point (closed polygon)."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        boundary = resp.get_json()['dispersion_boundary']

        for club, points in boundary.items():
            first = points[0]
            last = points[-1]
            assert abs(first['carry'] - last['carry']) < 0.01, \
                f"{club}: boundary not closed (carry: {first['carry']} vs {last['carry']})"
            assert abs(first['offline'] - last['offline']) < 0.01, \
                f"{club}: boundary not closed (offline: {first['offline']} vs {last['offline']})"

    def test_boundary_points_have_carry_and_offline(self, api, routed_app, ctx):
        """Every boundary point has 'carry' and 'offline' keys."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        boundary = resp.get_json()['dispersion_boundary']

        for club, points in boundary.items():
            for i, pt in enumerate(points):
                assert 'carry' in pt, f"{club} point {i}: missing 'carry'"
                assert 'offline' in pt, f"{club} point {i}: missing 'offline'"

    def test_boundary_points_are_valid_numbers(self, api, routed_app, ctx):
        """No NaN, None, or non-numeric values in boundary coordinates."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        boundary = resp.get_json()['dispersion_boundary']

        for club, points in boundary.items():
            for i, pt in enumerate(points):
                assert pt['carry'] is not None, f"{club} point {i}: carry is None"
                assert pt['offline'] is not None, f"{club} point {i}: offline is None"
                assert isinstance(pt['carry'], (int, float)), \
                    f"{club} point {i}: carry not numeric ({type(pt['carry'])})"
                assert isinstance(pt['offline'], (int, float)), \
                    f"{club} point {i}: offline not numeric ({type(pt['offline'])})"
                assert not math.isnan(pt['carry']), f"{club} point {i}: carry is NaN"
                assert not math.isnan(pt['offline']), f"{club} point {i}: offline is NaN"


class TestDispersionBoundaryPerClub:
    """Boundary is computed per club, not across all clubs."""

    def test_boundary_per_club_not_global(self, api, routed_app, ctx):
        """Each club's boundary contains coordinates in that club's range only."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        boundary = resp.get_json()['dispersion_boundary']

        if '7i' in boundary and 'PW' in boundary:
            # 7i carries ~155-165; PW carries ~111-120 — no overlap
            i7_carries = [pt['carry'] for pt in boundary['7i']]
            pw_carries = [pt['carry'] for pt in boundary['PW']]

            assert min(i7_carries) > max(pw_carries), \
                "7i boundary carry range overlaps PW — boundaries may be global, not per-club"

    def test_single_club_filter_single_boundary(self, api, routed_app, ctx):
        """Filtering to one club produces boundary for only that club."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}&club=7i')
        data = resp.get_json()
        boundary = data.get('dispersion_boundary', {})

        # Only 7i should be present
        assert '7i' in boundary
        assert 'PW' not in boundary, "PW boundary should not appear when filtering to 7i only"

    def test_multi_club_selection_multiple_boundaries(self, api, routed_app, ctx):
        """Multi-club selection returns boundaries for each selected club."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}&club=7i,PW')
        data = resp.get_json()
        boundary = data.get('dispersion_boundary', {})

        assert '7i' in boundary
        assert 'PW' in boundary


class TestDispersionBoundaryEdgeCases:
    """Boundary gracefully handles insufficient data."""

    def test_no_shots_no_boundary(self, api, routed_app, ctx):
        """Empty session: no boundary data at all."""
        session = _seed_session()

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()

        # Response may be old list format (no boundary) or new dict format
        if isinstance(data, dict):
            boundary = data.get('dispersion_boundary', {})
            assert boundary == {} or boundary is None or len(boundary) == 0

    def test_fewer_than_3_shots_no_boundary(self, api, routed_app, ctx):
        """Club with only 2 shots should NOT get a boundary (can't form polygon)."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', [
            (160.0, 2.0), (165.0, -3.0),
        ])

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()

        if isinstance(data, dict):
            boundary = data.get('dispersion_boundary', {})
            assert '7i' not in boundary, \
                "7i has only 2 shots — should not produce a boundary"

    def test_3_shots_too_few_after_percentile_filter(self, api, routed_app, ctx):
        """3 shots is the theoretical polygon minimum, but P-percentile
        filtering typically culls them below 3 survivors — no boundary."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', [
            (155.0, -5.0), (160.0, 3.0), (165.0, 0.0),
        ])

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()

        if isinstance(data, dict):
            boundary = data.get('dispersion_boundary', {})
            # With only 3 shots, percentile filtering usually eliminates
            # too many to form a polygon — boundary absent is acceptable
            assert '7i' not in boundary or len(boundary.get('7i', [])) >= 3

    def test_enough_shots_produces_boundary(self, api, routed_app, ctx):
        """8+ well-spread shots should survive percentile filtering."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', [
            (155.0, -6.0), (157.0, -3.0), (159.0, 0.0),
            (161.0, 3.0), (163.0, 6.0), (158.0, -1.0),
            (160.0, 2.0), (162.0, -4.0),
        ])

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()

        if isinstance(data, dict):
            boundary = data.get('dispersion_boundary', {})
            assert '7i' in boundary, "8 well-spread shots should produce a boundary"
            assert len(boundary['7i']) >= 3

    def test_mixed_club_counts_partial_boundary(self, api, routed_app, ctx):
        """Club with enough shots gets boundary; club with too few doesn't."""
        session = _seed_session()
        # 7i: 10 shots — enough to survive percentile filtering
        _seed_club_shots(session, '7 Iron', '7i', [
            (155.0, -6.0), (157.0, -3.0), (159.0, 0.0),
            (161.0, 3.0), (163.0, 6.0), (158.0, -1.0),
            (160.0, 2.0), (162.0, -4.0), (156.0, 1.0),
            (164.0, -2.0),
        ])
        # PW: only 2 shots — not enough
        _seed_club_shots(session, 'P-Wedge', 'PW', [
            (115.0, 2.0), (118.0, -1.0),
        ])

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()

        if isinstance(data, dict):
            boundary = data.get('dispersion_boundary', {})
            assert '7i' in boundary, "7i (5 shots) should have boundary"
            assert 'PW' not in boundary, "PW (2 shots) should NOT have boundary"

    def test_single_club_selected_still_works(self, api, routed_app, ctx):
        """Single club selection produces valid boundary for that club."""
        session = _seed_session()
        _seed_multi_club_dispersion(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}&club=PW')
        data = resp.get_json()

        if isinstance(data, dict):
            boundary = data.get('dispersion_boundary', {})
            assert 'PW' in boundary
            points = boundary['PW']
            assert len(points) >= 3
            # Verify it's closed
            assert abs(points[0]['carry'] - points[-1]['carry']) < 0.01
            assert abs(points[0]['offline'] - points[-1]['offline']) < 0.01

    def test_excluded_shots_not_in_boundary(self, api, routed_app, ctx):
        """Excluded shots should not influence the boundary computation."""
        session = _seed_session()
        # 3 normal shots
        for i, (carry, offline) in enumerate([(155.0, -5.0), (160.0, 3.0), (165.0, 0.0)]):
            _db.session.add(_make_shot(
                session.id, '7 Iron', '7i', carry, carry + 10.0,
                club_index=i, offline=offline, excluded=False,
            ))
        # 1 excluded shot with wild values — should not warp boundary
        _db.session.add(_make_shot(
            session.id, '7 Iron', '7i', 300.0, 310.0,
            club_index=3, offline=50.0, excluded=True,
        ))
        _db.session.commit()

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()

        if isinstance(data, dict):
            boundary = data.get('dispersion_boundary', {})
            if '7i' in boundary:
                for pt in boundary['7i']:
                    assert pt['carry'] < 200.0, \
                        "Excluded shot (carry=300) leaked into boundary"
                    assert pt['offline'] < 30.0, \
                        "Excluded shot (offline=50) leaked into boundary"
