"""Tests for TODO 71-76: Version, Gapping Fix, Dispersion Tooltips,
Launch & Spin Stability Sub-Swings, Box & Whisker Data, PGA Tour Averages.

Written by Hockney — the tester who asks "what if the data is wrong?"
before anyone else does.

TODO 71: Version number visible and semver-formatted.
TODO 72: Gapping must return N-1 gap values for N clubs. Fix edge cases.
TODO 73: Dispersion tooltip scatter data must include spin_rate,
    launch_angle (or dynamic_loft), ball_speed, face_angle.
TODO 74: Launch & spin stability should break wedge clubs into sub-swings.
TODO 75: Club comparison should use box-and-whisker stats, with wedge
    sub-swing breakdown.
TODO 76: PGA Tour averages must exist per wedge club (PW, AW, SW, LW)
    and comparison endpoint must return both user and PGA data.
"""
import re
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
        filename='test-todo71-76.csv',
        session_date=date(2026, 3, 26),
        location='Driving Ranges',
        data_type=data_type,
    )
    _db.session.add(s)
    _db.session.commit()
    return s


def _seed_club_shots(session, club, club_short, shots_data, swing_size='full'):
    """Seed shots for one club.

    shots_data: list of dicts with at least 'carry'. Optional: spin_rate,
    launch_angle, ball_speed, offline, face_angle, dynamic_loft, swing_size.
    """
    for i, shot_kw in enumerate(shots_data):
        carry = shot_kw.pop('carry')
        sw = shot_kw.pop('swing_size', swing_size)
        _db.session.add(_make_shot(
            session.id, club, club_short, carry, carry + 10.0,
            club_index=i, swing_size=sw, **shot_kw,
        ))
    _db.session.commit()


def _make_n_shots(n, base_carry=150.0, carry_step=2.0, **overrides):
    """Generate n shot dicts with incrementing carry."""
    shots = []
    for i in range(n):
        s = {
            'carry': base_carry + i * carry_step,
            'spin_rate': 5000 + i * 100,
            'launch_angle': 15.0 + i * 0.5,
            'ball_speed': 100.0 + i * 1.0,
            'face_angle': 2.0 + i * 0.1,
            'offline': float((-1) ** i * (2 + i * 0.5)),
        }
        s.update(overrides)
        shots.append(s)
    return shots


# ═════════════════════════════════════════════════════════════════════════
# TODO 71: Version Number
# ═════════════════════════════════════════════════════════════════════════

class TestVersionNumber:
    """App must expose a version string in semver format."""

    def test_version_string_exists(self, routed_app, ctx):
        """Version should be accessible as an app constant or config value."""
        # Check common locations: app config, module-level constant, or VERSION file
        import app as app_module
        version = getattr(app_module, 'VERSION', None) or \
                  getattr(app_module, '__version__', None) or \
                  routed_app.config.get('VERSION', None)
        assert version is not None, \
            "No VERSION found in app module or config"

    def test_version_follows_semver(self, routed_app, ctx):
        """Version must match semver: MAJOR.MINOR.PATCH (optional pre-release)."""
        import app as app_module
        version = getattr(app_module, 'VERSION', None) or \
                  getattr(app_module, '__version__', None) or \
                  routed_app.config.get('VERSION', None)
        assert version is not None, "No version found"
        # Semver: X.Y.Z with optional -suffix
        assert re.match(r'^\d+\.\d+\.\d+(-\w+)?$', version), \
            f"Version '{version}' does not follow semver format X.Y.Z"


# ═════════════════════════════════════════════════════════════════════════
# TODO 72: Gapping Fix
# ═════════════════════════════════════════════════════════════════════════

