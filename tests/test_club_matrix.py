"""Tests for services.club_matrix — club matrix generation, ordering, rounding."""
import pytest
import numpy as np
from tests.conftest import _make_shot


# ── Standard loft ordering (Driver first → LW last) ───────────────────
CLUB_ORDER = ['1W', '3W', '2H', '3H', '4i', '5i', '6i', '7i', '8i', '9i',
              'PW', 'AW', 'SW', 'LW']


class TestClubMatrixBasic:
    """Club matrix columns: Club | Carry(P75) | Total(P75) | Max(total)."""

    def test_club_matrix_basic(self, app, db, mixed_club_shots, sample_session):
        """Verify carry/total/max computed correctly for each club."""
        from services.club_matrix import generate_club_matrix

        with app.app_context():
            matrix = generate_club_matrix(session_id=sample_session.id, percentile=75)

        # 7i carries=[148,153,158,163,168], totals=[158,163,168,173,178]
        row_7i = next(r for r in matrix if r['club_short'] == '7i')
        expected_carry = float(np.percentile([148, 153, 158, 163, 168], 75))
        expected_total = float(np.percentile([158, 163, 168, 173, 178], 75))
        assert row_7i['carry'] == round(expected_carry)
        assert row_7i['total'] == round(expected_total)
        assert row_7i['max'] == 178  # max total

    def test_club_matrix_driver_values(self, app, db, mixed_club_shots, sample_session):
        """Driver carry/total/max check."""
        from services.club_matrix import generate_club_matrix

        with app.app_context():
            matrix = generate_club_matrix(session_id=sample_session.id, percentile=75)

        row_1w = next(r for r in matrix if r['club_short'] == '1W')
        expected_carry = float(np.percentile([215, 220, 225, 230, 235], 75))
        assert row_1w['carry'] == round(expected_carry)
        assert row_1w['max'] == 260


class TestClubMatrixOrdering:

    def test_club_matrix_ordering(self, app, db, mixed_club_shots, sample_session):
        """Matrix rows must be sorted by standard loft: 1W, ..., LW."""
        from services.club_matrix import generate_club_matrix

        with app.app_context():
            matrix = generate_club_matrix(session_id=sample_session.id, percentile=75)

        clubs_in_matrix = [r['club_short'] for r in matrix]
        # Filter CLUB_ORDER to only clubs that appear in the data
        expected_order = [c for c in CLUB_ORDER if c in clubs_in_matrix]
        assert clubs_in_matrix == expected_order


class TestClubMatrixScope:

    def test_club_matrix_single_session_scope(self, app, db, sample_session):
        """Single session scope only includes shots from that session."""
        from services.club_matrix import generate_club_matrix
        from models.database import Session, Shot

        with app.app_context():
            # Create two sessions
            session2 = Session(filename='s2.csv', session_date=None,
                               location='Range', data_type='club')
            db.session.add(session2)
            db.session.commit()

            # Add shots to session 1
            for i, carry in enumerate([150, 160, 170]):
                db.session.add(_make_shot(
                    sample_session.id, '7 Iron', '7i', float(carry),
                    float(carry + 10), club_index=i))
            # Add shots to session 2
            for i, carry in enumerate([200, 210, 220]):
                db.session.add(_make_shot(
                    session2.id, '7 Iron', '7i', float(carry),
                    float(carry + 10), club_index=i))
            db.session.commit()

            # Single session scope — should only see session 1 data
            matrix = generate_club_matrix(session_id=sample_session.id, percentile=75)
            row_7i = next(r for r in matrix if r['club_short'] == '7i')
            # Max total from session 1 should be 180, not 230
            assert row_7i['max'] <= 180

    def test_club_matrix_all_sessions_scope(self, app, db, sample_session):
        """All sessions scope aggregates across sessions."""
        from services.club_matrix import generate_club_matrix
        from models.database import Session

        with app.app_context():
            session2 = Session(filename='s2.csv', session_date=None,
                               location='Range', data_type='club')
            db.session.add(session2)
            db.session.commit()

            for i, carry in enumerate([150, 160, 170]):
                db.session.add(_make_shot(
                    sample_session.id, '7 Iron', '7i', float(carry),
                    float(carry + 10), club_index=i))
            for i, carry in enumerate([200, 210, 220]):
                db.session.add(_make_shot(
                    session2.id, '7 Iron', '7i', float(carry),
                    float(carry + 10), club_index=i))
            db.session.commit()

            # All sessions — session_id=None means aggregate all
            matrix = generate_club_matrix(session_id=None, percentile=75)
            row_7i = next(r for r in matrix if r['club_short'] == '7i')
            # Max total should be 230 (from session 2)
            assert row_7i['max'] == 230


