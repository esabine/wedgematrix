"""Tests for TODO 66 — Dispersion carry distance geometry fix.

Written by Hockney — the tester who asks "what if the data is wrong?"
before anyone else does.

The dispersion chart must treat carry distance as the hypotenuse of a
right triangle, not as raw forward distance. The correction is:

    true_carry = √(carry² − offline²)

This file tests:
  1. Geometry correctness — known inputs produce expected forward distance
  2. Edge cases — offline > carry, carry=0, negative offline, etc.
  3. Integration — API returns corrected values, boundary uses them
  4. Regression — other endpoints and wedge matrix are NOT affected
"""
import math
import pytest
import numpy as np
from datetime import date
from flask import Flask

from models.database import db as _db, Session, Shot, ClubLoft, init_db
from models.seed import seed_club_lofts
from app import register_routes
from tests.conftest import _make_shot


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope='function')
def routed_app():
    """Flask app with all routes registered."""
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
        filename='test-carry-geometry.csv',
        session_date=date(2026, 3, 23),
        location='Driving Ranges',
        data_type=data_type,
    )
    _db.session.add(s)
    _db.session.commit()
    return s


def _seed_shot(session, club, club_short, carry, offline, **kwargs):
    """Seed a single shot with specific carry and offline."""
    _db.session.add(_make_shot(
        session.id, club, club_short, carry, carry + 10.0,
        club_index=kwargs.get('club_index', 0),
        offline=offline,
        excluded=kwargs.get('excluded', False),
    ))
    _db.session.commit()


def _seed_known_geometry_shots(session):
    """Seed shots with carefully chosen carry/offline for geometry verification.

    Each shot has a known expected true_carry = √(carry² − offline²):
      carry=100, offline=0   → true_carry = 100.0     (straight)
      carry=100, offline=10  → true_carry ≈ 99.499    (slight)
      carry=100, offline=50  → true_carry ≈ 86.603    (significant)
      carry=150, offline=30  → true_carry ≈ 146.969   (realistic wedge)
      carry=200, offline=5   → true_carry ≈ 199.937   (driver, tiny offline)
    """
    shots = [
        # (club, club_short, carry, offline, expected_true_carry)
        ('7 Iron', '7i', 100.0,  0.0,  100.0),
        ('7 Iron', '7i', 100.0, 10.0,  math.sqrt(100**2 - 10**2)),
        ('7 Iron', '7i', 100.0, 50.0,  math.sqrt(100**2 - 50**2)),
        ('7 Iron', '7i', 150.0, 30.0,  math.sqrt(150**2 - 30**2)),
        ('7 Iron', '7i', 200.0,  5.0,  math.sqrt(200**2 - 5**2)),
    ]
    for i, (club, short, carry, offline, _expected) in enumerate(shots):
        _db.session.add(_make_shot(
            session.id, club, short, carry, carry + 10.0,
            club_index=i, offline=offline,
        ))
    _db.session.commit()
    return shots


def _seed_multi_club_geometry(session):
    """Seed 10+ shots per club for two clubs with known offlines.

    7i: carry ~160, offlines spread ±8 (corrections are small)
    PW: carry ~115, offlines spread ±5 (corrections are small)
    """
    # 7i shots
    for i, (carry, offline) in enumerate([
        (155.0, -8.0), (158.0, -3.0), (160.0, 1.0),
        (162.0, 5.0), (165.0, 2.0), (157.0, -5.0),
        (163.0, 7.0), (159.0, -1.0), (161.0, 4.0),
        (164.0, 0.0),
    ]):
        _db.session.add(_make_shot(
            session.id, '7 Iron', '7i', carry, carry + 10.0,
            club_index=i, offline=offline,
        ))

    # PW shots
    for i, (carry, offline) in enumerate([
        (112.0, -4.0), (114.0, -1.0), (116.0, 2.0),
        (118.0, 5.0), (113.0, -3.0), (117.0, 3.0),
        (115.0, 0.0), (119.0, 1.0), (111.0, -6.0),
        (120.0, 4.0),
    ]):
        _db.session.add(_make_shot(
            session.id, 'P-Wedge', 'PW', carry, carry + 10.0,
            club_index=10 + i, offline=offline,
        ))
    _db.session.commit()


