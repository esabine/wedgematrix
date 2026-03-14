from .database import db, ClubLoft

# All 14 clubs with standard loft angles
CLUB_LOFTS = [
    ('1W', 10.5),
    ('3W', 15.0),
    ('2H', 17.0),
    ('3H', 20.0),
    ('4i', 23.0),
    ('5i', 25.5),
    ('6i', 28.5),
    ('7i', 32.0),
    ('8i', 36.0),
    ('9i', 40.0),
    ('PW', 45.0),
    ('AW', 50.0),
    ('SW', 55.0),
    ('LW', 60.0),
]


def seed_club_lofts():
    """Seed the club_lofts table if empty."""
    if ClubLoft.query.count() == 0:
        for short, loft in CLUB_LOFTS:
            db.session.add(ClubLoft(club_short=short, standard_loft=loft))
        db.session.commit()
