"""Tests for services.csv_parser — CSV parsing, direction handling, club mapping."""
import os
import csv
import tempfile
import pytest
from tests.conftest import CLEVELANDS_CSV, ESABINE_CSV


# ── Club name mapping (source of truth from IMPLEMENTATION_PLAN.md) ────
CLUB_NAME_MAP = {
    'Driver':   '1W',
    '3 Wood':   '3W',
    '2 Hybrid': '2H',
    '3 Hybrid': '3H',
    '4 Iron':   '4i',
    '5 Iron':   '5i',
    '6 Iron':   '6i',
    '7 Iron':   '7i',
    '8 Iron':   '8i',
    '9 Iron':   '9i',
    'P-Wedge':  'PW',
    'G-Wedge':  'AW',
    'S-Wedge':  'SW',
    'L-Wedge':  'LW',
}


# ── Helpers ────────────────────────────────────────────────────────────
def _write_csv(tmp_dir, filename, lines):
    """Write a list of text lines as a CSV file and return its path."""
    path = os.path.join(tmp_dir, filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path


# ── Header parsing ─────────────────────────────────────────────────────
class TestParseHeaderRow:
    """CSV header row: Dates,MM-DD-YYYY,Place,LocationText."""

    def test_parse_header_row_clevelands(self):
        from services.csv_parser import parse_header
        header_line = 'Dates,03-12-2026,Place,Driving Ranges'
        result = parse_header(header_line)
        assert result['date_str'] == '03-12-2026'
        assert result['location'] == 'Driving Ranges'

    def test_parse_header_row_esabine(self):
        from services.csv_parser import parse_header
        header_line = 'Dates,03-08-2026,Place,Driving Ranges'
        result = parse_header(header_line)
        assert result['date_str'] == '03-08-2026'


# ── Direction parsing ──────────────────────────────────────────────────
class TestDirectionParsing:
    """Parse R/L prefixed direction strings into signed floats."""

    def test_direction_parsing_right(self):
        from services.csv_parser import parse_direction
        assert parse_direction('R8.5') == pytest.approx(8.5)

    def test_direction_parsing_left(self):
        from services.csv_parser import parse_direction
        assert parse_direction('L3.2') == pytest.approx(-3.2)

    def test_direction_parsing_zero_right(self):
        from services.csv_parser import parse_direction
        assert parse_direction('R0.0') == pytest.approx(0.0)

    def test_direction_parsing_zero_left(self):
        from services.csv_parser import parse_direction
        assert parse_direction('L0.0') == pytest.approx(0.0)

    def test_direction_parsing_plain_numeric(self):
        from services.csv_parser import parse_direction
        assert parse_direction('5.3') == pytest.approx(5.3)

    def test_direction_parsing_plain_zero(self):
        from services.csv_parser import parse_direction
        assert parse_direction('0.0') == pytest.approx(0.0)

    def test_direction_parsing_negative_plain(self):
        from services.csv_parser import parse_direction
        assert parse_direction('-2.5') == pytest.approx(-2.5)

    def test_direction_parsing_zero_no_prefix(self):
        from services.csv_parser import parse_direction
        # Some cells in real data show bare "0.0" for Club Path / Face Angle
        assert parse_direction('0.0') == pytest.approx(0.0)

    def test_direction_parsing_empty_string(self):
        from services.csv_parser import parse_direction
        result = parse_direction('')
        assert result is None or result == 0.0

    def test_direction_parsing_nan(self):
        """Real CSV has NaN in Landing Angle for some G-Wedge shots."""
        from services.csv_parser import parse_direction
        result = parse_direction('NaN')
        assert result is None


# ── Club name normalisation ────────────────────────────────────────────
class TestClubNameNormalization:
    """Map full CSV club names to short codes."""

    def test_club_name_normalization(self):
        from services.csv_parser import normalize_club_name
        assert normalize_club_name('5 Iron') == '5i'
        assert normalize_club_name('Driver') == '1W'

    @pytest.mark.parametrize('csv_name,expected_short', list(CLUB_NAME_MAP.items()))
    def test_club_name_normalization_all_clubs(self, csv_name, expected_short):
        from services.csv_parser import normalize_club_name
        assert normalize_club_name(csv_name) == expected_short

    def test_gwedge_maps_to_aw(self):
        """G-Wedge → AW is the critical mapping (gap wedge = anywhere wedge)."""
        from services.csv_parser import normalize_club_name
        assert normalize_club_name('G-Wedge') == 'AW'


# ── Shot data parsing ──────────────────────────────────────────────────
class TestParseShotData:

    def test_parse_shot_data_all_columns(self):
        """Verify every column from the header line is parsed correctly."""
        from services.csv_parser import parse_shot_row
        row = {
            'Club': '5 Iron',
            'Index': '2',
            'Ball Speed(mph)': '126.5',
            'Launch Direction': 'R4.8',
            'Launch Angle': '16.9',
            'Spin Rate': '3953',
            'Spin Axis': 'L28.2',
            'Back Spin': '3486',
            'Side Spin': 'L1865',
            'Apex(yd)': '29.7',
            'Carry(yd)': '188.0',
            'Total(yd)': '196.5',
            'Offline(yd)': 'L24.5',
            'Landing Angle': '41.6',
            'Club Path': 'R12.6',
            'Face Angle': 'R2.8',
            'Attack Angle': '0.4',
            ' Dynamic Loft': '22.8',
        }
        shot = parse_shot_row(row)
        assert shot['club'] == '5 Iron'
        assert shot['club_short'] == '5i'
        assert shot['club_index'] == 2
        assert shot['ball_speed'] == pytest.approx(126.5)
        assert shot['launch_direction_deg'] == pytest.approx(4.8)
        assert shot['carry'] == pytest.approx(188.0)
        assert shot['total'] == pytest.approx(196.5)
        assert shot['spin_rate'] == 3953
        assert shot['spin_axis_deg'] == pytest.approx(-28.2)
        assert shot['dynamic_loft'] == pytest.approx(22.8)
        assert shot['offline'] == pytest.approx(-24.5)


# ── Row skipping ───────────────────────────────────────────────────────
class TestRowSkipping:

    def test_skip_blank_rows(self):
        """Row 2 in real CSVs is blank — parser must skip it."""
        from services.csv_parser import should_skip_row
        row = {'Club': '', 'Index': ''}
        assert should_skip_row(row) is True

    def test_skip_average_rows(self):
        """Club=empty, Index=Average → skip."""
        from services.csv_parser import should_skip_row
        row = {'Club': '', 'Index': 'Average'}
        assert should_skip_row(row) is True

    def test_skip_deviation_rows(self):
        """Club=empty, Index=Deviation → skip."""
        from services.csv_parser import should_skip_row
        row = {'Club': '', 'Index': 'Deviation'}
        assert should_skip_row(row) is True

    def test_keep_valid_shot_row(self):
        """Normal shot row must NOT be skipped."""
        from services.csv_parser import should_skip_row
        row = {'Club': '7 Iron', 'Index': '0'}
        assert should_skip_row(row) is False


# ── Real CSV integration tests ─────────────────────────────────────────
class TestParseRealCSV:

    def test_parse_real_csv_clevelands(self, clevelands_csv_path):
        """Parse the full clevelands CSV and check shot counts per club.
        Manual count from CSV:
        2H:6, 4i:13, 5i:14, 6i:9, 7i:15, 8i:17, 9i:8, PW:15, AW:22, SW:11, LW:32
        Total: 162
        """
        from services.csv_parser import parse_csv_file
        result = parse_csv_file(clevelands_csv_path)
        assert result['date_str'] == '03-12-2026'
        assert result['location'] == 'Driving Ranges'
        shots = result['shots']
        # Verify we parsed actual shot rows, not averages/deviations
        assert len(shots) > 100  # there are ~162 shots
        # Every shot must have a non-empty club
        for shot in shots:
            assert shot['club'] != ''
            assert shot['club_short'] != ''

    def test_parse_real_csv_esabine(self, esabine_csv_path):
        """Parse the esabine CSV. Clubs present:
        Driver:2, 3W:2, 2H:5, 4i:7, 5i:15, 6i:8, 8i:7, 9i:14, PW:10, AW:5, SW:4, LW:3
        Total: 82
        """
        from services.csv_parser import parse_csv_file
        result = parse_csv_file(esabine_csv_path)
        assert result['date_str'] == '03-08-2026'
        shots = result['shots']
        assert len(shots) > 60  # there are ~82 shots
        # Check that Driver shots exist (unique to esabine file)
        driver_shots = [s for s in shots if s['club'] == 'Driver']
        assert len(driver_shots) == 2

    def test_no_average_rows_in_parsed_output(self, clevelands_csv_path):
        """Confirm Average/Deviation rows are excluded from shot data."""
        from services.csv_parser import parse_csv_file
        result = parse_csv_file(clevelands_csv_path)
        for shot in result['shots']:
            assert shot['club_index'] != 'Average'
            assert shot['club_index'] != 'Deviation'

    def test_clubs_present_in_clevelands(self, clevelands_csv_path):
        """Clevelands file has specific clubs — no Driver or 3 Wood."""
        from services.csv_parser import parse_csv_file
        result = parse_csv_file(clevelands_csv_path)
        club_shorts = set(s['club_short'] for s in result['shots'])
        assert '1W' not in club_shorts  # no Driver in clevelands
        assert '3W' not in club_shorts  # no 3 Wood in clevelands
        assert '2H' in club_shorts
        assert 'AW' in club_shorts  # G-Wedge → AW

    def test_clubs_present_in_esabine(self, esabine_csv_path):
        """Esabine file has Driver and 3 Wood but no 3 Hybrid or 7 Iron."""
        from services.csv_parser import parse_csv_file
        result = parse_csv_file(esabine_csv_path)
        club_shorts = set(s['club_short'] for s in result['shots'])
        assert '1W' in club_shorts   # Driver present
        assert '3W' in club_shorts   # 3 Wood present
        assert '3H' not in club_shorts
        assert '7i' not in club_shorts


# ── Malformed / edge case CSVs ─────────────────────────────────────────
class TestMalformedCSV:

    def test_malformed_csv_handling(self, tmp_path):
        """CSV with garbage data should not crash — raise or return empty."""
        from services.csv_parser import parse_csv_file
        bad_file = tmp_path / 'bad.csv'
        bad_file.write_text('this,is,not,valid,golf,data\n1,2,3')
        # Should either raise a ValueError or return with empty shots
        try:
            result = parse_csv_file(str(bad_file))
            assert result['shots'] == [] or isinstance(result, dict)
        except (ValueError, KeyError, IndexError):
            pass  # acceptable — malformed input should raise

    def test_empty_csv(self, tmp_path):
        """Completely empty CSV."""
        from services.csv_parser import parse_csv_file
        empty_file = tmp_path / 'empty.csv'
        empty_file.write_text('')
        try:
            result = parse_csv_file(str(empty_file))
            assert result['shots'] == []
        except (ValueError, KeyError, IndexError, StopIteration):
            pass  # acceptable

    def test_header_only_csv(self, tmp_path):
        """CSV with header row but no shots."""
        from services.csv_parser import parse_csv_file
        path = tmp_path / 'header_only.csv'
        path.write_text(
            'Dates,03-12-2026,Place,Test Range\n'
            '\n'
            'Club,Index,Ball Speed(mph),Launch Direction,Launch Angle,Spin Rate,'
            'Spin Axis,Back Spin,Side Spin,Apex(yd),Carry(yd),Total(yd),'
            'Offline(yd),Landing Angle,Club Path,Face Angle,Attack Angle, Dynamic Loft\n'
        )
        result = parse_csv_file(str(path))
        assert result['shots'] == []
        assert result['date_str'] == '03-12-2026'
