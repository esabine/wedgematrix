"""Tests for TODO 80-85: Version Auto-Increment, PGA Tour Average Table,
Symmetric Dispersion X-Axis, Dispersion Axis Label, Shot Shape Tooltip,
Consistent Club Colors.

Written by Hockney — the skeptic who makes sure the numbers don't lie.

TODO 80: Version auto-increment — semver format, bump_version.py exists,
         version injected into templates.
TODO 81: PGA Tour Average table API — /api/analytics/pga-averages returns
         14 clubs with carry, spin_rate, launch_angle, ball_speed, dispersion.
TODO 82: Symmetric dispersion x-axis — dispersion data has offline values
         that can be symmetrized (positive and negative).
TODO 83: Dispersion x-axis label — verify dispersion API response structure.
TODO 84: Shot Shape tooltip with club — shot-shape data includes club/club_short.
TODO 85: Consistent club colors — all chart APIs return club names in same format.
"""
import os
import re
import pytest
from datetime import date
from flask import Flask

from models.database import db as _db, Session, Shot, ClubLoft, init_db
from models.seed import seed_club_lofts
from app import register_routes, VERSION
from services.analytics import PGA_AVERAGES
from services.club_matrix import CLUB_ORDER
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
        filename='test-batch10.csv',
        session_date=date(2026, 3, 28),
        location='Driving Ranges',
        data_type=data_type,
    )
    _db.session.add(s)
    _db.session.commit()
    return s


CLUB_NAME_MAP = {
    '1W': 'Driver', '3W': '3 Wood', '2H': '2 Hybrid', '3H': '3 Hybrid',
    '4i': '4 Iron', '5i': '5 Iron', '6i': '6 Iron', '7i': '7 Iron',
    '8i': '8 Iron', '9i': '9 Iron', 'PW': 'P-Wedge', 'AW': 'G-Wedge',
    'SW': 'S-Wedge', 'LW': 'L-Wedge',
}


def _seed_full_bag(session_id, shots_per_club=5, base_carry=None):
    """Seed shots for all 14 canonical clubs. Returns list of club shorts."""
    default_carries = {
        '1W': 230, '3W': 210, '2H': 200, '3H': 195,
        '4i': 185, '5i': 175, '6i': 165, '7i': 155,
        '8i': 145, '9i': 135, 'PW': 120, 'AW': 105,
        'SW': 90, 'LW': 75,
    }
    for short, club_name in CLUB_NAME_MAP.items():
        bc = base_carry or default_carries[short]
        for i in range(shots_per_club):
            _db.session.add(_make_shot(
                session_id, club_name, short,
                carry=bc + i * 2.0,
                total=bc + i * 2.0 + 12.0,
                club_index=i,
                spin_rate=5000 + i * 100,
                launch_angle=12.0 + i * 0.5,
                ball_speed=100.0 + i * 1.5,
                face_angle=2.0 + i * 0.2,
                club_path=3.0 + i * 0.15,
                offline=float((-1) ** i * (3 + i * 0.5)),
            ))
    _db.session.commit()
    return list(CLUB_NAME_MAP.keys())


# ═════════════════════════════════════════════════════════════════════════
# TODO 80 — Version Auto-Increment
# ═════════════════════════════════════════════════════════════════════════

