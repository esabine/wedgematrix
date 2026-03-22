"""Tests for TODO 61 (test-data sessions), TODO 62 (swing size renames),
and TODO 63 (PW in wedge matrix).

Written by Hockney — testing the behavioral contracts BEFORE the
implementation lands.  These tests describe what the system MUST do,
not what it currently does.

Feature 1 (TODO 61): is_test flag on sessions, toggle endpoint,
    default exclusion from analytics/shots/matrices.
Feature 2 (TODO 62): "4/4" removed, swing labels 3/4→3/3, 2/4→2/3, 1/4→1/3.
Feature 3 (TODO 63): PW included in wedge matrix, column order PW,AW,SW,LW.
"""
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


def _create_session(data_type='club', is_test=False, filename='test.csv'):
    """Create and commit a Session, returning its id."""
    sess = Session(
        filename=filename,
        session_date=date(2026, 3, 20),
        location='Driving Range',
        data_type=data_type,
    )
    # Set is_test if the column exists (feature 1 may not be merged yet)
    if hasattr(Session, 'is_test'):
        sess.is_test = is_test
    _db.session.add(sess)
    _db.session.commit()
    return sess.id


def _seed_wedge_shots(session_id, club, club_short, swing_size, carries):
    """Seed multiple wedge shots for a given club/swing combo."""
    for i, carry in enumerate(carries):
        _db.session.add(_make_shot(
            session_id, club, club_short, carry, carry + 2.0,
            swing_size=swing_size, club_index=i,
        ))
    _db.session.commit()


# ═══════════════════════════════════════════════════════════════════════
# Feature 1: Test-data session facility (TODO 61)
# ═══════════════════════════════════════════════════════════════════════

class TestTestDataSessionModel:
    """Session.is_test column exists and defaults to False."""

    def test_session_has_is_test_column(self, routed_app, ctx):
        """The sessions table must have an is_test boolean column."""
        sid = _create_session()
        sess = Session.query.get(sid)
        assert hasattr(sess, 'is_test'), "Session model missing 'is_test' column"
        assert sess.is_test is False or sess.is_test == 0

    def test_session_is_test_default_false(self, routed_app, ctx):
        """New sessions default to is_test=False."""
        sid = _create_session()
        sess = Session.query.get(sid)
        assert not sess.is_test


class TestToggleTestEndpoint:
    """POST /api/sessions/<id>/toggle-test toggles is_test flag."""

    def test_toggle_test_on(self, routed_app, api, ctx):
        sid = _create_session()
        resp = api.post(f'/api/sessions/{sid}/toggle-test')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_test'] is True

    def test_toggle_test_off(self, routed_app, api, ctx):
        sid = _create_session(is_test=False)
        # Toggle once → True
        resp1 = api.post(f'/api/sessions/{sid}/toggle-test')
        assert resp1.status_code == 200
        assert resp1.get_json()['is_test'] is True
        # Toggle again → False
        resp2 = api.post(f'/api/sessions/{sid}/toggle-test')
        assert resp2.status_code == 200
        data = resp2.get_json()
        assert data['is_test'] is False

    def test_toggle_nonexistent_session_404(self, routed_app, api, ctx):
        resp = api.post('/api/sessions/99999/toggle-test')
        assert resp.status_code == 404


class TestTestSessionExcludedFromAnalytics:
    """Test sessions excluded from analytics by default, included with param."""

    def test_test_session_excluded_from_club_stats(self, routed_app, api, ctx):
        """Shots in a test session must not appear in analytics by default."""
        from services.analytics import compute_percentile_for_club

        # Real session with known carries
        real_sid = _create_session(is_test=False, filename='real.csv')
        for i, carry in enumerate([150, 160, 170, 180, 190]):
            _db.session.add(_make_shot(
                real_sid, '7 Iron', '7i', float(carry), float(carry + 10),
                club_index=i))

        # Test session with extreme carries that would skew results
        test_sid = _create_session(is_test=True, filename='test-data.csv')
        for i, carry in enumerate([300, 310, 320]):
            _db.session.add(_make_shot(
                test_sid, '7 Iron', '7i', float(carry), float(carry + 10),
                club_index=i))
        _db.session.commit()

        # When querying without include_test, only real data contributes
        # P75 of [150,160,170,180,190] = 180
        result = compute_percentile_for_club(real_sid, '7i', 75)
        expected = float(np.percentile([150, 160, 170, 180, 190], 75))
        assert result == pytest.approx(expected, abs=1.0)