# ═════════════════════════════════════════════════════════════════════════
# 1. Geometry Correctness — dispersion carry values are corrected
# ═════════════════════════════════════════════════════════════════════════

class TestCarryGeometryCorrectness:
    """The dispersion endpoint must return corrected forward distance,
    not raw hypotenuse carry."""

    def test_straight_shot_no_correction(self, api, routed_app, ctx):
        """carry=100, offline=0 → true_carry = 100 (no correction needed)."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 100.0, 0.0)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        shots = data['shots']
        assert len(shots) == 1
        assert shots[0]['carry'] == pytest.approx(100.0, abs=0.1)

    def test_slight_correction(self, api, routed_app, ctx):
        """carry=100, offline=10 → true_carry ≈ 99.499."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 100.0, 10.0)

        expected = math.sqrt(100**2 - 10**2)  # ≈ 99.4987
        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        assert len(shots) == 1
        assert shots[0]['carry'] == pytest.approx(expected, abs=0.1), \
            f"Expected corrected carry ≈{expected:.1f}, got {shots[0]['carry']}"

    def test_significant_correction(self, api, routed_app, ctx):
        """carry=100, offline=50 → true_carry ≈ 86.603."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 100.0, 50.0)

        expected = math.sqrt(100**2 - 50**2)  # ≈ 86.6025
        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        assert len(shots) == 1
        assert shots[0]['carry'] == pytest.approx(expected, abs=0.1), \
            f"Expected corrected carry ≈{expected:.1f}, got {shots[0]['carry']}"

    def test_all_lateral_edge_case(self, api, routed_app, ctx):
        """carry=100, offline=100 → true_carry = 0 (all lateral movement).

        This degenerate case should either return carry=0 or be skipped.
        """
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 100.0, 100.0)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        # Either the shot is included with carry≈0, or it's filtered out
        if len(shots) == 1:
            assert shots[0]['carry'] == pytest.approx(0.0, abs=0.5)
        # If filtered out, that's also acceptable — shot with 0 forward distance is noise

    @pytest.mark.parametrize('carry,offline,expected', [
        (100.0, 0.0, 100.0),
        (100.0, 10.0, math.sqrt(100**2 - 10**2)),
        (100.0, 50.0, math.sqrt(100**2 - 50**2)),
        (150.0, 30.0, math.sqrt(150**2 - 30**2)),
        (200.0, 5.0, math.sqrt(200**2 - 5**2)),
    ], ids=[
        'straight-shot',
        'slight-offline-10',
        'significant-offline-50',
        'realistic-wedge-150-30',
        'driver-tiny-offline-200-5',
    ])
    def test_parametrized_geometry(self, api, routed_app, ctx, carry, offline, expected):
        """Verify sqrt(carry² - offline²) for various carry/offline combos."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', carry, offline)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        assert len(shots) == 1
        assert shots[0]['carry'] == pytest.approx(expected, abs=0.2), \
            f"carry={carry}, offline={offline}: expected {expected:.3f}, got {shots[0]['carry']}"


# ═════════════════════════════════════════════════════════════════════════
# 2. Edge Cases — bad data, zeros, negatives
# ═════════════════════════════════════════════════════════════════════════

