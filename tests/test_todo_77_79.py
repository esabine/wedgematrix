"""Tests for TODO 77-79: Carry Distance Chart, Club Ordering, Swing Path Parsing.

Written by Hockney — the tester who asks "what if the data is wrong?"
before anyone else does.

TODO 77: Carry Distance Concentric Chart (frontend) — regression test that
    the carry distribution API still returns per-club averages with club names.
TODO 78: Club Ordering — CLUB_ORDER constant exists, clubs sorted correctly,
    unknown clubs appended at end, missing clubs skipped, empty data safe.
TODO 79: Swing Path L/R Parsing — "L5.2" → -5.2, "R3.1" → +3.1, edge cases.
"""
import pytest
import numpy as np
from datetime import date
from flask import Flask

from models.database import db as _db, Session, Shot, ClubLoft, init_db
from models.seed import seed_club_lofts
from app import register_routes
from services.csv_parser import parse_direction
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


def _seed_multi_club_shots(app, session_id, clubs_data):
    """Seed shots for multiple clubs. clubs_data: {club_short: [(carry, total), ...]}"""
    club_name_map = {
        '1W': 'Driver', '3W': '3 Wood', '2H': '2 Hybrid', '3H': '3 Hybrid',
        '4i': '4 Iron', '5i': '5 Iron', '6i': '6 Iron', '7i': '7 Iron',
        '8i': '8 Iron', '9i': '9 Iron', 'PW': 'P-Wedge', 'AW': 'G-Wedge',
        'SW': 'S-Wedge', 'LW': 'L-Wedge',
    }
    with app.app_context():
        for club_short, values in clubs_data.items():
            club_name = club_name_map.get(club_short, club_short)
            for i, (carry, total) in enumerate(values):
                s = _make_shot(session_id, club_name, club_short, carry, total,
                               club_index=i, spin_rate=5000 + i * 100,
                               launch_angle=12.0 + i * 0.5)
                _db.session.add(s)
        _db.session.commit()


# ══════════════════════════════════════════════════════════════════════════
# TODO 77 — Carry Distance API Regression
# ══════════════════════════════════════════════════════════════════════════

class TestCarryDistanceAPI:
    """Verify carry distance endpoint returns per-club data with correct shape."""

    def test_carry_endpoint_returns_per_club_averages(self, routed_app):
        """Carry distribution returns box-plot stats keyed by club short name."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()
            sid = sess.id

            _seed_multi_club_shots(routed_app, sid, {
                '7i': [(155, 165), (160, 170), (150, 160), (158, 168), (162, 172)],
                'PW': [(110, 115), (115, 120), (108, 113), (112, 117), (118, 123)],
            })

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/carry-distribution?session_id={sid}')
            assert resp.status_code == 200
            data = resp.get_json()

            # Both clubs present with correct keys
            assert '7i' in data
            assert 'PW' in data
            for club in ('7i', 'PW'):
                entry = data[club]
                assert 'min' in entry
                assert 'q1' in entry
                assert 'median' in entry
                assert 'q3' in entry
                assert 'max' in entry
                assert 'count' in entry
                assert entry['count'] == 5

    def test_carry_endpoint_club_names_are_short_codes(self, routed_app):
        """Keys must be short codes (7i, PW) not long names (7 Iron, P-Wedge)."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            _seed_multi_club_shots(routed_app, sess.id, clubs_data={
                '1W': [(230, 250), (225, 245), (235, 255)],
            })

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/carry-distribution?session_id={sess.id}')
            data = resp.get_json()
            assert '1W' in data
            assert 'Driver' not in data

    def test_carry_endpoint_empty_session_returns_empty(self, routed_app):
        """Empty session → empty JSON, no crash."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/carry-distribution?session_id={sess.id}')
            assert resp.status_code == 200
            data = resp.get_json()
            assert data == {} or len(data) == 0

    def test_carry_endpoint_gapping_present(self, routed_app):
        """Gapping data (gap field) included for adjacent clubs."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            _seed_multi_club_shots(routed_app, sess.id, clubs_data={
                '7i': [(155, 165), (160, 170), (150, 160), (158, 168), (162, 172)],
                '8i': [(140, 150), (145, 155), (138, 148), (142, 152), (148, 158)],
            })

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/carry-distribution?session_id={sess.id}')
            data = resp.get_json()
            # 7i is longer than 8i → 7i should have a gap value
            assert data['7i']['gap'] is not None
            assert data['7i']['gap'] > 0  # 7i carries more than 8i