class TestTestSessionExcludedFromShots:
    """Test session shots excluded from /api/shots by default."""

    def test_api_shots_excludes_test_sessions(self, routed_app, api, ctx):
        real_sid = _create_session(is_test=False, filename='real.csv')
        _db.session.add(_make_shot(real_sid, '7 Iron', '7i', 160.0, 170.0))
        _db.session.commit()

        test_sid = _create_session(is_test=True, filename='test-data.csv')
        _db.session.add(_make_shot(test_sid, '7 Iron', '7i', 300.0, 310.0))
        _db.session.commit()

        resp = api.get('/api/shots')
        assert resp.status_code == 200
        data = resp.get_json()
        shot_session_ids = {s['session_id'] for s in data['shots']}
        assert test_sid not in shot_session_ids
        assert real_sid in shot_session_ids

    def test_api_shots_includes_test_with_param(self, routed_app, api, ctx):
        """include_test=true brings test session shots back."""
        real_sid = _create_session(is_test=False, filename='real.csv')
        _db.session.add(_make_shot(real_sid, '7 Iron', '7i', 160.0, 170.0))

        test_sid = _create_session(is_test=True, filename='test-data.csv')
        _db.session.add(_make_shot(test_sid, '7 Iron', '7i', 300.0, 310.0))
        _db.session.commit()

        resp = api.get('/api/shots?include_test=true')
        assert resp.status_code == 200
        data = resp.get_json()
        shot_session_ids = {s['session_id'] for s in data['shots']}
        assert test_sid in shot_session_ids
        assert real_sid in shot_session_ids


class TestTestSessionExcludedFromClubMatrix:
    """Club matrix excludes test session data by default."""

    def test_club_matrix_excludes_test_sessions(self, routed_app, api, ctx):
        real_sid = _create_session(is_test=False, filename='real.csv')
        for i, carry in enumerate([150, 160, 170]):
            _db.session.add(_make_shot(
                real_sid, '7 Iron', '7i', float(carry), float(carry + 10),
                club_index=i))

        test_sid = _create_session(is_test=True, filename='test-data.csv')
        for i, carry in enumerate([300, 310, 320]):
            _db.session.add(_make_shot(
                test_sid, '7 Iron', '7i', float(carry), float(carry + 10),
                club_index=i))
        _db.session.commit()

        # All-sessions club matrix should NOT include test session data
        resp = api.get('/api/club-matrix')
        assert resp.status_code == 200
        data = resp.get_json()
        matrix = data.get('matrix', data)

        # If matrix is the build_club_matrix full result
        if isinstance(matrix, dict) and 'matrix' in matrix:
            rows = matrix['matrix']
        elif isinstance(matrix, list):
            rows = matrix
        else:
            rows = matrix

        if isinstance(rows, list):
            row_7i = next((r for r in rows if r.get('club_short') == '7i'
                           or r.get('club') == '7i'), None)
            if row_7i:
                # Max total from real data is 180, not 330
                assert row_7i['max'] <= 200

    def test_club_matrix_includes_test_with_param(self, routed_app, api, ctx):
        """include_test=true adds test session data to the matrix."""
        real_sid = _create_session(is_test=False, filename='real.csv')
        for i, carry in enumerate([150, 160, 170]):
            _db.session.add(_make_shot(
                real_sid, '7 Iron', '7i', float(carry), float(carry + 10),
                club_index=i))

        test_sid = _create_session(is_test=True, filename='test-data.csv')
        for i, carry in enumerate([300, 310, 320]):
            _db.session.add(_make_shot(
                test_sid, '7 Iron', '7i', float(carry), float(carry + 10),
                club_index=i))
        _db.session.commit()

        resp = api.get('/api/club-matrix?include_test=true')
        assert resp.status_code == 200
        data = resp.get_json()
        matrix = data.get('matrix', data)

        if isinstance(matrix, dict) and 'matrix' in matrix:
            rows = matrix['matrix']
        elif isinstance(matrix, list):
            rows = matrix
        else:
            rows = matrix

        if isinstance(rows, list):
            row_7i = next((r for r in rows if r.get('club_short') == '7i'
                           or r.get('club') == '7i'), None)
            if row_7i:
                # Max total should now be 330 (from test session)
                assert row_7i['max'] >= 300


