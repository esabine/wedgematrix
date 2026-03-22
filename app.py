import json
import os
import numpy as np
from datetime import date, datetime, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, send_from_directory
)

VERSION = '0.5.0'
from config import Config
from models.database import db, Session, Shot, ClubLoft, init_db
from models.seed import seed_club_lofts
from services.csv_parser import parse_csv, CLUB_NAME_MAP
from services.analytics import (
    club_stats, per_club_statistics, flag_errant_shots,
    dispersion_data, spin_vs_carry_data, shot_shape_data,
    carry_distribution, get_shots_query, detect_outliers,
    launch_spin_stability, radar_comparison,
    compute_dispersion_boundary,
)
from services.club_matrix import build_club_matrix, CLUB_ORDER
from services.wedge_matrix import build_wedge_matrix, SWING_SIZES, WEDGE_CLUBS
from services.loft_analysis import analyze_loft, loft_summary

DATE_RANGE_DAYS = {'7': 7, '30': 30, '60': 60, '90': 90}
DATE_RANGE_OPTIONS = [
    ('7', 'Last week'),
    ('30', 'Last 30 days'),
    ('60', 'Last 60 days'),
    ('90', 'Last 90 days'),
    ('', 'All time'),
]


def parse_date_range(value):
    """Convert a date_range query param to a date cutoff, or None for all time."""
    if value and value in DATE_RANGE_DAYS:
        return date.today() - timedelta(days=DATE_RANGE_DAYS[value])
    return None


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.json.sort_keys = False  # Preserve dict insertion order for CLUB_ORDER sorting

    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    init_db(app)

    @app.context_processor
    def inject_version():
        return dict(version=VERSION)

    with app.app_context():
        seed_club_lofts()

    register_routes(app)
    return app


