"""Shared pytest fixtures for the wedgeMatrix test suite."""
import os
import pytest
from datetime import date, datetime
from flask import Flask
from models.database import db as _db, Session, Shot, ClubLoft, init_db
from models.seed import seed_club_lofts, CLUB_LOFTS

# ── Paths to real CSV samples ──────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CLEVELANDS_CSV = os.path.join(PROJECT_ROOT, 'clevelands-03-12-2026-DrivingRange.csv')
ESABINE_CSV = os.path.join(PROJECT_ROOT, 'esabine-03-08-2026-DrivingRange.csv')


@pytest.fixture(scope='session')
def clevelands_csv_path():
    """Path to the clevelands sample CSV."""
    return CLEVELANDS_CSV


@pytest.fixture(scope='session')
def esabine_csv_path():
    """Path to the esabine sample CSV."""
    return ESABINE_CSV


# ── Flask app + in-memory DB ───────────────────────────────────────────
@pytest.fixture(scope='function')
def app():
    """Create a Flask app with an in-memory SQLite database per test."""
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    test_app.config['DEFAULT_PERCENTILE'] = 75

    _db.init_app(test_app)
    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    """Provide the SQLAlchemy database instance inside an app context."""
    with app.app_context():
        yield _db


@pytest.fixture(scope='function')
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def seeded_db(app, db):
    """Database with club_lofts pre-populated."""
    with app.app_context():
        seed_club_lofts()
        yield db


# ── Sample shot data fixtures ──────────────────────────────────────────
# These mirror real rows from the CSV files so integration tests stay honest.

@pytest.fixture
def sample_session(app, db):
    """Create a sample session in the database."""
    with app.app_context():
        session = Session(
            filename='test-session.csv',
            session_date=date(2026, 3, 12),
            location='Driving Ranges',
            data_type='club',
        )
        db.session.add(session)
        db.session.commit()
        yield session


@pytest.fixture
def sample_wedge_session(app, db):
    """Create a sample wedge session in the database."""
    with app.app_context():
        session = Session(
            filename='test-wedge-session.csv',
            session_date=date(2026, 3, 12),
            location='Driving Ranges',
            data_type='wedge',
        )
        db.session.add(session)
        db.session.commit()
        yield session


def _make_shot(session_id, club, club_short, carry, total, dynamic_loft=None,
               excluded=False, swing_size='full', club_index=0, **kwargs):
    """Helper to create a Shot object with sensible defaults."""
    return Shot(
        session_id=session_id,
        club=club,
        club_short=club_short,
        club_index=club_index,
        swing_size=swing_size,
        ball_speed=kwargs.get('ball_speed', 100.0),
        launch_direction=kwargs.get('launch_direction', 'R5.0'),
        launch_direction_deg=kwargs.get('launch_direction_deg', 5.0),
        launch_angle=kwargs.get('launch_angle', 15.0),
        spin_rate=kwargs.get('spin_rate', 5000),
        spin_axis=kwargs.get('spin_axis', 'L10.0'),
        spin_axis_deg=kwargs.get('spin_axis_deg', -10.0),
        back_spin=kwargs.get('back_spin', 4800),
        side_spin=kwargs.get('side_spin', -870),
        apex=kwargs.get('apex', 25.0),
        carry=carry,
        total=total,
        offline=kwargs.get('offline', 5.0),
        landing_angle=kwargs.get('landing_angle', 45.0),
        club_path=kwargs.get('club_path', 5.0),
        face_angle=kwargs.get('face_angle', 3.0),
        attack_angle=kwargs.get('attack_angle', 1.0),
        dynamic_loft=dynamic_loft,
        excluded=excluded,
    )