class TestTestSessionExcludedFromWedgeMatrix:
    """Wedge matrix excludes test session data by default."""

    def test_wedge_matrix_excludes_test_sessions(self, routed_app, api, ctx):
        real_sid = _create_session(is_test=False, data_type='wedge',
                                   filename='real-wedge.csv')
        _seed_wedge_shots(real_sid, 'G-Wedge', 'AW', '3/3', [70, 75, 80])

        test_sid = _create_session(is_test=True, data_type='wedge',
                                    filename='test-wedge.csv')
        _seed_wedge_shots(test_sid, 'G-Wedge', 'AW', '3/3', [200, 210, 220])
        _db.session.commit()

        resp = api.get('/api/wedge-matrix')
        assert resp.status_code == 200
        data = resp.get_json()
        matrix = data.get('matrix', {})

        # AW 3/3 carry from real data should be ≤ 100
        cell = matrix.get('3/3', {}).get('AW')
        if cell is not None:
            carry_val = cell['carry'] if isinstance(cell, dict) else cell
            assert carry_val <= 100

    def test_wedge_matrix_includes_test_with_param(self, routed_app, api, ctx):
        real_sid = _create_session(is_test=False, data_type='wedge',
                                   filename='real-wedge.csv')
        _seed_wedge_shots(real_sid, 'G-Wedge', 'AW', '3/3', [70, 75, 80])

        test_sid = _create_session(is_test=True, data_type='wedge',
                                    filename='test-wedge.csv')
        _seed_wedge_shots(test_sid, 'G-Wedge', 'AW', '3/3', [200, 210, 220])
        _db.session.commit()

        resp = api.get('/api/wedge-matrix?include_test=true')
        assert resp.status_code == 200
        data = resp.get_json()
        matrix = data.get('matrix', {})

        cell = matrix.get('3/3', {}).get('AW')
        if cell is not None:
            carry_val = cell['carry'] if isinstance(cell, dict) else cell
            assert carry_val >= 100  # includes the 200+ yard test data


class TestToggleTestRoundTrip:
    """Toggle on, verify excluded, toggle off, verify included again."""

    def test_toggle_on_excludes_toggle_off_includes(self, routed_app, api, ctx):
        sid = _create_session(is_test=False, filename='toggle-test.csv')
        _db.session.add(_make_shot(sid, '7 Iron', '7i', 165.0, 175.0))
        _db.session.commit()

        # Before toggle: shots appear
        resp = api.get('/api/shots')
        data = resp.get_json()
        assert any(s['session_id'] == sid for s in data['shots'])

        # Toggle on → test session → excluded
        api.post(f'/api/sessions/{sid}/toggle-test')
        resp = api.get('/api/shots')
        data = resp.get_json()
        assert not any(s['session_id'] == sid for s in data['shots'])

        # Toggle off → back to normal → included again
        api.post(f'/api/sessions/{sid}/toggle-test')
        resp = api.get('/api/shots')
        data = resp.get_json()
        assert any(s['session_id'] == sid for s in data['shots'])


# ═══════════════════════════════════════════════════════════════════════
# Feature 2: Wedge matrix swing sizes (TODO 62)
# ═══════════════════════════════════════════════════════════════════════