class TestClubMatrixExclusions:

    def test_club_matrix_excludes_excluded_shots(self, app, db, sample_session):
        """Excluded shots must not affect percentile or max calculations."""
        from services.club_matrix import generate_club_matrix

        with app.app_context():
            # 3 normal shots
            for i, carry in enumerate([150, 160, 170]):
                db.session.add(_make_shot(
                    sample_session.id, '7 Iron', '7i', float(carry),
                    float(carry + 10), club_index=i))
            # 1 excluded shot with carry=300 — must not affect max
            db.session.add(_make_shot(
                sample_session.id, '7 Iron', '7i', 300.0, 350.0,
                excluded=True, club_index=3))
            db.session.commit()

            matrix = generate_club_matrix(session_id=sample_session.id, percentile=75)
            row_7i = next(r for r in matrix if r['club_short'] == '7i')
            assert row_7i['max'] == 180  # not 350


class TestClubMatrixRounding:

    def test_club_matrix_rounding(self, app, db, sample_session):
        """All matrix values must be rounded to whole yards."""
        from services.club_matrix import generate_club_matrix

        with app.app_context():
            # Carries that produce fractional percentiles
            for i, carry in enumerate([151.3, 158.7, 162.2, 169.9, 174.1]):
                db.session.add(_make_shot(
                    sample_session.id, '8 Iron', '8i', carry, carry + 8,
                    club_index=i))
            db.session.commit()

            matrix = generate_club_matrix(session_id=sample_session.id, percentile=75)
            row_8i = next(r for r in matrix if r['club_short'] == '8i')
            assert row_8i['carry'] == int(row_8i['carry'])
            assert row_8i['total'] == int(row_8i['total'])
            assert row_8i['max'] == int(row_8i['max'])


class TestClubMatrixEmptyClub:

    def test_club_matrix_empty_club(self, app, db, sample_session, seeded_db):
        """Club with zero shots should not appear in matrix (or show empty)."""
        from services.club_matrix import generate_club_matrix

        with app.app_context():
            # Only add 7i shots — no other clubs
            for i in range(3):
                db.session.add(_make_shot(
                    sample_session.id, '7 Iron', '7i', 155.0, 165.0,
                    club_index=i))
            db.session.commit()

            matrix = generate_club_matrix(session_id=sample_session.id, percentile=75)
            clubs_in_matrix = [r['club_short'] for r in matrix]
            # Driver should NOT be in the matrix (no shots)
            assert '1W' not in clubs_in_matrix
            assert '7i' in clubs_in_matrix


class TestClubMatrixConfigurablePercentile:

    def test_club_matrix_configurable_percentile(self, app, db, sample_session):
        """Different percentiles produce different carry values."""
        from services.club_matrix import generate_club_matrix

        with app.app_context():
            for i, carry in enumerate([150, 160, 170, 180, 190]):
                db.session.add(_make_shot(
                    sample_session.id, '6 Iron', '6i', float(carry),
                    float(carry + 10), club_index=i))
            db.session.commit()

            matrix_p50 = generate_club_matrix(
                session_id=sample_session.id, percentile=50)
            matrix_p90 = generate_club_matrix(
                session_id=sample_session.id, percentile=90)

            carry_p50 = next(r for r in matrix_p50
                             if r['club_short'] == '6i')['carry']
            carry_p90 = next(r for r in matrix_p90
                             if r['club_short'] == '6i')['carry']
            # P90 must be greater than or equal to P50
            assert carry_p90 >= carry_p50
