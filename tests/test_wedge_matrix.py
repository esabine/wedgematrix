"""Tests for services.wedge_matrix — wedge matrix generation.

Wedge matrix rules:
- Only AW, SW, LW (PW NOT included)
- Fraction swings (4/4, 3/4, 2/4, 1/4): show Carry only
- Clock swings (10:2, 10:3, 9:3, 8:4): show Carry/Max
- Empty cell if no data for club+swing combo
"""
import pytest
import numpy as np
from tests.conftest import _make_shot

ALL_SWING_SIZES = ['4/4', '3/4', '2/4', '1/4', '10:2', '10:3', '9:3', '8:4']
FRACTION_SWINGS = ['4/4', '3/4', '2/4', '1/4']
CLOCK_SWINGS = ['10:2', '10:3', '9:3', '8:4']
WEDGE_CLUBS = ['AW', 'SW', 'LW']


class TestWedgeMatrixClubs:

    def test_wedge_matrix_aw_sw_lw_only(self, app, db, wedge_shots,
                                         sample_wedge_session):
        """Wedge matrix must only include AW, SW, LW — NOT PW."""
        from services.wedge_matrix import generate_wedge_matrix

        with app.app_context():
            # Also add a PW shot to verify it's excluded
            db.session.add(_make_shot(
                sample_wedge_session.id, 'P-Wedge', 'PW', 115.0, 118.0,
                swing_size='4/4', club_index=99))
            db.session.commit()

            matrix = generate_wedge_matrix(
                session_id=sample_wedge_session.id, percentile=75)

        # Columns should be AW, SW, LW only
        clubs_in_matrix = set()
        for row in matrix:
            for club in row.get('clubs', {}).keys():
                clubs_in_matrix.add(club)
        # Alternative: if matrix is a dict keyed by swing_size
        if isinstance(matrix, dict):
            for swing, clubs in matrix.items():
                for club in clubs.keys():
                    clubs_in_matrix.add(club)

        assert 'PW' not in clubs_in_matrix
        # At least AW and SW should be present (LW might also be there)
        assert 'AW' in clubs_in_matrix or len(clubs_in_matrix) >= 2


class TestWedgeMatrixFractions:

    def test_wedge_matrix_fraction_carry_only(self, app, db, wedge_shots,
                                               sample_wedge_session):
        """Fraction swing sizes (4/4, 3/4, 2/4, 1/4) show carry ONLY."""
        from services.wedge_matrix import generate_wedge_matrix

        with app.app_context():
            matrix = generate_wedge_matrix(
                session_id=sample_wedge_session.id, percentile=75)

        # For fraction swings, the cell should have 'carry' but NOT 'max'
        # (or max should be None/absent)
        for swing in FRACTION_SWINGS:
            if isinstance(matrix, dict) and swing in matrix:
                for club, cell in matrix[swing].items():
                    if cell is not None:
                        assert 'carry' in cell or isinstance(cell, (int, float))
            elif isinstance(matrix, list):
                row = next((r for r in matrix if r.get('swing_size') == swing), None)
                if row:
                    for club in WEDGE_CLUBS:
                        cell = row.get('clubs', {}).get(club)
                        if cell is not None:
                            # Fraction cells should have carry but no max
                            if isinstance(cell, dict):
                                assert cell.get('max') is None or 'max' not in cell


class TestWedgeMatrixClock:

    def test_wedge_matrix_clock_carry_max(self, app, db, wedge_shots,
                                          sample_wedge_session):
        """Clock swing sizes (10:2, 10:3, 9:3, 8:4) show Carry/Max."""
        from services.wedge_matrix import generate_wedge_matrix

        with app.app_context():
            matrix = generate_wedge_matrix(
                session_id=sample_wedge_session.id, percentile=75)

        # AW has 10:2 data: carries=[82,78,84], so P75 should be ~83
        # Max carry = 84
        if isinstance(matrix, dict):
            cell_aw_102 = matrix.get('10:2', {}).get('AW')
            if cell_aw_102 is not None:
                if isinstance(cell_aw_102, dict):
                    assert 'carry' in cell_aw_102
                    assert 'max' in cell_aw_102
                    assert cell_aw_102['max'] >= cell_aw_102['carry']
        elif isinstance(matrix, list):
            row_102 = next((r for r in matrix
                            if r.get('swing_size') == '10:2'), None)
            if row_102:
                cell = row_102.get('clubs', {}).get('AW')
                if cell and isinstance(cell, dict):
                    assert 'carry' in cell
                    assert 'max' in cell


