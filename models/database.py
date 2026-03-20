from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Session(db.Model):
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.Text, nullable=False)
    session_date = db.Column(db.Date, nullable=True)
    location = db.Column(db.Text, nullable=True)
    data_type = db.Column(db.Text, nullable=False)  # "club" or "wedge"
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    shots = db.relationship('Shot', backref='session', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'session_date': self.session_date.isoformat() if self.session_date else None,
            'location': self.location,
            'data_type': self.data_type,
            'imported_at': self.imported_at.isoformat() if self.imported_at else None,
            'notes': self.notes,
            'shot_count': self.shots.count(),
        }


class Shot(db.Model):
    __tablename__ = 'shots'
    __table_args__ = (
        db.Index('ix_shots_session_club', 'session_id', 'club_short'),
        db.Index('ix_shots_club_excluded', 'club_short', 'excluded'),
        db.Index('ix_shots_session_excluded', 'session_id', 'excluded'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False, index=True)
    club = db.Column(db.Text, nullable=False)
    club_short = db.Column(db.Text, nullable=False, index=True)
    club_index = db.Column(db.Integer, nullable=True)
    swing_size = db.Column(db.Text, nullable=False, default='full')
    ball_speed = db.Column(db.Float, nullable=True)
    launch_direction = db.Column(db.Text, nullable=True)
    launch_direction_deg = db.Column(db.Float, nullable=True)
    launch_angle = db.Column(db.Float, nullable=True)
    spin_rate = db.Column(db.Integer, nullable=True)
    spin_axis = db.Column(db.Text, nullable=True)
    spin_axis_deg = db.Column(db.Float, nullable=True)
    back_spin = db.Column(db.Integer, nullable=True)
    side_spin = db.Column(db.Integer, nullable=True)
    apex = db.Column(db.Float, nullable=True)
    carry = db.Column(db.Float, nullable=True)
    total = db.Column(db.Float, nullable=True)
    offline = db.Column(db.Float, nullable=True)
    landing_angle = db.Column(db.Float, nullable=True)
    club_path = db.Column(db.Float, nullable=True)
    face_angle = db.Column(db.Float, nullable=True)
    attack_angle = db.Column(db.Float, nullable=True)
    dynamic_loft = db.Column(db.Float, nullable=True)
    excluded = db.Column(db.Boolean, default=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'club': self.club,
            'club_short': self.club_short,
            'club_index': self.club_index,
            'swing_size': self.swing_size,
            'ball_speed': self.ball_speed,
            'launch_direction': self.launch_direction,
            'launch_direction_deg': self.launch_direction_deg,
            'launch_angle': self.launch_angle,
            'spin_rate': self.spin_rate,
            'spin_axis': self.spin_axis,
            'spin_axis_deg': self.spin_axis_deg,
            'back_spin': self.back_spin,
            'side_spin': self.side_spin,
            'apex': self.apex,
            'carry': self.carry,
            'total': self.total,
            'offline': self.offline,
            'landing_angle': self.landing_angle,
            'club_path': self.club_path,
            'face_angle': self.face_angle,
            'attack_angle': self.attack_angle,
            'dynamic_loft': self.dynamic_loft,
            'excluded': self.excluded,
        }


class ClubLoft(db.Model):
    __tablename__ = 'club_lofts'

    club_short = db.Column(db.Text, primary_key=True)
    standard_loft = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'club_short': self.club_short,
            'standard_loft': self.standard_loft,
        }


def init_db(app):
    """Initialize the database and create tables."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