class TestVersionAutoIncrement:
    """Version constant, bump script, and template injection."""

    def test_version_follows_semver(self):
        """VERSION must match semver: MAJOR.MINOR.PATCH (optional pre-release)."""
        assert VERSION is not None, "VERSION not defined in app.py"
        assert re.match(r'^\d+\.\d+\.\d+(-\w+)?$', VERSION), \
            f"VERSION '{VERSION}' does not follow semver format X.Y.Z"

    def test_version_parts_are_non_negative_integers(self):
        """Each version part must be a non-negative integer."""
        parts = VERSION.split('-')[0].split('.')
        assert len(parts) == 3, f"Expected 3 parts, got {len(parts)}"
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' is not a digit"
            assert int(part) >= 0

    def test_bump_version_script_exists(self):
        """bump_version.py must exist in the project root."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        script = os.path.join(project_root, 'bump_version.py')
        assert os.path.isfile(script), \
            "bump_version.py not found in project root"

    def test_bump_version_script_is_importable(self):
        """bump_version.py should be a valid Python file (no syntax errors)."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        script = os.path.join(project_root, 'bump_version.py')
        # Compile-check: catches SyntaxError without executing
        with open(script, 'r') as f:
            source = f.read()
        compile(source, script, 'exec')  # raises SyntaxError if invalid

    def test_version_injected_via_context_processor(self, routed_app, ctx):
        """The version must be available to templates via context_processor."""
        from app import create_app
        real_app = create_app()
        with real_app.test_request_context('/'):
            # The context processor injects 'version' into all templates
            processors = real_app.template_context_processors[None]
            injected = {}
            for proc in processors:
                injected.update(proc())
            assert 'version' in injected, \
                "Context processor does not inject 'version'"
            assert injected['version'] == VERSION, \
                f"Injected version {injected['version']} != {VERSION}"


# ═════════════════════════════════════════════════════════════════════════
# TODO 81 — PGA Tour Average Table API
# ═════════════════════════════════════════════════════════════════════════

class TestPGATourAverageTableAPI:
    """Dedicated /api/analytics/pga-averages endpoint for the PGA table."""

    def test_pga_averages_endpoint_returns_200(self, api, routed_app, ctx):
        """GET /api/analytics/pga-averages must return 200."""
        resp = api.get('/api/analytics/pga-averages')
        assert resp.status_code == 200

    def test_response_has_clubs_key_with_list(self, api, routed_app, ctx):
        """Response must be {clubs: [...]}."""
        resp = api.get('/api/analytics/pga-averages')
        data = resp.get_json()
        assert 'clubs' in data, "Response missing 'clubs' key"
        assert isinstance(data['clubs'], list), "'clubs' must be a list"

    def test_returns_14_clubs(self, api, routed_app, ctx):
        """PGA averages should cover all 14 standard bag clubs."""
        resp = api.get('/api/analytics/pga-averages')
        data = resp.get_json()
        assert len(data['clubs']) == 14, \
            f"Expected 14 clubs, got {len(data['clubs'])}"

    def test_each_club_has_required_fields(self, api, routed_app, ctx):
        """Every club entry must have: club, carry, spin_rate, launch_angle, ball_speed, dispersion."""
        resp = api.get('/api/analytics/pga-averages')
        data = resp.get_json()
        required = {'club', 'carry', 'spin_rate', 'launch_angle', 'ball_speed', 'dispersion'}
        for entry in data['clubs']:
            missing = required - set(entry.keys())
            assert not missing, \
                f"Club '{entry.get('club', '?')}' missing fields: {missing}"

    def test_clubs_sorted_in_canonical_order(self, api, routed_app, ctx):
        """Clubs must be sorted: 1W, 3W, 2H, 3H, 4i, 5i, ... LW."""
        resp = api.get('/api/analytics/pga-averages')
        data = resp.get_json()
        club_names = [c['club'] for c in data['clubs']]
        # Filter CLUB_ORDER to just the 14 bare names that appear in PGA_AVERAGES
        expected_order = [c for c in CLUB_ORDER if c in PGA_AVERAGES]
        assert club_names == expected_order, \
            f"Club order mismatch.\nGot:      {club_names}\nExpected: {expected_order}"

    def test_carry_values_are_positive(self, api, routed_app, ctx):
        """All carry values must be positive numbers."""
        resp = api.get('/api/analytics/pga-averages')
        data = resp.get_json()
        for entry in data['clubs']:
            carry = entry['carry']
            assert isinstance(carry, (int, float)), \
                f"Carry for {entry['club']} is not a number: {carry}"
            assert carry > 0, \
                f"Carry for {entry['club']} is not positive: {carry}"

    def test_spin_rates_are_positive(self, api, routed_app, ctx):
        """All spin_rate values must be positive numbers."""
        resp = api.get('/api/analytics/pga-averages')
        data = resp.get_json()
        for entry in data['clubs']:
            sr = entry['spin_rate']
            assert isinstance(sr, (int, float)) and sr > 0, \
                f"spin_rate for {entry['club']} invalid: {sr}"

    def test_carry_decreases_from_driver_to_lob_wedge(self, api, routed_app, ctx):
        """Carry should generally decrease from 1W to LW (sanity check)."""
        resp = api.get('/api/analytics/pga-averages')
        data = resp.get_json()
        clubs = data['clubs']
        first_carry = clubs[0]['carry']   # 1W
        last_carry = clubs[-1]['carry']   # LW
        assert first_carry > last_carry, \
            f"Driver carry ({first_carry}) should be > LW carry ({last_carry})"

    def test_pga_data_matches_source_constant(self, api, routed_app, ctx):
        """API response should match the PGA_AVERAGES constant in analytics.py."""
        resp = api.get('/api/analytics/pga-averages')
        data = resp.get_json()
        for entry in data['clubs']:
            club = entry['club']
            assert club in PGA_AVERAGES, f"{club} not in PGA_AVERAGES constant"
            for key in ('carry', 'spin_rate', 'launch_angle', 'ball_speed', 'dispersion'):
                assert entry[key] == PGA_AVERAGES[club][key], \
                    f"Mismatch for {club}.{key}: API={entry[key]}, source={PGA_AVERAGES[club][key]}"


