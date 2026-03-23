import csv
import io
import math
from datetime import datetime

# CSV club name → short name mapping
CLUB_NAME_MAP = {
    'Driver': '1W',
    '3 Wood': '3W',
    '2 Hybrid': '2H',
    '3 Hybrid': '3H',
    '4 Hybrid': '4H',
    '3 Iron': '3i',
    '4 Iron': '4i',
    '5 Iron': '5i',
    '6 Iron': '6i',
    '7 Iron': '7i',
    '8 Iron': '8i',
    '9 Iron': '9i',
    'P-Wedge': 'PW',
    'G-Wedge': 'AW',
    'S-Wedge': 'SW',
    'L-Wedge': 'LW',
}


def parse_direction(value):
    """Parse directional value: R prefix → positive, L prefix → negative.

    Handles: 'R8.5' → 8.5, 'L3.2' → -3.2, '0.0' → 0.0, 'NaN' → None
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() == 'nan':
        return None
    if value.startswith('R'):
        try:
            return float(value[1:])
        except ValueError:
            return None
    elif value.startswith('L'):
        try:
            return -float(value[1:])
        except ValueError:
            return None
    else:
        try:
            return float(value)
        except ValueError:
            return None


def safe_float(value):
    """Safely convert to float, returning None for empty/NaN."""
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() == 'nan':
        return None
    try:
        result = float(value)
        if math.isnan(result):
            return None
        return result
    except (ValueError, TypeError):
        return None


def safe_int(value):
    """Safely convert to int, returning None for empty/NaN."""
    f = safe_float(value)
    if f is None:
        return None
    return int(round(f))


def parse_side_spin(value):
    """Parse side spin — may have L/R prefix indicating direction, or be plain signed."""
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() == 'nan':
        return None
    if value.startswith('R'):
        try:
            return int(round(float(value[1:])))
        except ValueError:
            return None
    elif value.startswith('L'):
        try:
            return -int(round(float(value[1:])))
        except ValueError:
            return None
    else:
        try:
            return int(round(float(value)))
        except ValueError:
            return None


def parse_back_spin(value):
    """Parse back spin — may have L/R prefix or be plain signed."""
    return parse_side_spin(value)


def normalize_club_name(name):
    """Map a CSV club name to its short code.

    e.g. '5 Iron' -> '5i', 'G-Wedge' -> 'AW'
    Returns the short code if mapped, or the original name if unknown.
    """
    return CLUB_NAME_MAP.get(name, name)


def should_skip_row(row):
    """Return True if this CSV row should be skipped (blank, Average, Deviation)."""
    club = row.get('Club', '').strip() if isinstance(row, dict) else ''
    index_val = row.get('Index', '').strip() if isinstance(row, dict) else ''
    if not club and index_val in ('', 'Average', 'Deviation'):
        return True
    if not club:
        return True
    return False


def parse_shot_row(row):
    """Parse a single shot row (dict keyed by CSV column headers) into a shot dict."""
    club = row.get('Club', '').strip()
    club_short = normalize_club_name(club)
    index_val = row.get('Index', '')

    return {
        'club': club,
        'club_short': club_short,
        'club_index': safe_int(index_val),
        'ball_speed': safe_float(row.get('Ball Speed(mph)')),
        'launch_direction': row.get('Launch Direction', ''),
        'launch_direction_deg': parse_direction(row.get('Launch Direction')),
        'launch_angle': safe_float(row.get('Launch Angle')),
        'spin_rate': safe_int(row.get('Spin Rate')),
        'spin_axis': row.get('Spin Axis', ''),
        'spin_axis_deg': parse_direction(row.get('Spin Axis')),
        'back_spin': parse_back_spin(row.get('Back Spin')),
        'side_spin': parse_side_spin(row.get('Side Spin')),
        'apex': safe_float(row.get('Apex(yd)')),
        'carry': safe_float(row.get('Carry(yd)')),
        'total': safe_float(row.get('Total(yd)')),
        'offline': parse_direction(row.get('Offline(yd)')),
        'landing_angle': safe_float(row.get('Landing Angle')),
        'club_path': parse_direction(row.get('Club Path')),
        'face_angle': parse_direction(row.get('Face Angle')),
        'attack_angle': safe_float(row.get('Attack Angle')),
        'dynamic_loft': safe_float(row.get(' Dynamic Loft', row.get('Dynamic Loft'))),
    }


def parse_header(csv_text):
    """Parse the CSV header row to extract date and location.

    Expected format: Dates,03-12-2026,Place,Driving Ranges
    Returns: dict with 'date_str', 'date', and 'location' keys.
    """
    lines = csv_text.strip().split('\n')
    if not lines:
        return {'date_str': None, 'date': None, 'location': None}

    first_line = lines[0]
    parts = first_line.split(',')

    date_str = None
    session_date = None
    location = None

    if len(parts) >= 2:
        date_str = parts[1].strip()
        try:
            session_date = datetime.strptime(date_str, '%m-%d-%Y').date()
        except ValueError:
            try:
                session_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

    if len(parts) >= 4:
        location = parts[3].strip()

    return {'date_str': date_str, 'date': session_date, 'location': location}


def parse_csv_file(file_path):
    """Parse a CSV file from disk. Convenience wrapper around parse_csv.

    Returns dict with 'date_str', 'date', 'location', 'shots' keys.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    return parse_csv(text)


