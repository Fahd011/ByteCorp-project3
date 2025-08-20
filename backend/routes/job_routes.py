from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.models import ImportSession, ImportResult, User
from db.db import db
from azure_storage_client import upload_csv_to_supabase, get_csv_public_url, get_bills_bucket_public_url, download_from_bills_bucket
from agent_runner import run_agent_for_job_async, stop_agent_job
from datetime import datetime
from scheduler import scheduler
from scheduled_jobs import run_scheduled_job

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
            'results_count': len(results),
            # Add scheduling information
            'is_scheduled': session.is_scheduled,
            'schedule_type': session.schedule_type,
            'schedule_config': session.schedule_config,
            'next_run': session.next_run.isoformat() if session.next_run else None,
            'last_scheduled_run': session.last_scheduled_run.isoformat() if session.last_scheduled_run else None
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
    
    # Get scheduling parameters
    is_scheduled = request.form.get('is_scheduled', 'false').lower() == 'true'
    schedule_type = request.form.get('schedule_type')
    schedule_config = request.form.get('schedule_config')
    
    # Debug logging
    print(f"[DEBUG] Received scheduling data:")
    print(f"  is_scheduled: {is_scheduled}")
    print(f"  schedule_type: {schedule_type}")
    print(f"  schedule_config: {schedule_config}")
    print(f"  All form data: {dict(request.form)}")
    
    if not login_url or not billing_url:
        return jsonify({'error': 'login_url and billing_url required'}), 400
    
    # Create a unique filename using timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{user_id}/{timestamp}_{csv_file.filename}"
    csv_url = upload_csv_to_supabase(csv_file, filename)
    
    # Parse schedule_config if it's a string
    if schedule_config and isinstance(schedule_config, str):
        import json
        try:
            schedule_config = json.loads(schedule_config)
            print(f"[DEBUG] Parsed schedule_config: {schedule_config}")
        except json.JSONDecodeError:
            print(f"[DEBUG] Failed to parse schedule_config: {schedule_config}")
            return jsonify({'error': 'Invalid schedule_config format'}), 400
    
    # Create the session with scheduling fields
    session = ImportSession(
        user_id=user_id, 
        csv_url=csv_url, 
        login_url=login_url, 
        billing_url=billing_url, 
        status='idle',
        is_scheduled=is_scheduled,
        schedule_type=schedule_type if is_scheduled else None,
        schedule_config=schedule_config if is_scheduled else None
    )
    
    print(f"[DEBUG] Creating session with scheduling:")
    print(f"  is_scheduled: {session.is_scheduled}")
    print(f"  schedule_type: {session.schedule_type}")
    print(f"  schedule_config: {session.schedule_config}")
    
    db.session.add(session)
    db.session.commit()
    
    # If job is scheduled, add it to the scheduler
    if is_scheduled and schedule_type and schedule_config:
        print(f"[DEBUG] Attempting to schedule job {session.id}")
        
        # Import the Flask app instance directly to avoid context issues
        from app import app
        
        # Create a wrapper function that passes the app instance directly
        def run_job_wrapper(job_id):
            run_scheduled_job(job_id, app)
        
        schedule_success = scheduler.schedule_job(session.id, {
            'schedule_type': schedule_type,
            'schedule_config': schedule_config
        }, run_job_wrapper)
        
        if schedule_success:
            print(f"[DEBUG] Job scheduled successfully")
            # Calculate next run time
            next_run = scheduler.calculate_next_run(schedule_type, schedule_config)
            if next_run:
                session.next_run = next_run
                db.session.commit()
                print(f"[DEBUG] Next run time set to: {next_run}")
        else:
            print(f"[DEBUG] Failed to schedule job")
    else:
        print(f"[DEBUG] Job not scheduled - conditions not met:")
        print(f"  is_scheduled: {is_scheduled}")
        print(f"  schedule_type: {schedule_type}")
        print(f"  schedule_config: {schedule_config}")
    
    return jsonify({
        'id': session.id, 
        'csv_url': csv_url, 
        'login_url': login_url, 
        'billing_url': billing_url, 
        'status': session.status,
        'created_at': session.created_at.isoformat(),
        'results_count': 0,
        'is_scheduled': is_scheduled,
        'schedule_type': schedule_type if is_scheduled else None,
        'schedule_config': schedule_config if is_scheduled else None,
        'next_run': session.next_run.isoformat() if session.next_run else None
    }), 201