# ══════════════════════════════════════════════════════════════════════════
# TODO 78 — Club Ordering
# ══════════════════════════════════════════════════════════════════════════

class TestClubOrder:
    """CLUB_ORDER constant and its application across endpoints."""

    def test_club_order_constant_exists(self):
        """CLUB_ORDER is importable and is a list."""
        assert isinstance(CLUB_ORDER, list)
        assert len(CLUB_ORDER) > 0

    def test_club_order_starts_with_driver_ends_with_lw(self):
        """Order goes from longest club (Driver); last bare wedge is LW."""
        assert CLUB_ORDER[0] == '1W'
        # Bare wedge names are still present; compound labels follow
        assert 'LW' in CLUB_ORDER
        bare_lw_idx = CLUB_ORDER.index('LW')
        assert bare_lw_idx > CLUB_ORDER.index('PW')

    def test_club_order_has_14_standard_clubs(self):
        """Standard bag clubs (bare names) are all present."""
        standard_14 = ['1W', '3W', '2H', '3H', '4i', '5i', '6i', '7i', '8i', '9i', 'PW', 'AW', 'SW', 'LW']
        for club in standard_14:
            assert club in CLUB_ORDER, f'{club} missing from CLUB_ORDER'

    def test_club_order_woods_before_irons(self):
        """Woods appear before irons in the ordering."""
        wood_indices = [CLUB_ORDER.index(c) for c in ['1W', '3W'] if c in CLUB_ORDER]
        iron_indices = [CLUB_ORDER.index(c) for c in ['4i', '5i', '6i', '7i', '8i', '9i'] if c in CLUB_ORDER]
        assert max(wood_indices) < min(iron_indices)

    def test_club_order_irons_before_wedges(self):
        """Irons appear before wedges."""
        iron_indices = [CLUB_ORDER.index(c) for c in ['8i', '9i'] if c in CLUB_ORDER]
        wedge_indices = [CLUB_ORDER.index(c) for c in ['PW', 'AW', 'SW', 'LW'] if c in CLUB_ORDER]
        assert max(iron_indices) < min(wedge_indices)

    def test_carry_distribution_sorted_by_club_order(self, routed_app):
        """Carry distribution response keys follow CLUB_ORDER."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            # Seed in reverse order to prove sorting
            _seed_multi_club_shots(routed_app, sess.id, clubs_data={
                'PW': [(110, 115), (115, 120), (112, 117)],
                '7i': [(155, 165), (160, 170), (158, 168)],
                '1W': [(230, 250), (225, 245), (235, 255)],
            })

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/carry-distribution?session_id={sess.id}')
            data = resp.get_json()
            keys = list(data.keys())
            # Must be in CLUB_ORDER: 1W before 7i before PW
            assert keys.index('1W') < keys.index('7i')
            assert keys.index('7i') < keys.index('PW')

    def test_clubs_not_in_order_appended_at_end(self, routed_app):
        """Clubs not in CLUB_ORDER appear after all ordered clubs."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            # Seed a recognized club and a bogus one
            _seed_multi_club_shots(routed_app, sess.id, clubs_data={
                '7i': [(155, 165), (160, 170), (158, 168)],
            })
            # Add a shot with an unknown club short name
            s = _make_shot(sess.id, 'Weird Club', 'WC', 100.0, 110.0)
            _db.session.add(s)
            _db.session.commit()

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/carry-distribution?session_id={sess.id}')
            data = resp.get_json()
            keys = list(data.keys())
            # 7i is in CLUB_ORDER; WC is not → WC must appear after 7i
            assert '7i' in keys
            assert 'WC' in keys
            assert keys.index('7i') < keys.index('WC')

    def test_missing_clubs_skipped_gracefully(self, routed_app):
        """If data has only 2 of 14 clubs, the response only has those 2."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            _seed_multi_club_shots(routed_app, sess.id, clubs_data={
                'PW': [(110, 115), (115, 120), (112, 117)],
                'SW': [(90, 95), (95, 100), (88, 93)],
            })

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/carry-distribution?session_id={sess.id}')
            data = resp.get_json()
            assert len(data) == 2
            assert 'PW' in data
            assert 'SW' in data
            # No phantom clubs
            assert '1W' not in data

    def test_club_comparison_respects_order(self, routed_app):
        """Club comparison endpoint returns clubs sorted by CLUB_ORDER."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            _seed_multi_club_shots(routed_app, sess.id, clubs_data={
                '9i': [(135, 145), (140, 150), (138, 148)],
                '5i': [(170, 180), (175, 185), (173, 183)],
                '1W': [(230, 250), (225, 245), (235, 255)],
            })

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/club-comparison?session_id={sess.id}')
            data = resp.get_json()
            # Response is an array of entries with 'club' key
            club_labels = [e['club'] for e in data]
            idx_1w = club_labels.index('1W')
            idx_5i = club_labels.index('5i')
            idx_9i = club_labels.index('9i')
            assert idx_1w < idx_5i < idx_9i

    def test_launch_spin_stability_respects_order(self, routed_app):
        """Launch-spin stability endpoint returns clubs in CLUB_ORDER."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            _seed_multi_club_shots(routed_app, sess.id, clubs_data={
                'PW': [(110, 115), (115, 120), (112, 117), (108, 113), (118, 123)],
                '7i': [(155, 165), (160, 170), (150, 160), (158, 168), (162, 172)],
            })

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/launch-spin-stability?session_id={sess.id}')
            data = resp.get_json()
            club_keys = list(data['clubs'].keys())
            # 7i must come before PW (or PW-full sub-swing) in CLUB_ORDER
            idx_7i = next(i for i, k in enumerate(club_keys) if k == '7i')
            idx_pw = next(i for i, k in enumerate(club_keys) if k.startswith('PW'))
            assert idx_7i < idx_pw

    def test_empty_data_no_crash_carry(self, routed_app):
        """Empty DB → carry endpoint returns empty dict, no 500."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/carry-distribution?session_id={sess.id}')
            assert resp.status_code == 200

    def test_empty_data_no_crash_comparison(self, routed_app):
        """Empty DB → club-comparison returns empty list, no 500."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='club')
            _db.session.add(sess)
            _db.session.commit()

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/club-comparison?session_id={sess.id}')
            assert resp.status_code == 200

    def test_only_wedge_sub_swings_still_ordered(self, routed_app):
        """Wedge-only data with swing sizes doesn't crash ordering logic."""
        with routed_app.app_context():
            sess = Session(filename='test.csv', session_date=date(2026, 3, 12),
                           location='Range', data_type='wedge')
            _db.session.add(sess)
            _db.session.commit()

            # Seed wedge shots with swing sizes
            wedge_data = [
                ('P-Wedge', 'PW', '3/3', 115, 120),
                ('P-Wedge', 'PW', '3/3', 112, 117),
                ('P-Wedge', 'PW', '2/3', 90, 95),
                ('P-Wedge', 'PW', '2/3', 88, 93),
                ('G-Wedge', 'AW', '3/3', 100, 105),
                ('G-Wedge', 'AW', '3/3', 98, 103),
                ('G-Wedge', 'AW', '2/3', 78, 83),
                ('G-Wedge', 'AW', '2/3', 76, 81),
            ]
            for i, (club, short, swing, carry, total) in enumerate(wedge_data):
                s = _make_shot(sess.id, club, short, carry, total,
                               swing_size=swing, club_index=i)
                _db.session.add(s)
            _db.session.commit()

            client = routed_app.test_client()
            resp = client.get(f'/api/analytics/club-comparison?session_id={sess.id}')
            assert resp.status_code == 200
            data = resp.get_json()
            # Within each swing type group, PW before AW (canonical order)
            club_labels = [e['club'] for e in data]
            # Both PW and AW have 3/3 and 2/3; within each group PW should precede AW
            for swing in ['3/3', '2/3']:
                pw_key = f'PW-{swing}'
                aw_key = f'AW-{swing}'
                if pw_key in club_labels and aw_key in club_labels:
                    assert club_labels.index(pw_key) < club_labels.index(aw_key)


