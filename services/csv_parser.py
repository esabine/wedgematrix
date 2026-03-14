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


def parse_header(csv_text):
    """Parse the CSV header row to extract date and location.

    Expected format: Dates,03-12-2026,Place,Driving Ranges
    Returns: (date_obj, location_str)
    """
    lines = csv_text.strip().split('\n')
    if not lines:
        return None, None

    first_line = lines[0]
    parts = first_line.split(',')

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

    return session_date, location


def parse_csv(csv_text):
    """Parse the full CSV file and return structured shot data.

    Returns: {
        'session_date': date or None,
        'location': str or None,
        'shots': [dict, ...]
    }
    """
    session_date, location = parse_header(csv_text)

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
            'location': location,
            'shots': [],
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
            'offline': safe_float(parts[12]) if len(parts) > 12 else None,
            'landing_angle': safe_float(parts[13]) if len(parts) > 13 else None,
            'club_path': parse_direction(parts[14]) if len(parts) > 14 else None,
            'face_angle': parse_direction(parts[15]) if len(parts) > 15 else None,
            'attack_angle': safe_float(parts[16]) if len(parts) > 16 else None,
            'dynamic_loft': safe_float(parts[17]) if len(parts) > 17 else None,
        }

        # Handle signed offline: L prefix = negative (left), R prefix = positive (right)
        offline_raw = parts[12].strip() if len(parts) > 12 else None
        if offline_raw and (offline_raw.startswith('L') or offline_raw.startswith('R')):
            shot['offline'] = parse_direction(offline_raw)

        shots.append(shot)

    return {
        'session_date': session_date,
        'location': location,
        'shots': shots,
    }
