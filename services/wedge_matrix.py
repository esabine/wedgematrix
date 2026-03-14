import numpy as np
from models.database import db, Shot
from services.analytics import percentile_value

# Swing sizes in display order
SWING_SIZES = ['4/4', '3/4', '2/4', '1/4', '10:2', '10:3', '9:3', '8:4']

# Fraction sizes show Carry only; clock-hand sizes show Carry/Max
FRACTION_SIZES = {'4/4', '3/4', '2/4', '1/4'}
CLOCK_SIZES = {'10:2', '10:3', '9:3', '8:4'}

# Wedge matrix clubs — AW, SW, LW only (NOT PW)
WEDGE_CLUBS = ['AW', 'SW', 'LW']


def build_wedge_matrix(session_id=None, percentile=75):
    """Build the wedge matrix: Swing Size × AW/SW/LW.

    Fraction sizes (4/4, 3/4, 2/4, 1/4): cell = {'carry': N}
    Clock sizes (10:2, 10:3, 9:3, 8:4): cell = {'carry': N, 'max': M}
    Empty cell = None

    Returns:
        {
            'swing_sizes': ['4/4', ...],
            'clubs': ['AW', 'SW', 'LW'],
            'matrix': {
                '4/4': {'AW': {'carry': 85}, 'SW': None, 'LW': {'carry': 42}},
                ...
            }
        }
    """
    q = Shot.query.filter(
        Shot.excluded == False,
        Shot.club_short.in_(WEDGE_CLUBS),
        Shot.swing_size != 'full',
    )
    if session_id is not None:
        q = q.filter(Shot.session_id == session_id)

    shots = q.all()

    # Group by (swing_size, club_short)
    grouped = {}
    for s in shots:
        key = (s.swing_size, s.club_short)
        grouped.setdefault(key, []).append(s)

    matrix = {}
    for size in SWING_SIZES:
        row = {}
        for club in WEDGE_CLUBS:
            key = (size, club)
            club_shots = grouped.get(key, [])
            carries = [s.carry for s in club_shots if s.carry is not None]

            if not carries:
                row[club] = None
                continue

            carry_pct = round(percentile_value(carries, percentile))

            if size in FRACTION_SIZES:
                row[club] = {'carry': carry_pct}
            else:
                # Clock-hand: show carry and max carry
                max_carry = round(max(carries))
                row[club] = {'carry': carry_pct, 'max': max_carry}

        matrix[size] = row

    return {
        'swing_sizes': SWING_SIZES,
        'clubs': WEDGE_CLUBS,
        'matrix': matrix,
    }