class TestSwingSizeRenames:
    """4/4 removed; 3/4→3/3, 2/4→2/3, 1/4→1/3."""

    def test_wedge_matrix_no_four_four(self, routed_app, ctx):
        """The wedge matrix must NOT contain a '4/4' swing size row."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='swing-rename.csv')
        # Seed some AW shots at the old "4/4" swing size
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '4/4', [88, 90, 92])

        result = build_wedge_matrix(session_id=sid, percentile=75)
        swing_sizes = result.get('swing_sizes', [])
        matrix = result.get('matrix', {})

        assert '4/4' not in swing_sizes, "4/4 must be removed from swing sizes"
        assert '4/4' not in matrix, "4/4 must not appear as a matrix key"

    def test_wedge_matrix_has_new_fraction_names(self, routed_app, ctx):
        """Wedge matrix must use 3/3, 2/3, 1/3 (not 3/4, 2/4, 1/4)."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='swing-rename.csv')
        # Seed shots at old-style swing sizes
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '3/4', [70, 72, 74])
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '2/4', [55, 57, 59])
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '1/4', [30, 32, 34])

        result = build_wedge_matrix(session_id=sid, percentile=75)
        swing_sizes = result.get('swing_sizes', [])
        matrix = result.get('matrix', {})

        # New names must be present
        for new_name in ['3/3', '2/3', '1/3']:
            assert new_name in swing_sizes, f"{new_name} missing from swing_sizes"
            assert new_name in matrix, f"{new_name} missing from matrix keys"

        # Old names must NOT be present
        for old_name in ['3/4', '2/4', '1/4']:
            assert old_name not in swing_sizes, f"Old name {old_name} still in swing_sizes"
            assert old_name not in matrix, f"Old name {old_name} still in matrix keys"

    def test_old_swing_labels_mapped_correctly(self, routed_app, ctx):
        """Shots stored with old swing size labels (3/4, 2/4, 1/4) should
        appear under the new labels (3/3, 2/3, 1/3) in the matrix output."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='mapping.csv')
        # These shots have the OLD labels in the database
        _seed_wedge_shots(sid, 'S-Wedge', 'SW', '3/4', [60, 62, 64])

        result = build_wedge_matrix(session_id=sid, percentile=75)
        matrix = result.get('matrix', {})

        # The data should appear under '3/3', not '3/4'
        cell_new = matrix.get('3/3', {}).get('SW')
        cell_old = matrix.get('3/4', {}).get('SW') if '3/4' in matrix else None

        assert cell_new is not None, "SW 3/3 cell should have data (mapped from 3/4)"
        if cell_old is not None:
            # If old key still exists, it should be empty
            assert cell_old is None or cell_old == {}

    def test_swing_sizes_list_correct_order(self, routed_app, ctx):
        """The swing_sizes list must contain the new names in correct order."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='order.csv')
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '3/3', [70, 72])

        result = build_wedge_matrix(session_id=sid, percentile=75)
        swing_sizes = result.get('swing_sizes', [])

        # Fraction sizes should come first, then clock sizes
        expected_fractions = ['3/3', '2/3', '1/3']
        expected_clocks = ['10:2', '10:3', '9:3', '8:4']

        # All fraction sizes should appear before any clock sizes
        fraction_indices = [swing_sizes.index(s) for s in expected_fractions
                           if s in swing_sizes]
        clock_indices = [swing_sizes.index(s) for s in expected_clocks
                         if s in swing_sizes]

        if fraction_indices and clock_indices:
            assert max(fraction_indices) < min(clock_indices), \
                "Fraction sizes must come before clock sizes"