@bp.route('/jobs/<session_id>/run', methods=['POST'])
@jwt_required()
def run_job(session_id):
    print(f"[ROUTE] Starting run_job for session {session_id}")
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    if session.status == 'running':
        return jsonify({'error': 'Job already running'}), 400
    
    print(f"[ROUTE] Updating status to running for session {session_id}")
    # Update status to running immediately
    session.status = 'running'
    db.session.commit()
    
    print(f"[ROUTE] Calling run_agent_for_job_async for session {session_id}")
    # Start the agent in background
    run_agent_for_job_async(session_id)
    
    print(f"[ROUTE] Async function called, preparing response for session {session_id}")
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
    print(f"[ROUTE] Returning response for session {session_id}")
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
            'file_url': r.file_url,
            'retry_attempts': r.retry_attempts,
            'final_error': r.final_error,
            'created_at': r.created_at.isoformat() if r.created_at else None
        }
        # Add proxy URL for successful results with file URLs
        if r.status == 'success' and r.file_url:
            result_data['proxy_url'] = f"/api/jobs/{session_id}/bills/{r.id}/view"
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
        # Return proxy URL instead of direct Azure URL since storage is not public
        proxy_url = f"/api/jobs/{session_id}/credentials/view"
        
        return jsonify({
            'csv_url': proxy_url,
            'filename': session.csv_url.split('/')[-1] if session.csv_url else 'credentials.csv'
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get credentials URL: {str(e)}'}), 500

@bp.route('/jobs/<session_id>/credentials/view', methods=['GET'])
@jwt_required()
def view_credentials_csv(session_id):
    """Proxy endpoint to serve CSV with proper headers for browser viewing"""
    user_id = get_jwt_identity()
    session = ImportSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    if not session.csv_url:
        return jsonify({'error': 'No credentials file found for this job'}), 404
    
    try:
        # Download the CSV from Azure Storage using the storage key
        from azure_storage_client import download_file_from_azure
        
        print(f"[PROXY] Downloading CSV for session {session_id}")
        print(f"[PROXY] Azure URL: {session.csv_url}")
        
        # Download file content from Azure
        file_content = download_file_from_azure(session.csv_url)
        
        if not file_content:
            return jsonify({'error': 'Failed to download file from Azure'}), 500
        
        print(f"[PROXY] Successfully downloaded CSV, size: {len(file_content)} bytes")
        
        # Return the CSV with proper headers for browser viewing
        from flask import Response
        return Response(
            file_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'inline; filename=credentials.csv',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        
    except Exception as e:
        print(f"[PROXY] Error serving CSV: {str(e)}")
        return jsonify({'error': f'Failed to serve CSV: {str(e)}'}), 500

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
            'file_url': r.file_url,
            'retry_attempts': r.retry_attempts,
            'final_error': r.final_error
        }
        # Add proxy URL for successful results with file URLs
        if r.status == 'success' and r.file_url:
            result_data['proxy_url'] = f"/api/jobs/{session_id}/bills/{r.id}/view"
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
            
            # Generate proxy URL for secure access
            try:
                proxy_url = f"/api/jobs/{session_id}/bills/{result.id}/view"
                
                bill_data = {
                    'id': result.id,
                    'filename': filename,
                    'email': result.email,
                    'uploaded_at': result.created_at.isoformat() if result.created_at else None,
                    'file_size': None,  # Not stored in ImportResult
                    'status': 'uploaded',
                    'download_url': proxy_url
                }
                bills.append(bill_data)
            except Exception as e:
                print(f"Error generating proxy URL for {filename}: {e}")
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
        
        # Download the file from Azure Storage
        print(f"[PROXY] Downloading from Azure Storage...")
        from azure_storage_client import download_file_from_azure
        response = download_file_from_azure(result.file_url)
        
        if not response:
            print(f"[PROXY] Azure download returned empty response")
            return jsonify({'error': 'Failed to download file from Azure'}), 500
        
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
