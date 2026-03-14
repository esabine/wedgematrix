"""Tests for services.analytics — percentile math, errant flagging, per-club stats."""
import pytest
import numpy as np


class TestPercentileCalculation:
    """Percentile computations must be exact — verified against NumPy."""

    def test_percentile_p75_calculation(self):
        """P75 of 10 evenly spaced carry values [150..195 step 5]."""
        from services.analytics import compute_percentile
        carries = [150.0, 155.0, 160.0, 165.0, 170.0,
                   175.0, 180.0, 185.0, 190.0, 195.0]
        result = compute_percentile(carries, 75)
        expected = float(np.percentile(carries, 75))
        assert result == pytest.approx(expected, abs=0.01)

    def test_percentile_p50_median(self):
        """P50 should equal the median."""
        from services.analytics import compute_percentile
        carries = [100.0, 110.0, 120.0, 130.0, 140.0]
        result = compute_percentile(carries, 50)
        expected = float(np.percentile(carries, 50))
        assert result == pytest.approx(expected, abs=0.01)
        assert result == pytest.approx(120.0, abs=0.01)

    def test_percentile_p90(self):
        """P90 — aspirational distance."""
        from services.analytics import compute_percentile
        carries = [150.0, 155.0, 160.0, 165.0, 170.0,
                   175.0, 180.0, 185.0, 190.0, 195.0]
        result = compute_percentile(carries, 90)
        expected = float(np.percentile(carries, 90))
        assert result == pytest.approx(expected, abs=0.01)

    def test_percentile_single_shot(self):
        """One data point — the only percentile is the value itself."""
        from services.analytics import compute_percentile
        result = compute_percentile([172.5], 75)
        assert result == pytest.approx(172.5, abs=0.01)

    def test_percentile_empty_data(self):
        """Zero data points — should return None or 0 (not crash)."""
        from services.analytics import compute_percentile
        result = compute_percentile([], 75)
        assert result is None or result == 0.0

    def test_percentile_two_values(self):
        """Two values — percentile interpolation."""
        from services.analytics import compute_percentile
        carries = [100.0, 200.0]
        result = compute_percentile(carries, 75)
        expected = float(np.percentile(carries, 75))
        assert result == pytest.approx(expected, abs=0.01)

    def test_percentile_all_same(self):
        """All identical values — any percentile should return that value."""
        from services.analytics import compute_percentile
        carries = [165.0] * 10
        for p in [25, 50, 75, 90]:
            result = compute_percentile(carries, p)
            assert result == pytest.approx(165.0, abs=0.01)


class TestExcludedShotsNotInPercentile:
    """Excluded shots must be filtered out before percentile computation."""

    def test_excluded_shots_not_in_percentile(self, app, db, sample_session):
        """Shots marked excluded=True must not contribute to percentile."""
        from services.analytics import compute_percentile_for_club
        from tests.conftest import _make_shot

        with app.app_context():
            # Add 5 normal + 1 excluded shot (carry=500 — would skew results)
            for i, carry in enumerate([150, 160, 170, 180, 190]):
                db.session.add(_make_shot(
                    sample_session.id, '7 Iron', '7i', carry, carry + 10,
                    club_index=i))
            db.session.add(_make_shot(
                sample_session.id, '7 Iron', '7i', 500.0, 510.0,
                excluded=True, club_index=5))
            db.session.commit()

            result = compute_percentile_for_club(sample_session.id, '7i', 75)
            # P75 of [150,160,170,180,190] via numpy = 180.0
            expected = float(np.percentile([150, 160, 170, 180, 190], 75))
            assert result == pytest.approx(expected, abs=0.5)


class TestErrantShotFlagging:
    """Shots outside P10–P90 carry range should be flagged as errant."""

    def test_errant_shot_flagging(self, app, db, sample_session):
        from services.analytics import flag_errant_shots
        from tests.conftest import _make_shot

        with app.app_context():
            # 10 shots with carries [100..190 step 10]
            carries = list(range(100, 200, 10))
            for i, c in enumerate(carries):
                db.session.add(_make_shot(
                    sample_session.id, '7 Iron', '7i', float(c), float(c + 10),
                    club_index=i))
            # One clearly errant shot (carry=10)
            db.session.add(_make_shot(
                sample_session.id, '7 Iron', '7i', 10.0, 15.0, club_index=10))
            # One clearly errant shot (carry=300)
            db.session.add(_make_shot(
                sample_session.id, '7 Iron', '7i', 300.0, 310.0, club_index=11))
            db.session.commit()

            errant_ids = flag_errant_shots(sample_session.id, '7i')
            # The 10-yard and 300-yard shots should be flagged
            assert len(errant_ids) >= 2


class TestPerClubStatistics:
    """Per-club aggregate stats (mean, min, max, count)."""

    def test_per_club_statistics(self, app, db, sample_session):
        from services.analytics import per_club_stats
        from tests.conftest import _make_shot

        with app.app_context():
            for i, carry in enumerate([150, 160, 170]):
                db.session.add(_make_shot(
                    sample_session.id, '9 Iron', '9i', float(carry),
                    float(carry + 10), club_index=i))
            db.session.commit()

            stats = per_club_stats(sample_session.id, '9i')
            assert stats['count'] == 3
            assert stats['min_carry'] == pytest.approx(150.0)
            assert stats['max_carry'] == pytest.approx(170.0)
            assert stats['mean_carry'] == pytest.approx(160.0, abs=0.1)
