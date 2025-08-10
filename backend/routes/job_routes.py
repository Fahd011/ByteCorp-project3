from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.models import ImportSession, ImportResult, User
from db import db
from supabase_client import upload_csv_to_supabase, get_csv_public_url, supabase
from agent_runner import run_agent_for_job, stop_agent_job
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
    return jsonify({
        'id': session.id, 
        'csv_url': csv_url, 
        'login_url': login_url, 
        'billing_url': billing_url, 
        'status': session.status,
        'created_at': session.created_at.isoformat(),
        'results_count': 0
    }), 201

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
    output = []
    for r in results:
        result_data = {
            'id': r.id,
            'email': r.email,
            'status': r.status,
            'error': r.error,
            'file_url': r.file_url
        }
        # Add proxy URL for successful results with file URLs
        if r.status == 'success' and r.file_url:
            result_data['proxy_url'] = f"/jobs/{session_id}/bills/{r.id}/view"
        output.append(result_data)
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

@bp.route('/jobs/<session_id>/results', methods=['DELETE'])
@jwt_required()
def delete_all_results(session_id):
    """Delete all results for a specific job"""
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    try:
        # Delete all results for this session
        deleted_count = ImportResult.query.filter_by(session_id=session_id).delete()
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully deleted {deleted_count} results',
            'deleted_count': deleted_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete results: {str(e)}'}), 500

@bp.route('/jobs/<session_id>/results/<result_id>', methods=['DELETE'])
@jwt_required()
def delete_single_result(session_id, result_id):
    """Delete a single result for a specific job"""
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    result = ImportResult.query.filter_by(id=result_id, session_id=session_id).first()
    if not result:
        return jsonify({'error': 'Result not found'}), 404
    
    try:
        # Delete the specific result
        db.session.delete(result)
        db.session.commit()
        
        return jsonify({
            'message': 'Result deleted successfully',
            'deleted_result_id': result_id
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete result: {str(e)}'}), 500

@bp.route('/jobs/<session_id>/credentials', methods=['GET'])
@jwt_required()
def get_job_credentials(session_id):
    """Get the credentials file URL for a specific job"""
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    if not session.csv_url:
        return jsonify({'error': 'No credentials file found for this job'}), 404
    
    try:
        # Get the public URL for the CSV file
        csv_public_url = get_csv_public_url(session.csv_url)
        
        return jsonify({
            'csv_url': csv_public_url,
            'filename': session.csv_url.split('/')[-1] if session.csv_url else 'credentials.csv'
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get credentials URL: {str(e)}'}), 500

@bp.route('/jobs/<session_id>/realtime', methods=['GET'])
@jwt_required()
def get_job_realtime_status(session_id):
    """Get real-time status and results for a job"""
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Get results from database
    results = ImportResult.query.filter_by(session_id=session_id).all()
    
    # Format results for frontend
    output = []
    for r in results:
        result_data = {
            'id': r.id,
            'email': r.email,
            'status': r.status,
            'error': r.error,
            'file_url': r.file_url
        }
        # Add proxy URL for successful results with file URLs
        if r.status == 'success' and r.file_url:
            result_data['proxy_url'] = f"/jobs/{session_id}/bills/{r.id}/view"
        output.append(result_data)
    
    return jsonify({
        'id': session.id,
        'status': session.status,
        'results_count': len(results),
        'output': output
    }), 200

@bp.route('/jobs/<session_id>/bills', methods=['GET'])
@jwt_required()
def get_job_bills(session_id):
    """Get all bills (PDFs) for a specific job"""
    user_id = get_jwt_identity()
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Get all successful results with file URLs
    results = ImportResult.query.filter_by(
        session_id=session_id, 
        status='success'
    ).filter(ImportResult.file_url.isnot(None)).all()
    
    bills = []
    for result in results:
        if result.file_url:
            # Extract filename from the file_url for display
            import urllib.parse
            parsed = urllib.parse.urlparse(result.file_url)
            path_parts = parsed.path.split('/')
            
            # Find the bills bucket path and extract filename
            bills_index = path_parts.index('bills') if 'bills' in path_parts else -1
            if bills_index != -1:
                filename = '/'.join(path_parts[bills_index + 1:])
            else:
                filename = result.file_url.split('/')[-1]  # Fallback
            
            # Generate download URL from Supabase storage
            try:
                # Extract the file path from the Supabase URL
                file_path = '/'.join(path_parts[bills_index + 1:]) if bills_index != -1 else filename
                download_url = supabase.storage.from_('bills').get_public_url(file_path)
                
                bill_data = {
                    'id': result.id,
                    'filename': filename,
                    'email': result.email,
                    'uploaded_at': result.created_at.isoformat() if result.created_at else None,
                    'file_size': None,  # Not stored in ImportResult
                    'status': 'uploaded',
                    'download_url': download_url
                }
                bills.append(bill_data)
            except Exception as e:
                print(f"Error generating download URL for {filename}: {e}")
                # Add bill without download URL
                bill_data = {
                    'id': result.id,
                    'filename': filename,
                    'email': result.email,
                    'uploaded_at': result.created_at.isoformat() if result.created_at else None,
                    'file_size': None,
                    'status': 'uploaded',
                    'download_url': None
                }
                bills.append(bill_data)
    
    return jsonify({
        'session_id': session_id,
        'total_bills': len(bills),
        'bills': bills
    }), 200

@bp.route('/jobs/<session_id>/bills/<result_id>/view', methods=['GET'])
@jwt_required()
def view_bill_pdf(session_id, result_id):
    """Proxy endpoint to serve PDF with proper headers for browser viewing"""
    user_id = get_jwt_identity()
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    result = ImportResult.query.filter_by(
        id=result_id, 
        session_id=session_id,
        status='success'
    ).first()
    
    if not result or not result.file_url:
        return jsonify({'error': 'Bill not found'}), 404
    
    print(f"[PROXY] Serving PDF for result {result_id}, file_url: {result.file_url}")
    
    try:
        # Download the PDF from Supabase
        from supabase_client import supabase
        import urllib.parse
        
        # Extract the file path from the Supabase URL
        parsed = urllib.parse.urlparse(result.file_url)
        path_parts = parsed.path.split('/')
        
        print(f"[PROXY] Parsed URL path parts: {path_parts}")
        
        # Find the bills bucket path
        bills_index = path_parts.index('bills') if 'bills' in path_parts else -1
        if bills_index == -1:
            print(f"[PROXY] Error: 'bills' not found in path parts")
            return jsonify({'error': 'Invalid file URL'}), 400
        
        # Get the file path after 'bills'
        file_path = '/'.join(path_parts[bills_index + 1:])
        print(f"[PROXY] Extracted file path: {file_path}")
        
        # Download the file from Supabase
        print(f"[PROXY] Downloading from Supabase bills bucket...")
        response = supabase.storage.from_('bills').download(file_path)
        
        if hasattr(response, 'error') and response.error:
            print(f"[PROXY] Supabase download error: {response.error}")
            return jsonify({'error': f'Failed to download file: {response.error}'}), 500
        
        print(f"[PROXY] Successfully downloaded PDF, size: {len(response) if response else 'unknown'} bytes")
        
        # Return the PDF with proper headers for browser viewing
        from flask import Response
        return Response(
            response,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': 'inline; filename=bill.pdf',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        
    except Exception as e:
        print(f"[PROXY] Exception occurred: {str(e)}")
        return jsonify({'error': f'Failed to serve PDF: {str(e)}'}), 500