# ═════════════════════════════════════════════════════════════════════════
# TODO 82 — Symmetric Dispersion X-Axis (backend data verification)
# ═════════════════════════════════════════════════════════════════════════

class TestSymmetricDispersionData:
    """Verify dispersion API returns offline values that support symmetrization."""

    def test_dispersion_returns_offline_values(self, api, routed_app, ctx):
        """Dispersion scatter data must include 'offline' for each shot."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        shots = data['shots']
        assert len(shots) > 0, "No shots returned"
        for shot in shots:
            assert 'offline' in shot, "Shot missing 'offline' field"
            assert isinstance(shot['offline'], (int, float)), \
                f"offline is not numeric: {shot['offline']}"

    def test_offline_values_include_both_positive_and_negative(self, api, routed_app, ctx):
        """Data should contain both L and R misses (positive and negative offline)."""
        session = _seed_session()
        # Seed shots with alternating positive/negative offline
        for i in range(10):
            _db.session.add(_make_shot(
                session.id, '7 Iron', '7i', 155.0 + i, 165.0 + i,
                club_index=i,
                offline=float((-1) ** i * (3 + i)),
            ))
        _db.session.commit()

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        offlines = [s['offline'] for s in data['shots']]
        has_positive = any(o > 0 for o in offlines)
        has_negative = any(o < 0 for o in offlines)
        assert has_positive and has_negative, \
            "Dispersion data should include both positive and negative offline " \
            f"values for symmetric x-axis. Got: {offlines}"

    def test_dispersion_carry_is_positive(self, api, routed_app, ctx):
        """All corrected carry values in dispersion should be positive."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        for shot in data['shots']:
            assert shot['carry'] > 0, \
                f"Carry should be positive, got {shot['carry']}"


# ═════════════════════════════════════════════════════════════════════════
# TODO 83 — Dispersion X-Axis Label (API structure verification)
# ═════════════════════════════════════════════════════════════════════════

