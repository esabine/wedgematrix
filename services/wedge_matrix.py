import numpy as np
from models.database import db, Session, Shot
from services.analytics import percentile_value

# Swing sizes in display order (4/4 removed; fractions renamed x/3)
SWING_SIZES = ['3/3', '2/3', '1/3', '10:2', '10:3', '9:3', '8:4']

# Fraction sizes show Carry only; clock-hand sizes show Carry/Max
FRACTION_SIZES = {'3/3', '2/3', '1/3'}
CLOCK_SIZES = {'10:2', '10:3', '9:3', '8:4'}

# Wedge matrix clubs — PW first, then AW, SW, LW
WEDGE_CLUBS = ['PW', 'AW', 'SW', 'LW']


def build_wedge_matrix(session_id=None, percentile=75, include_test=False):
    """Build the wedge matrix: Swing Size × PW/AW/SW/LW.

    Fraction sizes (3/3, 2/3, 1/3): cell = {'carry': N}
    Clock sizes (10:2, 10:3, 9:3, 8:4): cell = {'carry': N, 'max': M}
    Empty cell = None

    Returns:
        {
            'swing_sizes': ['3/3', ...],
            'clubs': ['PW', 'AW', 'SW', 'LW'],
            'matrix': {
                '3/3': {'PW': {'carry': 100}, 'AW': {'carry': 85}, ...},
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
    elif not include_test:
        q = q.join(Session).filter(Session.is_test == False)

    shots = q.all()

    # Group by (swing_size, club_short), mapping old fraction names to new
    SWING_RENAME = {'3/4': '3/3', '2/4': '2/3', '1/4': '1/3'}
    grouped = {}
    for s in shots:
        size = SWING_RENAME.get(s.swing_size, s.swing_size)
        key = (size, s.club_short)
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


# Alias that returns just the matrix dict (keyed by swing_size) for simpler access
def generate_wedge_matrix(session_id=None, percentile=75, include_test=False):
    result = build_wedge_matrix(session_id=session_id, percentile=percentile, include_test=include_test)
    return result['matrix']