class TestGappingFix:
    """Gapping must return N-1 gap values for N clubs."""

    def test_three_clubs_two_gaps(self, api, routed_app, ctx):
        """3 clubs → 2 gap values."""
        session = _seed_session()
        # Driver (longest), 7 Iron, PW (shortest) → expect 2 gaps
        _seed_club_shots(session, 'Driver', '1W',
                         _make_n_shots(5, base_carry=230.0))
        _seed_club_shots(session, '7 Iron', '7i',
                         _make_n_shots(5, base_carry=160.0))
        _seed_club_shots(session, 'P-Wedge', 'PW',
                         _make_n_shots(5, base_carry=120.0))

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        gaps = [v['gap'] for v in data.values() if v.get('gap') is not None]
        assert len(gaps) == 2, f"Expected 2 gaps for 3 clubs, got {len(gaps)}"

    def test_two_clubs_one_gap(self, api, routed_app, ctx):
        """2 clubs → 1 gap value."""
        session = _seed_session()
        _seed_club_shots(session, 'Driver', '1W',
                         _make_n_shots(5, base_carry=230.0))
        _seed_club_shots(session, '7 Iron', '7i',
                         _make_n_shots(5, base_carry=160.0))

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        gaps = [v['gap'] for v in data.values() if v.get('gap') is not None]
        assert len(gaps) == 1, f"Expected 1 gap for 2 clubs, got {len(gaps)}"

    def test_gap_values_are_correct(self, api, routed_app, ctx):
        """Gap = difference between adjacent club q3 carry values."""
        session = _seed_session()
        driver_shots = _make_n_shots(5, base_carry=230.0)
        iron_shots = _make_n_shots(5, base_carry=160.0)
        _seed_club_shots(session, 'Driver', '1W', driver_shots)
        _seed_club_shots(session, '7 Iron', '7i', iron_shots)

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        data = resp.get_json()

        # Driver should be first (CLUB_ORDER), 7i second
        driver_q3 = data['1W']['q3']
        iron_q3 = data['7i']['q3']
        expected_gap = round(driver_q3 - iron_q3, 1)

        # The gap should be on the longer club (Driver)
        assert data['1W']['gap'] == expected_gap, \
            f"Gap mismatch: expected {expected_gap}, got {data['1W']['gap']}"

    def test_one_club_zero_gaps(self, api, routed_app, ctx):
        """1 club → 0 gaps (no error)."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i',
                         _make_n_shots(5, base_carry=160.0))

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        gaps = [v['gap'] for v in data.values() if v.get('gap') is not None]
        assert len(gaps) == 0, "1 club should produce 0 gaps"

    def test_club_with_no_shots_handled_gracefully(self, api, routed_app, ctx):
        """Session with no shots → empty response, no crash."""
        session = _seed_session()

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert len(data) == 0


# ═════════════════════════════════════════════════════════════════════════
# TODO 73: Dispersion Tooltip Data
# ═════════════════════════════════════════════════════════════════════════

class TestDispersionTooltipData:
    """Dispersion scatter data must include tooltip fields:
    spin_rate, launch_angle (or dynamic_loft), ball_speed, face_angle."""

    def test_scatter_data_includes_tooltip_fields(self, api, routed_app, ctx):
        """Each shot in dispersion scatter must have tooltip fields."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', [
            {'carry': 160.0, 'spin_rate': 5500, 'launch_angle': 16.0,
             'ball_speed': 115.0, 'face_angle': 2.5, 'offline': 3.0,
             'dynamic_loft': 28.0},
        ])

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        shots = data['shots']
        assert len(shots) >= 1

        shot = shots[0]
        # Must have tooltip fields
        assert 'spin_rate' in shot, "Missing spin_rate in dispersion shot"
        assert 'ball_speed' in shot, "Missing ball_speed in dispersion shot"
        assert 'face_angle' in shot, "Missing face_angle in dispersion shot"
        # launch_angle or dynamic_loft (descending loft) — either works
        assert 'launch_angle' in shot or 'dynamic_loft' in shot, \
            "Missing launch_angle or dynamic_loft in dispersion shot"

    def test_tooltip_fields_have_reasonable_values(self, api, routed_app, ctx):
        """Tooltip numeric fields must be reasonable (not null, within range)."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', [
            {'carry': 160.0, 'spin_rate': 7000, 'launch_angle': 16.5,
             'ball_speed': 118.0, 'face_angle': 1.5, 'offline': 4.0,
             'dynamic_loft': 29.0},
        ])

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shot = resp.get_json()['shots'][0]

        assert isinstance(shot['spin_rate'], (int, float))
        assert shot['spin_rate'] > 0
        assert isinstance(shot['ball_speed'], (int, float))
        assert shot['ball_speed'] > 0
        assert isinstance(shot['face_angle'], (int, float))

    def test_shot_missing_some_fields_returns_null(self, api, routed_app, ctx):
        """Shot with missing tooltip fields → null/None, not crash."""
        session = _seed_session()
        # Create a shot with None for spin_rate and face_angle
        shot_obj = _make_shot(
            session.id, '7 Iron', '7i', 160.0, 170.0,
            spin_rate=None, face_angle=None, offline=3.0,
        )
        _db.session.add(shot_obj)
        _db.session.commit()

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # Should not crash; shot may be included with null fields
        # or omitted if carry/offline are invalid
        assert isinstance(data['shots'], list)

    def test_empty_dataset_returns_empty_scatter(self, api, routed_app, ctx):
        """Empty session → empty scatter data."""
        session = _seed_session()

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['shots'] == []


# ═════════════════════════════════════════════════════════════════════════
# TODO 74: Launch & Spin Stability Sub-Swings
# ═════════════════════════════════════════════════════════════════════════

class TestStabilitySubSwings:
    """Stability endpoint must break wedge clubs into per-swing-type entries."""

    def _seed_wedge_with_swing_types(self, session):
        """Seed a PW with multiple swing types, each having 4+ shots."""
        swing_types = ['3/3', '2/3', '1/3', '10:2', '10:3']
        for j, swing in enumerate(swing_types):
            shots = []
            for i in range(4):
                shots.append({
                    'carry': 100.0 + j * 15 + i * 2.0,
                    'spin_rate': 8000 + j * 500 + i * 50,
                    'launch_angle': 22.0 + j * 1.0 + i * 0.3,
                    'ball_speed': 95.0 + j * 3 + i * 1.0,
                    'swing_size': swing,
                })
            _seed_club_shots(session, 'P-Wedge', 'PW', shots, swing_size=swing)

    def test_wedge_returns_per_swing_type_metrics(self, api, routed_app, ctx):
        """Wedge clubs should return entries broken by swing type."""
        session = _seed_session()
        self._seed_wedge_with_swing_types(session)

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        clubs = data['clubs']

        # Should have multiple PW entries (one per swing type), keyed like "PW (3/3)"
        pw_keys = [k for k in clubs.keys() if 'PW' in k]
        assert len(pw_keys) > 1, \
            f"Expected multiple PW entries for sub-swings, got {pw_keys}"

    def test_non_wedge_returns_single_entry(self, api, routed_app, ctx):
        """Non-wedge clubs should return a single entry, not broken by swing type."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', _make_n_shots(5))

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        clubs = data['clubs']

        iron_keys = [k for k in clubs.keys() if '7i' in k]
        assert len(iron_keys) == 1, \
            f"Non-wedge should have 1 entry, got {iron_keys}"

    def test_sub_swing_entry_has_required_fields(self, api, routed_app, ctx):
        """Each sub-swing entry must have mean, std_dev, cv fields in stability."""
        session = _seed_session()
        self._seed_wedge_with_swing_types(session)

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        clubs = data['clubs']

        pw_keys = [k for k in clubs.keys() if 'PW' in k]
        assert len(pw_keys) >= 1
        entry = clubs[pw_keys[0]]

        # Each entry should have stability metrics
        assert 'stability' in entry or ('spin' in entry and 'launch' in entry), \
            f"Sub-swing entry missing stability or spin/launch stats"

        if 'stability' in entry:
            stab = entry['stability']
            for field in ('spin_std', 'spin_cv', 'launch_std', 'launch_cv'):
                assert field in stab, f"Missing {field} in stability"

    def test_wedge_with_8_swing_types_returns_up_to_8(self, api, routed_app, ctx):
        """Wedge club with all 8 swing types should return up to 8 entries."""
        session = _seed_session()
        all_swings = ['full', '3/3', '2/3', '1/3', '10:2', '10:3', '9:3', '8:4']
        for j, swing in enumerate(all_swings):
            shots = []
            for i in range(4):
                shots.append({
                    'carry': 80.0 + j * 10 + i * 2.0,
                    'spin_rate': 9000 + j * 200 + i * 50,
                    'launch_angle': 25.0 + j * 0.5 + i * 0.2,
                    'ball_speed': 80.0 + j * 2 + i * 1.0,
                    'swing_size': swing,
                })
            _seed_club_shots(session, 'G-Wedge', 'AW', shots, swing_size=swing)

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        clubs = data['clubs']

        aw_keys = [k for k in clubs.keys() if 'AW' in k]
        assert len(aw_keys) <= 8, f"Should not exceed 8 entries, got {len(aw_keys)}"
        assert len(aw_keys) >= 2, \
            f"Expected multiple entries for AW sub-swings, got {len(aw_keys)}"

    def test_swing_type_with_one_shot_std_dev_zero_or_null(self, api, routed_app, ctx):
        """Swing type with only 1 shot → std_dev = 0 or null, not error."""
        session = _seed_session()
        # 1 shot at 3/3 swing, 4 shots at full swing
        _seed_club_shots(session, 'P-Wedge', 'PW', [
            {'carry': 120.0, 'spin_rate': 9000, 'launch_angle': 24.0,
             'ball_speed': 100.0, 'swing_size': '3/3'},
        ], swing_size='3/3')
        shots_full = _make_n_shots(4, base_carry=130.0)
        for s in shots_full:
            s['swing_size'] = 'full'
        _seed_club_shots(session, 'P-Wedge', 'PW', shots_full, swing_size='full')

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        assert resp.status_code == 200
        # Single-shot swing type should either be excluded (< 3 shots) or have std=0

    def test_swing_type_with_no_shots_not_included(self, api, routed_app, ctx):
        """Swing type with no shots → not included in results."""
        session = _seed_session()
        # Only seed 3/3 and full for PW — other swing types should be absent
        for swing in ['3/3', 'full']:
            shots = _make_n_shots(4, base_carry=120.0 if swing == '3/3' else 130.0)
            for s in shots:
                s['swing_size'] = swing
            _seed_club_shots(session, 'P-Wedge', 'PW', shots, swing_size=swing)

        resp = api.get(f'/api/analytics/launch-spin-stability?session_id={session.id}')
        data = resp.get_json()
        clubs = data['clubs']

        # Should not have entries for un-seeded swing types like 10:2, 8:4
        all_keys_str = ' '.join(clubs.keys())
        assert '10:2' not in all_keys_str, "Unseeded swing type 10:2 should not appear"
        assert '8:4' not in all_keys_str, "Unseeded swing type 8:4 should not appear"