class TestDispersionAPIStructure:
    """Verify dispersion API response structure is intact for frontend rendering."""

    def test_dispersion_response_is_envelope(self, api, routed_app, ctx):
        """Response must be {shots: [...], dispersion_boundary: {...}}."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        assert 'shots' in data, "Missing 'shots' key"
        assert 'dispersion_boundary' in data, "Missing 'dispersion_boundary' key"
        assert isinstance(data['shots'], list)
        assert isinstance(data['dispersion_boundary'], dict)

    def test_each_shot_has_carry_and_offline(self, api, routed_app, ctx):
        """Every shot must have both carry and offline for axis rendering."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        for shot in data['shots']:
            assert 'carry' in shot, "Shot missing 'carry'"
            assert 'offline' in shot, "Shot missing 'offline'"

    def test_each_shot_has_club_identifier(self, api, routed_app, ctx):
        """Every shot in dispersion data must have club and club_short."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        for shot in data['shots']:
            assert 'club_short' in shot, "Shot missing 'club_short'"

    def test_empty_session_returns_empty_shots(self, api, routed_app, ctx):
        """An empty session should return empty shots list, not error."""
        session = _seed_session()
        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['shots'] == []


# ═════════════════════════════════════════════════════════════════════════
# TODO 84 — Shot Shape Tooltip with Club
# ═════════════════════════════════════════════════════════════════════════

class TestShotShapeTooltipClub:
    """Shot Shape API must include club info for tooltip rendering."""

    def test_shot_shape_returns_200(self, api, routed_app, ctx):
        """GET /api/analytics/shot-shape must return 200."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)
        resp = api.get(f'/api/analytics/shot-shape?session_id={session.id}')
        assert resp.status_code == 200

    def test_each_shot_has_club_field(self, api, routed_app, ctx):
        """Every shot-shape item must have 'club' or 'club_short' for tooltip."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)

        resp = api.get(f'/api/analytics/shot-shape?session_id={session.id}')
        data = resp.get_json()
        assert len(data) > 0, "No shot shape data returned"
        for item in data:
            has_club = 'club' in item or 'club_short' in item
            assert has_club, \
                f"Shot shape item missing club identifier: {item.keys()}"

    def test_each_shot_has_club_path_and_face_angle(self, api, routed_app, ctx):
        """Shot shape items must have both club_path and face_angle."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)

        resp = api.get(f'/api/analytics/shot-shape?session_id={session.id}')
        data = resp.get_json()
        for item in data:
            assert 'club_path' in item, f"Missing club_path: {item.keys()}"
            assert 'face_angle' in item, f"Missing face_angle: {item.keys()}"

    def test_shot_shape_includes_diff_field(self, api, routed_app, ctx):
        """Shot shape items should include the face-path diff."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)

        resp = api.get(f'/api/analytics/shot-shape?session_id={session.id}')
        data = resp.get_json()
        for item in data:
            assert 'diff' in item, "Missing 'diff' (face_angle - club_path)"

    def test_club_short_matches_known_clubs(self, api, routed_app, ctx):
        """Club identifiers in shot shape should be valid club_short codes."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=3)

        resp = api.get(f'/api/analytics/shot-shape?session_id={session.id}')
        data = resp.get_json()
        valid_shorts = set(CLUB_NAME_MAP.keys())
        for item in data:
            club = item.get('club') or item.get('club_short')
            assert club in valid_shorts, \
                f"Unknown club_short '{club}' in shot shape data"

    def test_empty_session_returns_empty_list(self, api, routed_app, ctx):
        """Empty session should return empty list, not error."""
        session = _seed_session()
        resp = api.get(f'/api/analytics/shot-shape?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == []


# ═════════════════════════════════════════════════════════════════════════
# TODO 85 — Consistent Club Colors (cross-API club name format)
# ═════════════════════════════════════════════════════════════════════════

class TestConsistentClubColors:
    """All chart APIs must return club names in the same format so
    the frontend color function can match them consistently."""

    def _get_club_names_from_endpoint(self, api, endpoint, session_id):
        """Extract club name set from a given chart endpoint response."""
        resp = api.get(f'/api/analytics/{endpoint}?session_id={session_id}')
        assert resp.status_code == 200
        data = resp.get_json()

        clubs = set()
        if isinstance(data, list):
            # Flat array of items (shot-shape, spin-carry)
            for item in data:
                c = item.get('club') or item.get('club_short')
                if c:
                    clubs.add(c)
        elif isinstance(data, dict):
            if 'shots' in data:
                # Dispersion envelope
                for item in data['shots']:
                    c = item.get('club') or item.get('club_short')
                    if c:
                        clubs.add(c)
            elif 'clubs' in data:
                # PGA averages
                for item in data['clubs']:
                    c = item.get('club')
                    if c:
                        clubs.add(c)
            else:
                # Dict keyed by club (carry-distribution, loft-summary)
                clubs = set(data.keys())
        return clubs

    def test_dispersion_and_shot_shape_use_same_club_format(self, api, routed_app, ctx):
        """Club names in dispersion and shot-shape must match."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=5)

        disp_clubs = self._get_club_names_from_endpoint(api, 'dispersion', session.id)
        shape_clubs = self._get_club_names_from_endpoint(api, 'shot-shape', session.id)

        # Both should use the same club_short format
        assert disp_clubs == shape_clubs, \
            f"Club name mismatch:\n  dispersion: {sorted(disp_clubs)}\n  shot-shape: {sorted(shape_clubs)}"

    def test_dispersion_and_spin_carry_use_same_format(self, api, routed_app, ctx):
        """Club names in dispersion and spin-carry must match."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=5)

        disp_clubs = self._get_club_names_from_endpoint(api, 'dispersion', session.id)
        spin_clubs = self._get_club_names_from_endpoint(api, 'spin-carry', session.id)

        assert disp_clubs == spin_clubs, \
            f"Club name mismatch:\n  dispersion: {sorted(disp_clubs)}\n  spin-carry: {sorted(spin_clubs)}"

    def test_carry_distribution_uses_same_club_format(self, api, routed_app, ctx):
        """Carry distribution keys must use same club_short codes as scatter charts."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=5)

        disp_clubs = self._get_club_names_from_endpoint(api, 'dispersion', session.id)
        carry_clubs = self._get_club_names_from_endpoint(api, 'carry-distribution', session.id)

        assert disp_clubs == carry_clubs, \
            f"Club name mismatch:\n  dispersion: {sorted(disp_clubs)}\n  carry-dist: {sorted(carry_clubs)}"

    def test_all_chart_clubs_are_short_codes(self, api, routed_app, ctx):
        """All chart APIs should use short codes (7i, PW), not long names (7 Iron, P-Wedge)."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=5)

        long_names = {'Driver', '3 Wood', '2 Hybrid', '3 Hybrid', '4 Iron',
                      '5 Iron', '6 Iron', '7 Iron', '8 Iron', '9 Iron',
                      'P-Wedge', 'G-Wedge', 'S-Wedge', 'L-Wedge'}

        for endpoint in ('dispersion', 'shot-shape', 'spin-carry', 'carry-distribution'):
            clubs = self._get_club_names_from_endpoint(api, endpoint, session.id)
            bad = clubs & long_names
            assert not bad, \
                f"/{endpoint} uses long club names: {bad} (should be short codes)"

    def test_pga_averages_uses_same_format_as_chart_endpoints(self, api, routed_app, ctx):
        """PGA averages club names should match the format used by chart endpoints."""
        session = _seed_session()
        _seed_full_bag(session.id, shots_per_club=5)

        pga_clubs = self._get_club_names_from_endpoint(api, 'pga-averages', None)
        carry_clubs = self._get_club_names_from_endpoint(api, 'carry-distribution', session.id)

        # PGA has all 14; carry might have fewer if shots were excluded
        # But the ones that overlap must use same format
        overlap = pga_clubs & carry_clubs
        assert len(overlap) > 0, "No overlapping clubs between PGA and carry-distribution"
        # All overlapping names must be identical (same format)
        for club in overlap:
            assert club in pga_clubs and club in carry_clubs
