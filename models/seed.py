from .database import db, ClubLoft

# All 14 clubs with standard loft angles
CLUB_LOFTS = [
    ('1W', 10.5),
    ('3W', 15.0),
    ('2H', 18.0),
    ('3H', 21.0),
    ('4i', 21.0),
    ('5i', 24.0),
    ('6i', 27.0),
    ('7i', 31.0),
    ('8i', 35.0),
    ('9i', 39.0),
    ('PW', 44.0),
    ('AW', 50.0),
    ('SW', 56.0),
    ('LW', 60.0),
]


def seed_club_lofts():
    """Seed the club_lofts table if empty."""
    if ClubLoft.query.count() == 0:
        for short, loft in CLUB_LOFTS:
            db.session.add(ClubLoft(club_short=short, standard_loft=loft))
        db.session.commit()