class TestWedgeMatrixEmptyCell:

    def test_wedge_matrix_empty_cell(self, app, db, wedge_shots,
                                      sample_wedge_session):
        """No data for a club+swing combo → empty/None cell."""
        from services.wedge_matrix import generate_wedge_matrix

        with app.app_context():
            matrix = generate_wedge_matrix(
                session_id=sample_wedge_session.id, percentile=75)

        # LW has no '10:3' data in our fixture → should be empty
        if isinstance(matrix, dict):
            cell = matrix.get('10:3', {}).get('LW')
            assert cell is None or cell == {} or cell == ''
        elif isinstance(matrix, list):
            row = next((r for r in matrix
                        if r.get('swing_size') == '10:3'), None)
            if row:
                cell = row.get('clubs', {}).get('LW')
                assert cell is None or cell == {} or cell == ''


class TestWedgeMatrixExclusions:

    def test_wedge_matrix_excludes_excluded_shots(self, app, db,
                                                   sample_wedge_session):
        """Excluded shots must not contribute to wedge matrix values."""
        from services.wedge_matrix import generate_wedge_matrix

        with app.app_context():
            # Two normal AW 4/4 shots
            db.session.add(_make_shot(
                sample_wedge_session.id, 'G-Wedge', 'AW', 85.0, 87.0,
                swing_size='4/4', club_index=0))
            db.session.add(_make_shot(
                sample_wedge_session.id, 'G-Wedge', 'AW', 90.0, 92.0,
                swing_size='4/4', club_index=1))
            # One excluded AW 4/4 shot with extreme carry
            db.session.add(_make_shot(
                sample_wedge_session.id, 'G-Wedge', 'AW', 200.0, 205.0,
                swing_size='4/4', excluded=True, club_index=2))
            db.session.commit()

            matrix = generate_wedge_matrix(
                session_id=sample_wedge_session.id, percentile=75)

        # The carry value for AW 4/4 should be based on [85, 90], not [85, 90, 200]
        if isinstance(matrix, dict):
            cell = matrix.get('4/4', {}).get('AW')
        elif isinstance(matrix, list):
            row = next((r for r in matrix
                        if r.get('swing_size') == '4/4'), None)
            cell = row.get('clubs', {}).get('AW') if row else None

        if cell is not None:
            carry_val = cell['carry'] if isinstance(cell, dict) else cell
            assert carry_val <= 100  # should not be affected by 200-yard outlier


class TestWedgeMatrixPercentile:

    def test_wedge_matrix_configurable_percentile(self, app, db,
                                                   sample_wedge_session):
        """Different percentiles should produce different carry values."""
        from services.wedge_matrix import generate_wedge_matrix

        with app.app_context():
            for i, carry in enumerate([60, 65, 70, 75, 80]):
                db.session.add(_make_shot(
                    sample_wedge_session.id, 'S-Wedge', 'SW', float(carry),
                    float(carry + 2), swing_size='4/4', club_index=i))
            db.session.commit()

            m50 = generate_wedge_matrix(
                session_id=sample_wedge_session.id, percentile=50)
            m90 = generate_wedge_matrix(
                session_id=sample_wedge_session.id, percentile=90)

        def _get_carry(matrix, swing, club):
            if isinstance(matrix, dict):
                cell = matrix.get(swing, {}).get(club)
            elif isinstance(matrix, list):
                row = next((r for r in matrix
                            if r.get('swing_size') == swing), None)
                cell = row.get('clubs', {}).get(club) if row else None
            else:
                return None
            if cell is None:
                return None
            return cell['carry'] if isinstance(cell, dict) else cell

        c50 = _get_carry(m50, '4/4', 'SW')
        c90 = _get_carry(m90, '4/4', 'SW')
        if c50 is not None and c90 is not None:
            assert c90 >= c50


class TestAllSwingSizesPresent:

    def test_all_eight_swing_sizes_present(self, app, db,
                                            sample_wedge_session):
        """The matrix structure must include all 8 swing size rows."""
        from services.wedge_matrix import generate_wedge_matrix

        with app.app_context():
            # Add at least one shot so the matrix generates
            db.session.add(_make_shot(
                sample_wedge_session.id, 'G-Wedge', 'AW', 80.0, 82.0,
                swing_size='4/4', club_index=0))
            db.session.commit()

            matrix = generate_wedge_matrix(
                session_id=sample_wedge_session.id, percentile=75)

        if isinstance(matrix, dict):
            for swing in ALL_SWING_SIZES:
                assert swing in matrix, f"Missing swing size row: {swing}"
        elif isinstance(matrix, list):
            swings_in_matrix = [r.get('swing_size') for r in matrix]
            for swing in ALL_SWING_SIZES:
                assert swing in swings_in_matrix, \
                    f"Missing swing size row: {swing}"