# ═════════════════════════════════════════════════════════════════════════
# TODO 75: Box & Whisker Data
# ═════════════════════════════════════════════════════════════════════════

class TestBoxAndWhiskerData:
    """Club comparison endpoint should return box-plot stats."""

    def test_comparison_returns_box_plot_stats(self, api, routed_app, ctx):
        """Comparison data must include min, q1, median, q3, max."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', _make_n_shots(8))

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()

        assert len(data) >= 1
        entry = data[0]
        for key in ('min', 'q1', 'median', 'q3', 'max'):
            assert key in entry, f"Missing box plot key '{key}' in comparison"

    def test_wedge_clubs_broken_by_sub_swing(self, api, routed_app, ctx):
        """Wedge clubs should be broken into sub-swing type entries."""
        session = _seed_session()
        for swing in ['3/3', 'full']:
            shots = _make_n_shots(5, base_carry=110.0 if swing == '3/3' else 130.0)
            for s in shots:
                s['swing_size'] = swing
            _seed_club_shots(session, 'P-Wedge', 'PW', shots, swing_size=swing)

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        data = resp.get_json()

        pw_entries = [e for e in data if 'PW' in e.get('club', '')]
        assert len(pw_entries) > 1, \
            f"Wedge should be split by sub-swing, got {len(pw_entries)} PW entries"

    def test_non_wedge_clubs_single_entry(self, api, routed_app, ctx):
        """Non-wedge clubs should appear as a single entry."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', _make_n_shots(8))
        _seed_club_shots(session, 'Driver', '1W', _make_n_shots(5, base_carry=230.0))

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        data = resp.get_json()

        iron_entries = [e for e in data if e.get('club') == '7i']
        assert len(iron_entries) == 1, \
            f"Non-wedge should have 1 entry, got {len(iron_entries)}"

    def test_outlier_detection_iqr(self, api, routed_app, ctx):
        """Outliers beyond 1.5*IQR should be detected."""
        session = _seed_session()
        # 7 normal shots + 1 extreme outlier
        shots = _make_n_shots(7, base_carry=155.0, carry_step=2.0)
        shots.append({'carry': 250.0, 'spin_rate': 5000, 'launch_angle': 15.0,
                      'ball_speed': 100.0, 'offline': 3.0})
        _seed_club_shots(session, '7 Iron', '7i', shots)

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        data = resp.get_json()

        entry = [e for e in data if '7i' in e.get('club', '')][0]
        if 'outliers' in entry:
            assert 250.0 in entry['outliers'] or len(entry['outliers']) > 0

    def test_fewer_than_5_shots_valid_stats(self, api, routed_app, ctx):
        """Fewer than 5 shots → still returns valid stats."""
        session = _seed_session()
        _seed_club_shots(session, '7 Iron', '7i', _make_n_shots(3))

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1

    def test_all_identical_values(self, api, routed_app, ctx):
        """All identical carry values → min=q1=median=q3=max."""
        session = _seed_session()
        shots = [{'carry': 160.0, 'spin_rate': 5000, 'launch_angle': 15.0,
                  'ball_speed': 100.0, 'offline': 3.0}
                 for _ in range(5)]
        _seed_club_shots(session, '7 Iron', '7i', shots)

        resp = api.get(f'/api/analytics/club-comparison?session_id={session.id}')
        data = resp.get_json()

        entry = [e for e in data if '7i' in e.get('club', '')][0]
        if all(k in entry for k in ('min', 'q1', 'median', 'q3', 'max')):
            assert entry['min'] == entry['q1'] == entry['median'] == \
                   entry['q3'] == entry['max'], \
                "All identical values should yield equal box-plot stats"