def register_routes(app):

    # ──────────────────────────────────────────────
    # Page routes
    # ──────────────────────────────────────────────

    @app.route('/')
    def dashboard():
        all_sessions = Session.query.filter(Session.is_test == False).order_by(Session.session_date.desc()).all()
        total_shots = Shot.query.join(Session).filter(Session.is_test == False).count()
        clubs_tracked = db.session.query(Shot.club_short).join(Session).filter(Session.is_test == False).distinct().count()
        recent = Session.query.filter(Session.is_test == False).order_by(Session.imported_at.desc()).limit(5).all()
        return render_template('dashboard.html',
                               total_sessions=len(all_sessions),
                               total_shots=total_shots,
                               clubs_tracked=clubs_tracked,
                               recent_sessions=recent,
                               club_order=CLUB_ORDER)

    @app.route('/import/upload', methods=['POST'])
    def import_upload():
        """Alias for the POST side of import — templates may reference this."""
        return import_data()

    @app.route('/import', methods=['GET', 'POST'])
    def import_data():
        if request.method == 'GET':
            return render_template('import.html')

        file = request.files.get('file')
        if not file or not file.filename:
            flash('No file selected.', 'error')
            return redirect(url_for('import_data'))

        if not file.filename.lower().endswith('.csv'):
            flash('Please upload a CSV file.', 'error')
            return redirect(url_for('import_data'))

        csv_text = file.read().decode('utf-8', errors='replace')
        parsed = parse_csv(csv_text)

        if not parsed.get('shots'):
            flash('No shot data found in CSV.', 'error')
            return redirect(url_for('import_data'))

        data_type = request.form.get('data_type', 'club')

        session_info = {
            'filename': file.filename,
            'date': parsed.get('date_str', ''),
            'location': parsed.get('location', ''),
            'data_type': data_type,
        }

        return render_template('import.html',
                               parsed_shots=parsed['shots'],
                               session_info=session_info)

    @app.route('/import/save', methods=['POST'])
    def import_save():
        session_info = json.loads(request.form.get('session_info', '{}'))
        shots_data = json.loads(request.form.get('shots_data', '[]'))

        data_type = session_info.get('data_type', 'club')
        filename = session_info.get('filename', 'unknown.csv')
        location = session_info.get('location')

        # Parse date string back to a date object
        date_str = session_info.get('date', '')
        session_date = None
        if date_str:
            for fmt in ('%m-%d-%Y', '%Y-%m-%d'):
                try:
                    session_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue

        session = Session(
            filename=filename,
            session_date=session_date,
            location=location,
            data_type=data_type,
            notes='',
        )
        db.session.add(session)
        db.session.flush()  # get session.id

        for i, shot_data in enumerate(shots_data):
            if data_type == 'club':
                swing_size = 'full'
            else:
                swing_size = request.form.get(f'swing_sizes[{i}]', 'full')

            shot = Shot(
                session_id=session.id,
                club=shot_data.get('club', ''),
                club_short=shot_data.get('club_short', ''),
                club_index=shot_data.get('club_index'),
                swing_size=swing_size,
                ball_speed=shot_data.get('ball_speed'),
                launch_direction=shot_data.get('launch_direction'),
                launch_direction_deg=shot_data.get('launch_direction_deg'),
                launch_angle=shot_data.get('launch_angle'),
                spin_rate=shot_data.get('spin_rate'),
                spin_axis=shot_data.get('spin_axis'),
                spin_axis_deg=shot_data.get('spin_axis_deg'),
                back_spin=shot_data.get('back_spin'),
                side_spin=shot_data.get('side_spin'),
                apex=shot_data.get('apex'),
                carry=shot_data.get('carry'),
                total=shot_data.get('total'),
                offline=shot_data.get('offline'),
                landing_angle=shot_data.get('landing_angle'),
                club_path=shot_data.get('club_path'),
                face_angle=shot_data.get('face_angle'),
                attack_angle=shot_data.get('attack_angle'),
                dynamic_loft=shot_data.get('dynamic_loft'),
                excluded=False,
            )
            db.session.add(shot)

        db.session.commit()
        flash(f'Imported {len(shots_data)} shots from {filename}.', 'success')
        return redirect(url_for('session_detail', session_id=session.id))

    @app.route('/sessions')
    def sessions():
        include_test = request.args.get('include_test', 'false').lower() == 'true'
        q = Session.query
        if not include_test:
            q = q.filter(Session.is_test == False)
        sessions = q.order_by(Session.imported_at.desc()).all()
        return render_template('sessions.html', sessions=sessions, include_test=include_test)

    @app.route('/sessions/<int:session_id>')
    def session_detail(session_id):
        session = Session.query.get_or_404(session_id)
        shots = session.shots.order_by(Shot.club_short, Shot.club_index).all()
        return render_template('session_detail.html', session=session, shots=shots)

    @app.route('/sessions/<int:session_id>', methods=['DELETE'])
    def delete_session(session_id):
        session = Session.query.get_or_404(session_id)
        db.session.delete(session)
        db.session.commit()
        return jsonify({'status': 'deleted', 'id': session_id})

    @app.route('/sessions/<int:session_id>/delete', methods=['POST'])
    def delete_session_post(session_id):
        """POST alias for session deletion (form-based)."""
        session = Session.query.get_or_404(session_id)
        db.session.delete(session)
        db.session.commit()
        flash('Session deleted.', 'success')
        return redirect(url_for('sessions'))

    @app.route('/api/sessions/<int:session_id>/toggle-test', methods=['POST'])
    def toggle_test(session_id):
        session = Session.query.get_or_404(session_id)
        session.is_test = not session.is_test
        db.session.commit()
        return jsonify({'success': True, 'id': session.id, 'is_test': session.is_test})

    @app.route('/club-matrix')
    def club_matrix():
        session_id = request.args.get('session_id', type=int)
        percentile = request.args.get('percentile', Config.DEFAULT_PERCENTILE, type=int)
        include_test = request.args.get('include_test', 'false').lower() == 'true'
        all_sessions = Session.query.order_by(Session.session_date.desc()).all()
        matrix = build_club_matrix(session_id=session_id, percentile=percentile, include_test=include_test)
        return render_template('club_matrix.html',
                               matrix=matrix,
                               sessions=all_sessions,
                               selected_session=session_id,
                               percentile=percentile)

    @app.route('/wedge-matrix')
    def wedge_matrix():
        session_id = request.args.get('session_id', type=int)
        percentile = request.args.get('percentile', Config.DEFAULT_PERCENTILE, type=int)
        include_test = request.args.get('include_test', 'false').lower() == 'true'
        all_sessions = Session.query.order_by(Session.session_date.desc()).all()
        data = build_wedge_matrix(session_id=session_id, percentile=percentile, include_test=include_test)
        return render_template('wedge_matrix.html',
                               matrix=data['matrix'],
                               sessions=all_sessions,
                               selected_session=session_id,
                               percentile=percentile)

    @app.route('/shots')
    def shots():
        session_id = request.args.get('session_id', type=int)
        club = request.args.get('club', '')
        swing_size = request.args.get('swing_size')
        date_range = request.args.get('date_range', '')
        include_hidden = request.args.get('include_hidden', 'false').lower() == 'true'
        include_test = request.args.get('include_test', 'false').lower() == 'true'
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        per_page = min(per_page, 200)  # cap at 200

        date_from = parse_date_range(date_range)

        q = Shot.query
        needs_session_join = False

        if date_from is not None or (not include_test and not session_id):
            needs_session_join = True
            q = q.join(Session)
            if date_from is not None:
                q = q.filter(Session.session_date >= date_from)
            if not include_test and not session_id:
                q = q.filter(Session.is_test == False)

        if session_id:
            q = q.filter(Shot.session_id == session_id)
        if needs_session_join and session_id and date_from is not None:
            q = q.filter(Shot.session_id == session_id)

        # Parse comma-separated club filter
        club_list = [c.strip() for c in club.split(',') if c.strip()] if club else []
        if club_list:
            q = q.filter(Shot.club_short.in_(club_list))

        if swing_size:
            q = q.filter(Shot.swing_size == swing_size)

        # Count hidden shots before filtering them out
        hidden_count = q.filter(Shot.excluded == True).count()

        # Filter out excluded shots unless include_hidden is true
        if not include_hidden:
            q = q.filter(Shot.excluded == False)

        total_count = q.count()
        shot_list = q.order_by(
            Shot.session_id, Shot.club_short, Shot.club_index
        ).offset((page - 1) * per_page).limit(per_page).all()

        total_pages = max(1, (total_count + per_page - 1) // per_page)
        all_sessions = Session.query.order_by(Session.session_date.desc()).all()
        clubs = [r[0] for r in db.session.query(Shot.club_short).distinct().order_by(Shot.club_short).all()]

        # Augment shots with standard_loft and errant flag for template
        lofts = {cl.club_short: cl.standard_loft for cl in ClubLoft.query.all()}
        for s in shot_list:
            s.standard_loft = lofts.get(s.club_short)
            s.errant = False

        return render_template('shots.html',
                               shots=shot_list,
                               sessions=all_sessions,
                               clubs=clubs,
                               all_possible_clubs=CLUB_ORDER,
                               selected_session=session_id,
                               selected_club=club,
                               selected_clubs=club_list,
                               selected_swing_size=swing_size,
                               date_range=date_range,
                               include_hidden=include_hidden,
                               hidden_count=hidden_count,
                               page=page,
                               per_page=per_page,
                               total_pages=total_pages,
                               total_count=total_count)

    @app.route('/analytics')
    def analytics():
        session_id = request.args.get('session_id', type=int)
        date_range = request.args.get('date_range', '')
        percentile = request.args.get('percentile', Config.DEFAULT_PERCENTILE, type=int)
        sessions = Session.query.order_by(Session.session_date.desc()).all()
        has_data = Shot.query.join(Session).filter(Shot.excluded == False, Session.is_test == False).count() > 0
        clubs = [r[0] for r in db.session.query(Shot.club_short).join(Session).filter(Session.is_test == False).distinct().order_by(Shot.club_short).all()]
        return render_template('analytics.html',
                               sessions=sessions,
                               current_session_id=session_id,
                               has_data=has_data,
                               clubs=clubs,
                               date_range=date_range,
                               percentile=percentile,
                               date_range_options=DATE_RANGE_OPTIONS)

    # ──────────────────────────────────────────────
    # Print routes
    # ──────────────────────────────────────────────

    @app.route('/print/club-matrix')
    def print_club_matrix():
        session_id = request.args.get('session_id', type=int)
        percentile = request.args.get('percentile', Config.DEFAULT_PERCENTILE, type=int)
        matrix = build_club_matrix(session_id=session_id, percentile=percentile)
        return render_template('print_card.html',
                               club_matrix=matrix,
                               wedge_matrix={},
                               percentile=percentile)

    @app.route('/print/wedge-matrix')
    def print_wedge_matrix():
        session_id = request.args.get('session_id', type=int)
        percentile = request.args.get('percentile', Config.DEFAULT_PERCENTILE, type=int)
        data = build_wedge_matrix(session_id=session_id, percentile=percentile)
        return render_template('print_card.html',
                               club_matrix=[],
                               wedge_matrix=data['matrix'],
                               percentile=percentile)

    @app.route('/print/pocket-card')
    def print_pocket_card():
        session_id = request.args.get('session_id', type=int)
        percentile = request.args.get('percentile', Config.DEFAULT_PERCENTILE, type=int)
        cm = build_club_matrix(session_id=session_id, percentile=percentile)
        wd = build_wedge_matrix(session_id=session_id, percentile=percentile)
        return render_template('print_card.html',
                               club_matrix=cm,
                               wedge_matrix=wd['matrix'],
                               percentile=percentile)

    @app.route('/print')
    def print_card():
        """Alias — templates may link to print_card."""
        return print_pocket_card()

    # ──────────────────────────────────────────────
    # Shot management actions
    # ──────────────────────────────────────────────

    @app.route('/shots/<int:shot_id>/toggle-exclude', methods=['POST'])
    def toggle_exclude(shot_id):
        shot = Shot.query.get_or_404(shot_id)
        shot.excluded = not shot.excluded
        db.session.commit()
        return jsonify({'success': True, 'id': shot.id, 'excluded': shot.excluded})

    @app.route('/shots/batch-exclude', methods=['POST'])
    def batch_exclude():
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON body'}), 400

        shot_ids = data.get('shot_ids', [])
        # Support both 'exclude' (bool) and 'action' (string) from frontend
        if 'exclude' in data:
            exclude_val = bool(data['exclude'])
        else:
            action = data.get('action', 'exclude')
            exclude_val = action == 'exclude'

        if not shot_ids:
            return jsonify({'error': 'No shot IDs provided'}), 400

        Shot.query.filter(Shot.id.in_(shot_ids)).update(
            {'excluded': exclude_val}, synchronize_session='fetch'
        )
        db.session.commit()
        return jsonify({'success': True, 'updated': len(shot_ids), 'excluded': exclude_val})

    @app.route('/api/shots/suggested-exclusions')
    def api_suggested_exclusions():
        """Identify statistical outliers using IQR method per club.

        Query params:
            session_id: optional session filter.
            club: optional comma-separated club filter.
            date_range: optional date range filter (7/30/60/90).
            iqr_multiplier: IQR scaling factor (default 1.5).
        """
        session_id = request.args.get('session_id', type=int)
        club_raw = request.args.get('club', '')
        date_range = request.args.get('date_range', '')
        iqr_multiplier = request.args.get('iqr_multiplier', 1.5, type=float)
        date_from = parse_date_range(date_range)

        clubs = [c.strip() for c in club_raw.split(',') if c.strip()] if club_raw else None

        outliers = detect_outliers(
            session_id=session_id,
            club_short=clubs,
            date_from=date_from,
            iqr_multiplier=iqr_multiplier,
        )

        # Sort clubs by CLUB_ORDER for consistent frontend display
        ordered = {}
        for c in CLUB_ORDER:
            if c in outliers:
                ordered[c] = outliers[c]
        # Include any clubs not in CLUB_ORDER at the end
        for c in outliers:
            if c not in ordered:
                ordered[c] = outliers[c]

        total_count = sum(len(v) for v in ordered.values())
        return jsonify({
            'outliers': ordered,
            'total_count': total_count,
            'iqr_multiplier': iqr_multiplier,
        })

    # ──────────────────────────────────────────────
    # Batch import routes
    # ──────────────────────────────────────────────

    @app.route('/api/import/batch', methods=['POST'])
    def api_import_batch():
        """Save a batch of shots from a parsed CSV preview.

        Accepts JSON:
          session_info: {filename, date, location, data_type}
          session_id:   null on first batch, reuse on subsequent batches
          shots:        [{swing_size, club, club_short, carry, ...}, ...]

        Returns {success, session_id, saved_count}.
        """
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON body'}), 400

        session_info = data.get('session_info', {})
        shots_list = data.get('shots', [])
        existing_session_id = data.get('session_id')

        if not shots_list:
            return jsonify({'error': 'No shots provided'}), 400

        # Reuse session or create a new one
        if existing_session_id:
            sess = Session.query.get(existing_session_id)
            if not sess:
                return jsonify({'error': f'Session {existing_session_id} not found'}), 404
        else:
            data_type = session_info.get('data_type', 'wedge')
            filename = session_info.get('filename', 'unknown.csv')
            location = session_info.get('location')

            date_str = session_info.get('date', '')
            session_date = None
            if date_str:
                for fmt in ('%m-%d-%Y', '%Y-%m-%d'):
                    try:
                        session_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue

            sess = Session(
                filename=filename,
                session_date=session_date,
                location=location,
                data_type=data_type,
                notes='',
            )
            db.session.add(sess)
            db.session.flush()

        for shot_data in shots_list:
            shot = Shot(
                session_id=sess.id,
                club=shot_data.get('club', ''),
                club_short=shot_data.get('club_short', ''),
                club_index=shot_data.get('club_index'),
                swing_size=shot_data.get('swing_size', 'full'),
                ball_speed=shot_data.get('ball_speed'),
                launch_direction=shot_data.get('launch_direction'),
                launch_direction_deg=shot_data.get('launch_direction_deg'),
                launch_angle=shot_data.get('launch_angle'),
                spin_rate=shot_data.get('spin_rate'),
                spin_axis=shot_data.get('spin_axis'),
                spin_axis_deg=shot_data.get('spin_axis_deg'),
                back_spin=shot_data.get('back_spin'),
                side_spin=shot_data.get('side_spin'),
                apex=shot_data.get('apex'),
                carry=shot_data.get('carry'),
                total=shot_data.get('total'),
                offline=shot_data.get('offline'),
                landing_angle=shot_data.get('landing_angle'),
                club_path=shot_data.get('club_path'),
                face_angle=shot_data.get('face_angle'),
                attack_angle=shot_data.get('attack_angle'),
                dynamic_loft=shot_data.get('dynamic_loft'),
                excluded=False,
            )
            db.session.add(shot)

        db.session.commit()
        return jsonify({
            'success': True,
            'session_id': sess.id,
            'saved_count': len(shots_list),
        })

    # ──────────────────────────────────────────────
    # JSON API routes
    # ──────────────────────────────────────────────

    @app.route('/api/club-matrix')
    def api_club_matrix():
        session_id = request.args.get('session_id', type=int)
        percentile = request.args.get('percentile', Config.DEFAULT_PERCENTILE, type=int)
        include_test = request.args.get('include_test', 'false').lower() == 'true'
        matrix = build_club_matrix(session_id=session_id, percentile=percentile, include_test=include_test)
        return jsonify({'percentile': percentile, 'session_id': session_id, 'matrix': matrix})

    @app.route('/api/wedge-matrix')
    def api_wedge_matrix():
        session_id = request.args.get('session_id', type=int)
        percentile = request.args.get('percentile', Config.DEFAULT_PERCENTILE, type=int)
        include_test = request.args.get('include_test', 'false').lower() == 'true'
        data = build_wedge_matrix(session_id=session_id, percentile=percentile, include_test=include_test)
        return jsonify({'percentile': percentile, 'session_id': session_id, **data})

    @app.route('/api/analytics/<chart_type>')
    def api_analytics(chart_type):
        session_id = request.args.get('session_id', type=int)
        club_raw = request.args.get('club', '')
        date_range = request.args.get('date_range', '')
        percentile = request.args.get('percentile', Config.DEFAULT_PERCENTILE, type=int)
        include_test = request.args.get('include_test', 'false').lower() == 'true'
        date_from = parse_date_range(date_range)

        # Parse comma-separated club list; None means "all clubs"
        clubs = [c.strip() for c in club_raw.split(',') if c.strip()] if club_raw else None

        if chart_type == 'dispersion':
            shots = dispersion_data(session_id=session_id, club_short=clubs, date_from=date_from)
            boundary = compute_dispersion_boundary(
                session_id=session_id, club_short=clubs,
                date_from=date_from, percentile=percentile,
            )
            return jsonify({'shots': shots, 'dispersion_boundary': boundary})
        elif chart_type == 'spin-carry':
            return jsonify(spin_vs_carry_data(session_id=session_id, club_short=clubs, date_from=date_from))
        elif chart_type == 'shot-shape':
            return jsonify(shot_shape_data(session_id=session_id, club_short=clubs, date_from=date_from))
        elif chart_type == 'carry-distribution':
            raw = carry_distribution(session_id=session_id, club_short=clubs, date_from=date_from, percentile=percentile)
            # Sort by CLUB_ORDER for consistent display
            ordered = {}
            for c in CLUB_ORDER:
                if c in raw:
                    ordered[c] = raw[c]
            for c in raw:
                if c not in ordered:
                    ordered[c] = raw[c]
            return jsonify(ordered)
        elif chart_type == 'club-comparison':
            # Box-and-whisker data with wedge sub-swing breakdown
            # Returns a list of dicts with both old fields and box plot stats
            all_shots = get_shots_query(
                session_id=session_id, club_short=clubs,
                excluded=False, date_from=date_from,
            ).all()

            # Detect which wedge clubs have multiple swing types
            wedge_swing_types = {}
            for s in all_shots:
                if s.club_short in WEDGE_CLUBS:
                    wedge_swing_types.setdefault(s.club_short, set()).add(s.swing_size)

            # Group: wedge with multiple swings → club+swing_size, else just club
            by_group = {}
            for s in all_shots:
                if s.club_short in WEDGE_CLUBS and len(wedge_swing_types.get(s.club_short, set())) > 1:
                    label = f'{s.club_short}-{s.swing_size}'
                else:
                    label = s.club_short
                by_group.setdefault(label, []).append(s)

            from services.analytics import _box_plot_stats
            entries = {}
            for label, group_shots in by_group.items():
                carries = [s.carry for s in group_shots if s.carry is not None]
                totals = [s.total for s in group_shots if s.total is not None]
                if len(carries) < 2:
                    continue
                box = _box_plot_stats(carries)
                entry = {
                    'club': label,
                    # Backward-compat fields
                    'carry_p75': round(float(np.percentile(carries, percentile)), 1) if carries else None,
                    'total_p75': round(float(np.percentile(totals, percentile)), 1) if totals else None,
                    'max_total': round(float(max(totals)), 1) if totals else None,
                    'shot_count': len(group_shots),
                }
                entry.update(box)
                entries[label] = entry

            # Sort: non-wedge in CLUB_ORDER, wedge sub-swings grouped
            result = []
            for c in CLUB_ORDER:
                if c in WEDGE_CLUBS and len(wedge_swing_types.get(c, set())) > 1:
                    for sw in SWING_SIZES:
                        key = f'{c}-{sw}'
                        if key in entries:
                            result.append(entries.pop(key))
                    for key in list(entries.keys()):
                        if key.startswith(f'{c}-'):
                            result.append(entries.pop(key))
                else:
                    if c in entries:
                        result.append(entries.pop(c))
            # Any remaining
            for key in entries:
                result.append(entries[key])
            return jsonify(result)
        elif chart_type == 'loft-analysis':
            return jsonify(analyze_loft(session_id=session_id, club_short=clubs, date_from=date_from))
        elif chart_type == 'loft-summary':
            raw = loft_summary(session_id=session_id, date_from=date_from)
            ordered = {}
            for c in CLUB_ORDER:
                if c in raw:
                    ordered[c] = raw[c]
            for c in raw:
                if c not in ordered:
                    ordered[c] = raw[c]
            return jsonify(ordered)
        elif chart_type == 'errant-flags':
            if session_id is None:
                return jsonify({'error': 'session_id required'}), 400
            flagged = flag_errant_shots(session_id)
            return jsonify({'flagged_ids': flagged, 'count': len(flagged)})
        elif chart_type == 'launch-spin-stability':
            return jsonify(launch_spin_stability(session_id=session_id, club_short=clubs, date_from=date_from, percentile=percentile))
        elif chart_type == 'radar-comparison':
            return jsonify(radar_comparison(session_id=session_id, club_short=clubs, date_from=date_from, percentile=percentile))
        else:
            return jsonify({'error': f'Unknown chart type: {chart_type}'}), 404

    @app.route('/api/shots')
    def api_shots():
        """Paginated shots API with multi-club and date range filtering.

        Query params:
            session_id: optional session filter.
            club: optional comma-separated club filter.
            swing_size: optional swing size filter.
            date_range: optional date range (7/30/60/90).
            include_hidden: include excluded shots (default false).
            include_test: include test sessions (default false).
            page: page number (default 1).
            per_page: results per page (default 50, max 200).
        """
        session_id = request.args.get('session_id', type=int)
        club_raw = request.args.get('club', '')
        swing_size = request.args.get('swing_size')
        date_range = request.args.get('date_range', '')
        include_hidden = request.args.get('include_hidden', 'false').lower() == 'true'
        include_test = request.args.get('include_test', 'false').lower() == 'true'
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        date_from = parse_date_range(date_range)

        q = Shot.query
        needs_session_join = False

        if date_from is not None or (not include_test and not session_id):
            needs_session_join = True
            q = q.join(Session)
            if date_from is not None:
                q = q.filter(Session.session_date >= date_from)
            if not include_test and not session_id:
                q = q.filter(Session.is_test == False)

        if session_id:
            q = q.filter(Shot.session_id == session_id)

        club_list = [c.strip() for c in club_raw.split(',') if c.strip()] if club_raw else []
        if club_list:
            q = q.filter(Shot.club_short.in_(club_list))
        if swing_size:
            q = q.filter(Shot.swing_size == swing_size)
        if not include_hidden:
            q = q.filter(Shot.excluded == False)

        total_count = q.count()
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        shots = q.order_by(
            Shot.session_id, Shot.club_short, Shot.club_index
        ).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            'shots': [s.to_dict() for s in shots],
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages,
        })

    @app.route('/api/lofts', methods=['POST'])
    def api_update_lofts():
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON body'}), 400

        updated = []
        for club_short, loft_value in data.items():
            loft = ClubLoft.query.get(club_short)
            if loft:
                loft.standard_loft = float(loft_value)
                updated.append(club_short)
            else:
                new_loft = ClubLoft(club_short=club_short, standard_loft=float(loft_value))
                db.session.add(new_loft)
                updated.append(club_short)

        db.session.commit()
        return jsonify({'updated': updated})

    @app.route('/api/sessions')
    def api_sessions():
        include_test = request.args.get('include_test', 'false').lower() == 'true'
        q = Session.query
        if not include_test:
            q = q.filter(Session.is_test == False)
        sessions = q.order_by(Session.imported_at.desc()).all()
        return jsonify([s.to_dict() for s in sessions])

    @app.route('/api/lofts', methods=['GET'])
    def api_get_lofts():
        lofts = ClubLoft.query.all()
        return jsonify([l.to_dict() for l in lofts])


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

app = create_app()

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, port=5000)