@pytest.fixture
def five_iron_shots(app, db, sample_session):
    """Ten 5-Iron shots with known carry values for percentile verification."""
    carries = [150.0, 155.0, 160.0, 165.0, 170.0,
               175.0, 180.0, 185.0, 190.0, 195.0]
    totals = [c + 10 for c in carries]
    shots = []
    with app.app_context():
        for i, (c, t) in enumerate(zip(carries, totals)):
            s = _make_shot(sample_session.id, '5 Iron', '5i', c, t,
                           dynamic_loft=24.0, club_index=i)
            db.session.add(s)
            shots.append(s)
        db.session.commit()
    return carries, totals


@pytest.fixture
def mixed_club_shots(app, db, sample_session, seeded_db):
    """Shots across multiple clubs for club matrix testing."""
    data = {
        '7 Iron': ('7i', [148.0, 153.0, 158.0, 163.0, 168.0],
                         [158.0, 163.0, 168.0, 173.0, 178.0]),
        'P-Wedge': ('PW', [108.0, 112.0, 116.0, 120.0, 124.0],
                          [110.0, 114.0, 118.0, 122.0, 126.0]),
        'Driver':  ('1W', [215.0, 220.0, 225.0, 230.0, 235.0],
                          [240.0, 245.0, 250.0, 255.0, 260.0]),
    }
    shots = []
    with app.app_context():
        for club, (short, carries, totals) in data.items():
            for i, (c, t) in enumerate(zip(carries, totals)):
                s = _make_shot(sample_session.id, club, short, c, t, club_index=i)
                db.session.add(s)
                shots.append(s)
        db.session.commit()
    return data


@pytest.fixture
def wedge_shots(app, db, sample_wedge_session, seeded_db):
    """Wedge shots across AW/SW/LW with various swing sizes (new naming)."""
    entries = [
        # (club, club_short, swing_size, carry, total)
        ('G-Wedge', 'AW', '3/3', 72.0, 74.0),
        ('G-Wedge', 'AW', '3/3', 70.0, 72.0),
        ('G-Wedge', 'AW', '2/3', 55.0, 57.0),
        ('G-Wedge', 'AW', '10:2', 82.0, 85.0),
        ('G-Wedge', 'AW', '10:2', 78.0, 80.0),
        ('G-Wedge', 'AW', '10:2', 84.0, 87.0),
        ('S-Wedge', 'SW', '3/3', 80.0, 82.0),
        ('S-Wedge', 'SW', '3/3', 78.0, 80.0),
        ('S-Wedge', 'SW', '2/3', 62.0, 64.0),
        ('S-Wedge', 'SW', '10:3', 68.0, 70.0),
        ('S-Wedge', 'SW', '10:3', 72.0, 74.0),
        ('L-Wedge', 'LW', '3/3', 70.0, 72.0),
        ('L-Wedge', 'LW', '3/3', 68.0, 70.0),
        ('L-Wedge', 'LW', '1/3', 25.0, 27.0),
        ('L-Wedge', 'LW', '8:4', 38.0, 40.0),
        ('L-Wedge', 'LW', '8:4', 42.0, 44.0),
    ]
    shots = []
    with app.app_context():
        for i, (club, short, swing, carry, total) in enumerate(entries):
            s = _make_shot(sample_wedge_session.id, club, short, carry, total,
                           swing_size=swing, club_index=i)
            db.session.add(s)
            shots.append(s)
        db.session.commit()
    return entries


@pytest.fixture
def loft_analysis_shots(app, db, sample_session, seeded_db):
    """Shots with specific dynamic_loft values for loft analysis tests.
    Standard loft for 7i = 31.0 degrees.
    """
    lofts = [28.0, 30.0, 31.0, 33.0, 35.0]  # 3 good (≤31), 2 bad (>31)
    shots = []
    with app.app_context():
        for i, dl in enumerate(lofts):
            s = _make_shot(sample_session.id, '7 Iron', '7i', 155.0, 165.0,
                           dynamic_loft=dl, club_index=i)
            db.session.add(s)
            shots.append(s)
        db.session.commit()
    return lofts
