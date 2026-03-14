"""Tests for services.loft_analysis — dynamic loft vs standard loft assessment.

Rules:
  - Good shot: dynamic_loft ≤ standard_loft (compression)
  - Bad shot:  dynamic_loft > standard_loft (scooping/flipping)
"""
import pytest
from tests.conftest import _make_shot


class TestDynamicLoftAssessment:

    def test_good_shot_dynamic_loft_le_standard(self, app, seeded_db):
        """Dynamic loft ≤ standard loft → good shot (proper compression)."""
        from services.loft_analysis import assess_loft
        # Standard loft for 7i = 31.0
        result = assess_loft(dynamic_loft=28.0, club_short='7i')
        assert result['is_good'] is True

    def test_good_shot_dynamic_loft_equal_standard(self, app, seeded_db):
        """Dynamic loft == standard loft → good shot (boundary)."""
        from services.loft_analysis import assess_loft
        result = assess_loft(dynamic_loft=31.0, club_short='7i')
        assert result['is_good'] is True

    def test_bad_shot_dynamic_loft_gt_standard(self, app, seeded_db):
        """Dynamic loft > standard loft → bad shot (scooping)."""
        from services.loft_analysis import assess_loft
        result = assess_loft(dynamic_loft=35.0, club_short='7i')
        assert result['is_good'] is False

    def test_loft_difference_reported(self, app, seeded_db):
        """Assessment should report the difference from standard."""
        from services.loft_analysis import assess_loft
        result = assess_loft(dynamic_loft=28.0, club_short='7i')
        # Difference: 28.0 - 31.0 = -3.0 (negative = good, under standard)
        assert result['difference'] == pytest.approx(-3.0)

    def test_bad_shot_positive_difference(self, app, seeded_db):
        """Bad shot has positive difference from standard."""
        from services.loft_analysis import assess_loft
        result = assess_loft(dynamic_loft=35.0, club_short='7i')
        assert result['difference'] == pytest.approx(4.0)


class TestPerClubGoodPercentage:

    def test_per_club_good_percentage(self, app, db, loft_analysis_shots,
                                      sample_session, seeded_db):
        """With dynamic lofts [28,30,31,33,35] and 7i standard=31:
        Good shots: 28, 30, 31 (3 out of 5 = 60%).
        """
        from services.loft_analysis import club_loft_summary

        with app.app_context():
            summary = club_loft_summary(sample_session.id, '7i')
            assert summary['total_shots'] == 5
            assert summary['good_shots'] == 3
            assert summary['good_pct'] == pytest.approx(60.0)

    def test_all_good_shots(self, app, db, sample_session, seeded_db):
        """All shots with dynamic_loft ≤ standard → 100% good."""
        from services.loft_analysis import club_loft_summary

        with app.app_context():
            for i, dl in enumerate([20.0, 25.0, 31.0]):
                db.session.add(_make_shot(
                    sample_session.id, '7 Iron', '7i', 155.0, 165.0,
                    dynamic_loft=dl, club_index=i))
            db.session.commit()

            summary = club_loft_summary(sample_session.id, '7i')
            assert summary['good_pct'] == pytest.approx(100.0)

    def test_no_good_shots(self, app, db, sample_session, seeded_db):
        """All shots with dynamic_loft > standard → 0% good."""
        from services.loft_analysis import club_loft_summary

        with app.app_context():
            for i, dl in enumerate([35.0, 38.0, 40.0]):
                db.session.add(_make_shot(
                    sample_session.id, '8 Iron', '8i', 130.0, 140.0,
                    dynamic_loft=dl, club_index=i))
            db.session.commit()

            summary = club_loft_summary(sample_session.id, '8i')
            assert summary['good_pct'] == pytest.approx(0.0)


class TestLoftAnalysisWithExcludedShots:

    def test_loft_analysis_with_excluded_shots(self, app, db, sample_session,
                                                seeded_db):
        """Excluded shots should NOT count toward loft analysis."""
        from services.loft_analysis import club_loft_summary

        with app.app_context():
            # 2 good shots
            db.session.add(_make_shot(
                sample_session.id, '7 Iron', '7i', 155.0, 165.0,
                dynamic_loft=28.0, club_index=0))
            db.session.add(_make_shot(
                sample_session.id, '7 Iron', '7i', 160.0, 170.0,
                dynamic_loft=30.0, club_index=1))
            # 1 bad shot (excluded)
            db.session.add(_make_shot(
                sample_session.id, '7 Iron', '7i', 100.0, 110.0,
                dynamic_loft=45.0, excluded=True, club_index=2))
            db.session.commit()

            summary = club_loft_summary(sample_session.id, '7i')
            # Only 2 non-excluded shots, both good → 100%
            assert summary['total_shots'] == 2
            assert summary['good_pct'] == pytest.approx(100.0)


class TestLoftAnalysisEdgeCases:

    def test_no_shots_for_club(self, app, db, sample_session, seeded_db):
        """Club with zero shots — should return empty/zero summary."""
        from services.loft_analysis import club_loft_summary

        with app.app_context():
            summary = club_loft_summary(sample_session.id, 'LW')
            assert summary['total_shots'] == 0
            assert summary['good_pct'] == pytest.approx(0.0) or \
                   summary['good_pct'] is None

    def test_shot_with_zero_dynamic_loft(self, app, db, sample_session,
                                          seeded_db):
        """Some real CSV rows have dynamic_loft=0.0 — handle gracefully.
        Real data shows 0.0 dynamic loft for some G-Wedge/S-Wedge shots.
        """
        from services.loft_analysis import assess_loft
        result = assess_loft(dynamic_loft=0.0, club_short='AW')
        # 0.0 ≤ 50.0 (standard for AW) → good shot
        assert result['is_good'] is True

    def test_shot_with_none_dynamic_loft(self, app, seeded_db):
        """If dynamic_loft is None/missing, should not crash."""
        from services.loft_analysis import assess_loft
        try:
            result = assess_loft(dynamic_loft=None, club_short='7i')
            # Should return unknown/None or handle gracefully
            assert result is None or result.get('is_good') is None
        except (TypeError, ValueError):
            pass  # acceptable — None input may raise