class TestSwingSizeRenamesInApi:
    """API endpoint reflects the new swing size names."""

    def test_api_wedge_matrix_no_four_four(self, routed_app, api, ctx):
        sid = _create_session(data_type='wedge', filename='api-swing.csv')
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '4/4', [85, 88, 90])

        resp = api.get(f'/api/wedge-matrix?session_id={sid}')
        assert resp.status_code == 200
        data = resp.get_json()

        swing_sizes = data.get('swing_sizes', [])
        matrix = data.get('matrix', {})
        assert '4/4' not in swing_sizes
        assert '4/4' not in matrix

    def test_api_wedge_matrix_new_names(self, routed_app, api, ctx):
        sid = _create_session(data_type='wedge', filename='api-swing.csv')
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '3/4', [70, 72, 74])

        resp = api.get(f'/api/wedge-matrix?session_id={sid}')
        assert resp.status_code == 200
        data = resp.get_json()

        swing_sizes = data.get('swing_sizes', [])
        assert '3/3' in swing_sizes
        assert '3/4' not in swing_sizes


# ═══════════════════════════════════════════════════════════════════════
# Feature 3: PW in wedge matrix (TODO 63)
# ═══════════════════════════════════════════════════════════════════════

class TestPWInWedgeMatrix:
    """PW is now included in the wedge matrix."""

    def test_wedge_matrix_includes_pw(self, routed_app, ctx):
        """PW must appear in the wedge matrix clubs list."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='pw-wedge.csv')
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '3/3', [110, 112, 115])
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '3/3', [90, 92, 95])

        result = build_wedge_matrix(session_id=sid, percentile=75)
        clubs = result.get('clubs', [])
        assert 'PW' in clubs, "PW must be in the wedge matrix clubs list"

    def test_wedge_matrix_pw_data_computed(self, routed_app, ctx):
        """PW cells must contain carry values computed with same percentile logic."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='pw-data.csv')
        pw_carries = [108.0, 112.0, 116.0, 120.0, 124.0]
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '3/3', pw_carries)

        result = build_wedge_matrix(session_id=sid, percentile=75)
        matrix = result.get('matrix', {})

        pw_cell = matrix.get('3/3', {}).get('PW')
        assert pw_cell is not None, "PW should have data in 3/3 row"

        expected_carry = round(float(np.percentile(pw_carries, 75)))
        carry_val = pw_cell['carry'] if isinstance(pw_cell, dict) else pw_cell
        assert carry_val == pytest.approx(expected_carry, abs=1)

    def test_wedge_matrix_club_order_pw_before_aw(self, routed_app, ctx):
        """Club column order must be: PW, AW, SW, LW."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='pw-order.csv')
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '3/3', [110, 115])
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '3/3', [90, 95])
        _seed_wedge_shots(sid, 'S-Wedge', 'SW', '3/3', [80, 85])
        _seed_wedge_shots(sid, 'L-Wedge', 'LW', '3/3', [60, 65])

        result = build_wedge_matrix(session_id=sid, percentile=75)
        clubs = result.get('clubs', [])

        assert clubs == ['PW', 'AW', 'SW', 'LW'], \
            f"Expected ['PW', 'AW', 'SW', 'LW'], got {clubs}"

    def test_wedge_matrix_pw_percentile_logic(self, routed_app, ctx):
        """PW percentile logic matches other wedges — verify P50 vs P90."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='pw-pct.csv')
        carries = [100.0, 105.0, 110.0, 115.0, 120.0]
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '3/3', carries)

        m50 = build_wedge_matrix(session_id=sid, percentile=50)
        m90 = build_wedge_matrix(session_id=sid, percentile=90)

        cell50 = m50['matrix'].get('3/3', {}).get('PW')
        cell90 = m90['matrix'].get('3/3', {}).get('PW')

        c50 = cell50['carry'] if isinstance(cell50, dict) else cell50
        c90 = cell90['carry'] if isinstance(cell90, dict) else cell90

        assert c50 is not None and c90 is not None
        assert c90 >= c50, "P90 carry must be >= P50 carry for PW"

        # Verify against numpy
        expected_50 = round(float(np.percentile(carries, 50)))
        expected_90 = round(float(np.percentile(carries, 90)))
        assert c50 == pytest.approx(expected_50, abs=1)
        assert c90 == pytest.approx(expected_90, abs=1)