# ══════════════════════════════════════════════════════════════════════════
# TODO 79 — Swing Path L/R Parsing
# ══════════════════════════════════════════════════════════════════════════

class TestSwingPathParsing:
    """parse_direction() applied to Club Path and Face Angle fields."""

    def test_L_prefix_parses_negative(self):
        """'L5.2' → -5.2 (out-to-in swing path)."""
        assert parse_direction('L5.2') == pytest.approx(-5.2)

    def test_R_prefix_parses_positive(self):
        """'R3.1' → +3.1 (in-to-out swing path)."""
        assert parse_direction('R3.1') == pytest.approx(3.1)

    def test_zero_string_parses_to_zero(self):
        """'0' → 0.0 (straight path)."""
        assert parse_direction('0') == pytest.approx(0.0)

    def test_zero_point_zero_parses_to_zero(self):
        """'0.0' → 0.0 (straight path)."""
        assert parse_direction('0.0') == pytest.approx(0.0)

    def test_plain_number_no_prefix(self):
        """'5.2' without L/R prefix → 5.2 (positive)."""
        assert parse_direction('5.2') == pytest.approx(5.2)

    def test_empty_string_returns_none(self):
        """'' → None, no crash."""
        assert parse_direction('') is None

    def test_none_returns_none(self):
        """None → None, no crash."""
        assert parse_direction(None) is None

    def test_nan_string_returns_none(self):
        """'NaN' → None, no crash."""
        assert parse_direction('NaN') is None

    def test_nan_lowercase_returns_none(self):
        """'nan' → None (case insensitive)."""
        assert parse_direction('nan') is None

    def test_L0_returns_zero(self):
        """'L0' → 0 or -0.0 (both acceptable, must not crash)."""
        result = parse_direction('L0')
        assert result == pytest.approx(0.0) or result == pytest.approx(-0.0)

    def test_R0_returns_zero(self):
        """'R0' → 0.0."""
        assert parse_direction('R0') == pytest.approx(0.0)

    def test_very_large_L_value(self):
        """'L99.9' → -99.9 (extreme out-to-in)."""
        assert parse_direction('L99.9') == pytest.approx(-99.9)

    def test_very_large_R_value(self):
        """'R99.9' → +99.9 (extreme in-to-out)."""
        assert parse_direction('R99.9') == pytest.approx(99.9)

    def test_negative_number_without_prefix(self):
        """'-2.5' → -2.5 (already signed)."""
        assert parse_direction('-2.5') == pytest.approx(-2.5)

    def test_whitespace_stripped(self):
        """' R3.0 ' → 3.0 (whitespace tolerance)."""
        assert parse_direction(' R3.0 ') == pytest.approx(3.0)

    def test_garbage_returns_none(self):
        """'abc' → None (unparseable)."""
        assert parse_direction('abc') is None

    def test_L_only_no_number_returns_none(self):
        """'L' with no number → None."""
        assert parse_direction('L') is None

    def test_R_only_no_number_returns_none(self):
        """'R' with no number → None."""
        assert parse_direction('R') is None