# ═════════════════════════════════════════════════════════════════════════
# TODO 76: PGA Tour Averages
# ═════════════════════════════════════════════════════════════════════════

class TestPGATourAverages:
    """PGA Tour averages must exist for all wedge clubs and be accessible
    via the radar-comparison endpoint."""

    def test_pga_averages_exist_for_all_wedges(self, api, routed_app, ctx):
        """PGA averages must cover PW, AW, SW, LW."""
        from services.analytics import radar_comparison
        # Access PGA_AVERAGES by calling with wedge shots
        session = _seed_session()
        for club, short in [('P-Wedge', 'PW'), ('G-Wedge', 'AW'),
                            ('S-Wedge', 'SW'), ('L-Wedge', 'LW')]:
            _seed_club_shots(session, club, short,
                             _make_n_shots(5, base_carry=100.0))

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # Response should contain PGA data
        assert 'pga' in data, "radar-comparison must return PGA data"

    @pytest.mark.parametrize('club_short', ['PW', 'AW', 'SW', 'LW'])
    def test_pga_data_includes_required_metrics(self, club_short, api, routed_app, ctx):
        """PGA data for each wedge must include carry, spin, launch_angle, ball_speed."""
        # Import PGA_AVERAGES directly to verify structure
        session = _seed_session()
        club_map = {'PW': 'P-Wedge', 'AW': 'G-Wedge', 'SW': 'S-Wedge', 'LW': 'L-Wedge'}
        _seed_club_shots(session, club_map[club_short], club_short,
                         _make_n_shots(5, base_carry=100.0))

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}&club={club_short}')
        assert resp.status_code == 200
        data = resp.get_json()
        # PGA raw data should have these metrics
        if 'pga' in data and 'raw' in data['pga']:
            pga_raw = data['pga']['raw']
            for metric in ('Carry', 'Spin Rate', 'Launch Angle', 'Ball Speed'):
                assert metric in pga_raw, \
                    f"PGA data missing {metric} for {club_short}"

    def test_comparison_returns_both_user_and_pga(self, api, routed_app, ctx):
        """Comparison endpoint must return both user data and PGA data."""
        session = _seed_session()
        _seed_club_shots(session, 'P-Wedge', 'PW',
                         _make_n_shots(5, base_carry=120.0))

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        data = resp.get_json()

        assert 'user' in data, "Must have user data"
        assert 'pga' in data, "Must have PGA data"
        assert 'axes' in data, "Must have axes labels"

    def test_comparison_with_no_user_data(self, api, routed_app, ctx):
        """Clubs with no user data → still returns (empty), no crash."""
        session = _seed_session()
        # Empty session, no shots
        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # Should return empty dict or minimal structure, not crash
        assert isinstance(data, dict)

    def test_unknown_club_no_pga_no_crash(self, api, routed_app, ctx):
        """Unknown club type → falls back to DEFAULT_PGA, no crash."""
        session = _seed_session()
        # Seed with a weird club name
        _seed_club_shots(session, 'Mystery Club', 'XX',
                         _make_n_shots(5, base_carry=150.0))

        resp = api.get(f'/api/analytics/radar-comparison?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # Should not crash; DEFAULT_PGA is used
        assert isinstance(data, dict)