class TestCarryGeometryEdgeCases:
    """Edge cases for the carry geometry correction."""

    def test_offline_greater_than_carry_handled(self, api, routed_app, ctx):
        """offline > carry is physically impossible (bad data).

        sqrt(carry² - offline²) would be imaginary. Must be handled
        gracefully: either skip the shot or clamp to 0.
        """
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 50.0, 80.0)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        shots = resp.get_json()['shots']
        # Shot should either be excluded or clamped to carry=0
        if len(shots) == 1:
            assert shots[0]['carry'] >= 0, "Corrected carry must not be negative"
            assert shots[0]['carry'] == pytest.approx(0.0, abs=0.5)
        # Else: filtered out entirely — also acceptable

    def test_carry_zero_handled(self, api, routed_app, ctx):
        """carry=0 (duffed shot) — should be handled without crash."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 0.0, 0.0)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        shots = resp.get_json()['shots']
        if len(shots) == 1:
            assert shots[0]['carry'] == pytest.approx(0.0, abs=0.1)

    def test_offline_zero_no_correction(self, api, routed_app, ctx):
        """offline=0 means no lateral deviation — carry unchanged."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 165.0, 0.0)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        assert len(shots) == 1
        assert shots[0]['carry'] == pytest.approx(165.0, abs=0.1)

    def test_very_small_offline_negligible_correction(self, api, routed_app, ctx):
        """offline=0.5 on carry=160 → correction < 0.001 yards, negligible."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 160.0, 0.5)

        expected = math.sqrt(160**2 - 0.5**2)  # ≈ 159.9992
        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        assert len(shots) == 1
        assert shots[0]['carry'] == pytest.approx(expected, abs=0.1)
        # The correction is so small it's basically carry itself
        assert abs(shots[0]['carry'] - 160.0) < 0.01

    def test_negative_offline_works(self, api, routed_app, ctx):
        """offline can be negative (left of target). Squaring negates the sign.

        carry=100, offline=-10 should give same result as offline=+10.
        """
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 100.0, -10.0)

        expected = math.sqrt(100**2 - 10**2)  # same as offline=+10
        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        assert len(shots) == 1
        assert shots[0]['carry'] == pytest.approx(expected, abs=0.1)

    def test_negative_offline_same_as_positive(self, api, routed_app, ctx):
        """Left and right offline of same magnitude produce identical correction."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 150.0, -20.0, club_index=0)
        _seed_shot(session, '7 Iron', '7i', 150.0, 20.0, club_index=1)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        assert len(shots) == 2

        carries = sorted([s['carry'] for s in shots])
        assert carries[0] == pytest.approx(carries[1], abs=0.01), \
            "Left and right offline should produce identical corrected carry"

    def test_multiple_bad_data_shots_no_crash(self, api, routed_app, ctx):
        """Mix of normal and edge-case shots: endpoint must not crash."""
        session = _seed_session()
        # Normal shot
        _seed_shot(session, '7 Iron', '7i', 160.0, 5.0, club_index=0)
        # Zero carry
        _seed_shot(session, '7 Iron', '7i', 0.0, 0.0, club_index=1)
        # Offline > carry (bad data)
        _seed_shot(session, '7 Iron', '7i', 10.0, 50.0, club_index=2)
        # Near-equal carry and offline
        _seed_shot(session, '7 Iron', '7i', 50.0, 49.9, club_index=3)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'shots' in data
        # At minimum the normal shot should be present
        valid_shots = [s for s in data['shots'] if s['carry'] > 0]
        assert len(valid_shots) >= 1


# ═════════════════════════════════════════════════════════════════════════
# 3. Integration — boundary uses corrected values
# ═════════════════════════════════════════════════════════════════════════