class TestSwingPathInCSVParsing:
    """Verify club_path and face_angle are parsed via parse_direction in CSV flow."""

    def test_club_path_L_parsed_in_csv_row(self):
        """CSV row with Club Path 'L4.3' → club_path = -4.3."""
        from services.csv_parser import parse_shot_row
        row = {
            'Club': 'Driver (1)',
            'Ball Speed(mph)': '150',
            'Launch Direction': 'R1.0',
            'Launch Angle': '12.0',
            'Spin Rate': '2500',
            'Spin Axis': 'R5.0',
            'Back Spin': '2400',
            'Side Spin': 'R200',
            'Apex(yd)': '30',
            'Carry(yd)': '230',
            'Total(yd)': '250',
            'Offline(yd)': 'R5.0',
            'Landing Angle': '40',
            'Club Path': 'L4.3',
            'Face Angle': 'R2.1',
            'Attack Angle': '3.0',
            ' Dynamic Loft': '15.0',
        }
        result = parse_shot_row(row)
        assert result['club_path'] == pytest.approx(-4.3)

    def test_face_angle_R_parsed_in_csv_row(self):
        """CSV row with Face Angle 'R2.1' → face_angle = +2.1."""
        from services.csv_parser import parse_shot_row
        row = {
            'Club': '7 Iron (7)',
            'Ball Speed(mph)': '120',
            'Launch Direction': 'L0.5',
            'Launch Angle': '18.0',
            'Spin Rate': '6500',
            'Spin Axis': 'L8.0',
            'Back Spin': '6200',
            'Side Spin': 'L500',
            'Apex(yd)': '28',
            'Carry(yd)': '155',
            'Total(yd)': '165',
            'Offline(yd)': 'L3.0',
            'Landing Angle': '48',
            'Club Path': 'R1.5',
            'Face Angle': 'R2.1',
            'Attack Angle': '-1.0',
            ' Dynamic Loft': '24.0',
        }
        result = parse_shot_row(row)
        assert result['face_angle'] == pytest.approx(2.1)

    def test_face_angle_L_parsed_in_csv_row(self):
        """CSV row with Face Angle 'L1.8' → face_angle = -1.8."""
        from services.csv_parser import parse_shot_row
        row = {
            'Club': '7 Iron (7)',
            'Ball Speed(mph)': '120',
            'Launch Direction': 'R0.5',
            'Launch Angle': '18.0',
            'Spin Rate': '6500',
            'Spin Axis': 'R8.0',
            'Back Spin': '6200',
            'Side Spin': 'R500',
            'Apex(yd)': '28',
            'Carry(yd)': '155',
            'Total(yd)': '165',
            'Offline(yd)': 'R3.0',
            'Landing Angle': '48',
            'Club Path': '0.0',
            'Face Angle': 'L1.8',
            'Attack Angle': '-1.0',
            ' Dynamic Loft': '24.0',
        }
        result = parse_shot_row(row)
        assert result['face_angle'] == pytest.approx(-1.8)

    def test_missing_club_path_returns_none(self):
        """CSV row with missing Club Path key → club_path = None."""
        from services.csv_parser import parse_shot_row
        row = {
            'Club': 'Driver (1)',
            'Ball Speed(mph)': '150',
            'Launch Direction': 'R1.0',
            'Launch Angle': '12.0',
            'Spin Rate': '2500',
            'Spin Axis': 'R5.0',
            'Back Spin': '2400',
            'Side Spin': 'R200',
            'Apex(yd)': '30',
            'Carry(yd)': '230',
            'Total(yd)': '250',
            'Offline(yd)': 'R5.0',
            'Landing Angle': '40',
            # No Club Path or Face Angle
            'Attack Angle': '3.0',
            ' Dynamic Loft': '15.0',
        }
        result = parse_shot_row(row)
        assert result['club_path'] is None
