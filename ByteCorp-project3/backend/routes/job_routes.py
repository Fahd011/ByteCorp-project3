from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.models import ImportSession, ImportResult, User
from backend.db import db
from backend.supabase_client import upload_csv_to_supabase
from backend.agent_runner import run_agent_for_job, stop_agent_job
from datetime import datetime

bp = Blueprint("jobs", __name__)


@bp.route('/jobs', methods=['GET'])
@jwt_required()
def get_all_jobs():
    user_id = get_jwt_identity()
    sessions = ImportSession.query.filter_by(user_id=user_id).order_by(ImportSession.created_at.desc()).all()
    jobs = []
    for session in sessions:
        results = ImportResult.query.filter_by(session_id=session.id).all()
        job_data = {
            'id': session.id,
            'csv_url': session.csv_url,
            'login_url': session.login_url,
            'billing_url': session.billing_url,
            'status': session.status,
            'created_at': session.created_at.isoformat(),
            'results_count': len(results)
        }
        jobs.append(job_data)
    return jsonify(jobs), 200

@bp.route('/jobs', methods=['POST'])
@jwt_required()
def create_job():
    user_id = get_jwt_identity()
    if 'csv' not in request.files:
        return jsonify({'error': 'CSV file required'}), 400
    csv_file = request.files['csv']
    login_url = request.form.get('login_url')
    billing_url = request.form.get('billing_url')
    if not login_url or not billing_url:
        return jsonify({'error': 'login_url and billing_url required'}), 400
    # Create a unique filename using timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{user_id}/{timestamp}_{csv_file.filename}"
    csv_url = upload_csv_to_supabase(csv_file, filename)
    session = ImportSession(user_id=user_id, csv_url=csv_url, login_url=login_url, billing_url=billing_url, status='idle')
    db.session.add(session)
    db.session.commit()
    return jsonify({'id': session.id, 'csv_url': csv_url, 'login_url': login_url, 'billing_url': billing_url, 'status': session.status}), 201

@bp.route('/jobs/<session_id>/run', methods=['POST'])
@jwt_required()
def run_job(session_id):
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    if session.status == 'running':
        return jsonify({'error': 'Job already running'}), 400
    
    # Update status to running immediately
    session.status = 'running'
    db.session.commit()
    
    # Start the agent in background
    run_agent_for_job(session_id)
    
    # Return updated job data
    results = ImportResult.query.filter_by(session_id=session_id).all()
    job_data = {
        'id': session.id,
        'csv_url': session.csv_url,
        'login_url': session.login_url,
        'billing_url': session.billing_url,
        'status': session.status,
        'created_at': session.created_at.isoformat(),
        'results_count': len(results)
    }
    return jsonify(job_data), 200

@bp.route('/jobs/<session_id>/stop', methods=['POST'])
@jwt_required()
def stop_job(session_id):
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Try to stop the running process
    if stop_agent_job(session_id):
        session.status = 'stopped'
        db.session.commit()
        message = 'Process terminated successfully'
    else:
        session.status = 'stopped'
        db.session.commit()
        message = 'No running process found'
    
    # Return updated job data
    results = ImportResult.query.filter_by(session_id=session_id).all()
    job_data = {
        'id': session.id,
        'csv_url': session.csv_url,
        'login_url': session.login_url,
        'billing_url': session.billing_url,
        'status': session.status,
        'created_at': session.created_at.isoformat(),
        'results_count': len(results)
    }
    return jsonify(job_data), 200

@bp.route('/jobs/<session_id>', methods=['DELETE'])
@jwt_required()
def delete_job(session_id):
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    try:
        # Stop any running process first
        stop_agent_job(session_id)
        
        # Delete all associated results first
        ImportResult.query.filter_by(session_id=session_id).delete()
        
        # Then delete the session
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({'message': 'Job and associated results deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete job: {str(e)}'}), 500

@bp.route('/jobs/<session_id>', methods=['GET'])
@jwt_required()
def get_job(session_id):
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    results = ImportResult.query.filter_by(session_id=session_id).all()
    return jsonify({
        'id': session.id,
        'csv_url': session.csv_url,
        'login_url': session.login_url,
        'billing_url': session.billing_url,
        'status': session.status,
        'created_at': session.created_at.isoformat(),
        'results_count': len(results)
    }), 200

@bp.route('/jobs/<session_id>/details', methods=['GET'])
@jwt_required()
def get_job_details(session_id):
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    results = ImportResult.query.filter_by(session_id=session_id).all()
    output = [
        {
            'email': r.email,
            'status': r.status,
            'error': r.error,
            'filename': r.file_url
        } for r in results
    ]
    return jsonify({
        'id': session.id,
        'csv_url': session.csv_url,
        'login_url': session.login_url,
        'billing_url': session.billing_url,
        'status': session.status,
        'created_at': session.created_at.isoformat(),
        'results_count': len(results),
        'output': output
    }), 200