class TestPWInWedgeMatrixApi:
    """API endpoint includes PW data."""

    def test_api_wedge_matrix_includes_pw(self, routed_app, api, ctx):
        sid = _create_session(data_type='wedge', filename='api-pw.csv')
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '3/3', [110, 112, 115])
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '3/3', [90, 92, 95])

        resp = api.get(f'/api/wedge-matrix?session_id={sid}')
        assert resp.status_code == 200
        data = resp.get_json()

        clubs = data.get('clubs', [])
        assert 'PW' in clubs, "PW must appear in API wedge matrix clubs"

    def test_api_wedge_matrix_pw_aw_order(self, routed_app, api, ctx):
        """PW must come before AW in the API response."""
        sid = _create_session(data_type='wedge', filename='api-pw-order.csv')
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '3/3', [110, 115])
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '3/3', [90, 95])

        resp = api.get(f'/api/wedge-matrix?session_id={sid}')
        assert resp.status_code == 200
        data = resp.get_json()

        clubs = data.get('clubs', [])
        if 'PW' in clubs and 'AW' in clubs:
            assert clubs.index('PW') < clubs.index('AW'), \
                "PW must come before AW in column order"

    def test_api_wedge_matrix_pw_clock_carry_max(self, routed_app, api, ctx):
        """PW clock-hand swings should have carry AND max."""
        sid = _create_session(data_type='wedge', filename='api-pw-clock.csv')
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '10:2', [100, 105, 110])

        resp = api.get(f'/api/wedge-matrix?session_id={sid}')
        assert resp.status_code == 200
        data = resp.get_json()
        matrix = data.get('matrix', {})

        pw_cell = matrix.get('10:2', {}).get('PW')
        assert pw_cell is not None, "PW 10:2 cell should have data"
        assert 'carry' in pw_cell
        assert 'max' in pw_cell
        assert pw_cell['max'] >= pw_cell['carry']


# ═══════════════════════════════════════════════════════════════════════
# Feature 2 + 3 combined: Verify old existing tests still make sense
# ═══════════════════════════════════════════════════════════════════════

class TestCombinedSwingAndPW:
    """Cross-feature: PW + new swing sizes work together."""

    def test_pw_with_new_swing_sizes(self, routed_app, ctx):
        """PW data with new swing size labels produces correct matrix."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='combined.csv')
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '3/3', [115, 118, 120])
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '2/3', [95, 98, 100])
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '1/3', [70, 72, 75])
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '10:2', [105, 108, 110])

        result = build_wedge_matrix(session_id=sid, percentile=75)
        matrix = result.get('matrix', {})

        # PW should have data in all seeded swing sizes
        assert matrix.get('3/3', {}).get('PW') is not None
        assert matrix.get('2/3', {}).get('PW') is not None
        assert matrix.get('1/3', {}).get('PW') is not None
        assert matrix.get('10:2', {}).get('PW') is not None

        # Clock swing should have carry AND max
        pw_clock = matrix['10:2']['PW']
        assert 'carry' in pw_clock
        assert 'max' in pw_clock

    def test_full_matrix_shape(self, routed_app, ctx):
        """Full wedge matrix has correct clubs and swing sizes."""
        from services.wedge_matrix import build_wedge_matrix

        sid = _create_session(data_type='wedge', filename='shape.csv')
        _seed_wedge_shots(sid, 'P-Wedge', 'PW', '3/3', [115, 118])
        _seed_wedge_shots(sid, 'G-Wedge', 'AW', '3/3', [90, 92])

        result = build_wedge_matrix(session_id=sid, percentile=75)

        assert result['clubs'] == ['PW', 'AW', 'SW', 'LW']
        assert '4/4' not in result['swing_sizes']
        assert '3/3' in result['swing_sizes']
        assert '2/3' in result['swing_sizes']
        assert '1/3' in result['swing_sizes']