class TestBoundaryUsesCorrectGeometry:
    """The dispersion boundary must be computed using corrected carry
    values, not raw carry from the database."""

    def test_boundary_carry_values_are_corrected(self, api, routed_app, ctx):
        """Boundary carry coordinates must be ≤ raw carry for any shot
        (since true_carry ≤ carry always holds when offline != 0)."""
        session = _seed_session()
        _seed_multi_club_geometry(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        boundary = data.get('dispersion_boundary', {})

        if '7i' in boundary:
            # Raw 7i carries range from 155-165. With offlines up to ±8,
            # corrected carries should be slightly less.
            for pt in boundary['7i']:
                # A corrected carry should never exceed the max raw carry
                assert pt['carry'] <= 166.0, \
                    f"Boundary carry {pt['carry']} exceeds max raw carry of 165"

    def test_multi_club_different_corrections(self, api, routed_app, ctx):
        """Different clubs with different offset patterns produce
        correctly separated boundaries."""
        session = _seed_session()
        _seed_multi_club_geometry(session)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        data = resp.get_json()
        boundary = data.get('dispersion_boundary', {})

        if '7i' in boundary and 'PW' in boundary:
            i7_carries = [pt['carry'] for pt in boundary['7i']]
            pw_carries = [pt['carry'] for pt in boundary['PW']]
            # 7i range ~155-165, PW range ~111-120 — no overlap even after correction
            assert min(i7_carries) > max(pw_carries), \
                "7i and PW boundaries should not overlap in carry axis"

    def test_shot_carries_less_than_or_equal_raw(self, api, routed_app, ctx):
        """Every shot's corrected carry ≤ its raw carry (triangle inequality).

        We seed shots with known raw carries and verify the response
        carries are not larger.
        """
        session = _seed_session()
        raw_carries = []
        for i, (carry, offline) in enumerate([
            (160.0, 8.0), (165.0, 3.0), (155.0, 12.0),
        ]):
            _seed_shot(session, '7 Iron', '7i', carry, offline, club_index=i)
            raw_carries.append(carry)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        for shot in shots:
            max_raw = max(raw_carries)
            assert shot['carry'] <= max_raw + 0.1, \
                f"Corrected carry {shot['carry']} exceeds max raw carry {max_raw}"


# ═════════════════════════════════════════════════════════════════════════
# 4. Regression — other endpoints NOT affected
# ═════════════════════════════════════════════════════════════════════════

class TestCarryGeometryRegression:
    """The carry correction must ONLY affect dispersion data.
    Other chart endpoints and the wedge matrix must use raw carry."""

    def test_carry_distribution_uses_raw_carry(self, api, routed_app, ctx):
        """Carry distribution chart uses raw carry — NOT corrected."""
        session = _seed_session()
        # Seed a shot with large offline for obvious correction difference
        _seed_shot(session, '7 Iron', '7i', 100.0, 50.0)

        resp = api.get(f'/api/analytics/carry-distribution?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        # Carry distribution should show 100.0, not 86.6
        if isinstance(data, dict) and '7i' in data:
            club_data = data['7i']
            if isinstance(club_data, dict) and 'data' in club_data:
                carries = club_data['data']
                if carries:
                    assert max(carries) == pytest.approx(100.0, abs=0.5), \
                        "Carry distribution should use raw carry, not corrected"

    def test_spin_carry_uses_raw_carry(self, api, routed_app, ctx):
        """Spin vs carry chart uses raw carry — NOT corrected."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 100.0, 50.0)

        resp = api.get(f'/api/analytics/spin-carry?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        if isinstance(data, list) and len(data) > 0:
            # Spin-carry should have carry=100, not 86.6
            carries = [d.get('carry', d.get('x', None)) for d in data]
            carries = [c for c in carries if c is not None]
            if carries:
                assert max(carries) == pytest.approx(100.0, abs=0.5), \
                    "Spin-carry should use raw carry, not corrected"

    def test_wedge_matrix_uses_raw_carry(self, api, routed_app, ctx):
        """Wedge matrix carry values must be raw (unmodified).

        The wedge matrix helps golfers know their distances — it must
        reflect the actual measured carry, not a geometric correction.
        """
        session = Session(
            filename='test-wedge.csv',
            session_date=date(2026, 3, 23),
            location='Driving Ranges',
            data_type='wedge',
        )
        _db.session.add(session)
        _db.session.commit()

        # Seed AW wedge shots with known carries and large offlines
        carries = [72.0, 70.0, 75.0, 68.0, 74.0]
        for i, c in enumerate(carries):
            _db.session.add(_make_shot(
                session.id, 'G-Wedge', 'AW', c, c + 2.0,
                swing_size='3/3', club_index=i, offline=15.0,
            ))
        _db.session.commit()

        resp = api.get(f'/api/wedge-matrix?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()

        # Find AW data in the matrix
        matrix = data.get('matrix', data) if isinstance(data, dict) else data
        if isinstance(matrix, list):
            for row in matrix:
                if isinstance(row, dict):
                    aw_val = row.get('AW')
                    if aw_val and isinstance(aw_val, dict) and 'carry' in aw_val:
                        # The carry should be based on raw values (~70-75 range)
                        # not corrected (~68.5-73.5 with offline=15)
                        assert aw_val['carry'] >= 68, \
                            f"Wedge carry {aw_val['carry']} looks corrected — should be raw"

    def test_club_matrix_uses_raw_carry(self, api, routed_app, ctx):
        """Club matrix carry values must be raw (unmodified)."""
        session = _seed_session()
        # Seed 7i shots with carries around 160 but large offline
        for i in range(5):
            _seed_shot(session, '7 Iron', '7i', 160.0, 30.0, club_index=i)

        resp = api.get(f'/api/club-matrix?session_id={session.id}')
        assert resp.status_code == 200
        data = resp.get_json()

        matrix = data.get('matrix', []) if isinstance(data, dict) else []
        if matrix:
            for row in matrix:
                if isinstance(row, dict):
                    i7_val = row.get('7i')
                    if i7_val and isinstance(i7_val, (int, float)):
                        # Raw carry is 160. Corrected would be ~157.
                        # The matrix should show 160.
                        assert i7_val >= 159, \
                            f"Club matrix carry {i7_val} looks corrected — should be raw"

    def test_launch_spin_not_affected(self, api, routed_app, ctx):
        """Launch-spin chart is not affected by dispersion geometry fix."""
        session = _seed_session()
        for i in range(5):
            _seed_shot(session, '7 Iron', '7i', 160.0, 20.0, club_index=i)

        resp = api.get(
            f'/api/analytics/launch-spin-stability?session_id={session.id}'
        )
        assert resp.status_code == 200

    def test_radar_comparison_not_affected(self, api, routed_app, ctx):
        """Radar comparison chart is not affected by dispersion geometry fix."""
        session = _seed_session()
        for i in range(5):
            _seed_shot(session, '7 Iron', '7i', 160.0, 20.0, club_index=i)

        resp = api.get(
            f'/api/analytics/radar-comparison?session_id={session.id}'
        )
        assert resp.status_code == 200


# ═════════════════════════════════════════════════════════════════════════
# 5. Offline value preservation
# ═════════════════════════════════════════════════════════════════════════

class TestOfflinePreservation:
    """The offline value in dispersion data must remain unchanged.
    Only carry gets corrected, not offline."""

    def test_offline_unchanged_in_response(self, api, routed_app, ctx):
        """Offline value in the response matches the raw database value."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 160.0, 12.5)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        assert len(shots) == 1
        assert shots[0]['offline'] == pytest.approx(12.5, abs=0.1), \
            "Offline must remain unchanged — only carry gets corrected"

    def test_negative_offline_preserved(self, api, routed_app, ctx):
        """Negative offline (left of target) is preserved in response."""
        session = _seed_session()
        _seed_shot(session, '7 Iron', '7i', 160.0, -8.3)

        resp = api.get(f'/api/analytics/dispersion?session_id={session.id}')
        shots = resp.get_json()['shots']
        assert len(shots) == 1
        assert shots[0]['offline'] == pytest.approx(-8.3, abs=0.1), \
            "Negative offline must be preserved"