def parse_csv(csv_text):
    """Parse the full CSV file and return structured shot data.

    Returns: {
        'date_str': str or None,
        'date': date or None,
        'location': str or None,
        'shots': [dict, ...]
    }
    """
    header = parse_header(csv_text)
    session_date = header['date']
    location = header['location']
    date_str = header['date_str']

    lines = csv_text.strip().split('\n')
    shots = []

    # Find the column header row (starts with "Club,Index,")
    header_row_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Club,Index,'):
            header_row_idx = i
            break

    if header_row_idx is None:
        return {
            'session_date': session_date,
        'date_str': date_str,
        'date': session_date,
        }

    # Parse remaining rows as shot data
    data_lines = lines[header_row_idx + 1:]

    for line in data_lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split(',')
        if len(parts) < 18:
            continue

        club = parts[0].strip()
        index_val = parts[1].strip()

        # Skip summary rows: empty club with "Average" or "Deviation" index
        if not club and index_val in ('Average', 'Deviation'):
            continue

        # Skip rows with no club name at all
        if not club:
            continue

        # Normalize club name
        club_short = CLUB_NAME_MAP.get(club, club)

        shot = {
            'club': club,
            'club_short': club_short,
            'club_index': safe_int(index_val),
            'ball_speed': safe_float(parts[2]),
            'launch_direction': parts[3].strip() if len(parts) > 3 else None,
            'launch_direction_deg': parse_direction(parts[3]) if len(parts) > 3 else None,
            'launch_angle': safe_float(parts[4]) if len(parts) > 4 else None,
            'spin_rate': safe_int(parts[5]) if len(parts) > 5 else None,
            'spin_axis': parts[6].strip() if len(parts) > 6 else None,
            'spin_axis_deg': parse_direction(parts[6]) if len(parts) > 6 else None,
            'back_spin': parse_back_spin(parts[7]) if len(parts) > 7 else None,
            'side_spin': parse_side_spin(parts[8]) if len(parts) > 8 else None,
            'apex': safe_float(parts[9]) if len(parts) > 9 else None,
            'carry': safe_float(parts[10]) if len(parts) > 10 else None,
            'total': safe_float(parts[11]) if len(parts) > 11 else None,
            'offline': parse_direction(parts[12]) if len(parts) > 12 else None,
            'landing_angle': safe_float(parts[13]) if len(parts) > 13 else None,
            'club_path': parse_direction(parts[14]) if len(parts) > 14 else None,
            'face_angle': parse_direction(parts[15]) if len(parts) > 15 else None,
            'attack_angle': safe_float(parts[16]) if len(parts) > 16 else None,
            'dynamic_loft': safe_float(parts[17]) if len(parts) > 17 else None,
        }

        shots.append(shot)

    return {
        'session_date': session_date,
        'date_str': date_str,
        'date': session_date,
        'location': location,
        'shots': shots,
    }
