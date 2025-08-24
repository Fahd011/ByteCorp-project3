from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import multiprocessing
from datetime import datetime
from pathlib import Path

from app.db import SessionLocal
from app.models import AgentRequest, AgentResult, ErrorResult, UserBillingCredential
from app.agent import run_agent_task

# Import Azure storage service
from azure_storage_service import azure_storage_service
from typing import Optional

import json
import io

router = APIRouter()

@router.post("/api/agent/run")
async def run_agent(request: AgentRequest, background_tasks: BackgroundTasks):
    """
    POST API to run the agent for multiple users
    """
    
    try:
        if request.user_creds:
            first_user = request.user_creds[0]
            print(f"[INFO] First user ----> username: {first_user['username']}, password: {first_user['password']}")
            
            # # Start agent in background process with the full user_creds array
            process = multiprocessing.Process(
                target=run_agent_task,
                args=(first_user, request.signin_url, request.billing_history_url)  # one user at a time
            )
            process.start()
            
            return {
                "message": f"Agent started successfully for {len(request.user_creds)} users",
                "status": "running",
                "total_users": len(request.user_creds),
                "users": [creds.get("username", "unknown") for creds in request.user_creds],
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")

@router.post("/api/agent/stop")
async def stop_agent():
    """
    POST API to stop the agent with force kill of all browser processes
    """
    return {
        "message": "Stop agent functionality not implemented yet",
        "status": "not_implemented",
    }

@router.post("/api/agent/error")
async def store_agent_error(error: ErrorResult):
    """
    POST API to store agent errors
    """
    try:
        # Store the error locally
        error_data = {
            "error_message": error.error_message,
            "user_creds": error.user_creds,
            "timestamp": error.timestamp,
            "traceback": error.traceback
        }
        
        store_error_result_locally(error_data)
        
        return {
            "message": "Agent error stored successfully",
            "user": error.user_creds.get("username", "unknown"),
            "timestamp": error.timestamp
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store error: {str(e)}")

@router.get("/api/agent/health")
async def health_check():
    """
    Health test API to check if FastAPI is responsive
    """
    # Check and update agent status
    # check_and_update_agent_status()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_status": "dummy",  # Placeholder, replace with actual status if needed
        "message": "FastAPI is running and responsive"
    }

@router.get("/api/agent/status")
async def get_agent_status():
    """
    GET API to check detailed agent status
    """
    # Check and update agent status
    # check_and_update_agent_status()
    
    return {
        "running": "dummy",  # Placeholder, replace with actual status if needed
        "stop_requested": "dummy",  # Placeholder, replace with actual status if needed
        "timestamp": datetime.now().isoformat()
    }

@router.get("/api/azure/list")
async def list_azure_blobs(prefix: Optional[str] = None):
    """
    List blobs in Azure container with proper JSON structure.
    """
    try:
        blobs = azure_storage_service.list_blobs(prefix)

        blob_urls = [
            {
                "name": blob_name,
                "url": azure_storage_service.get_blob_url(blob_name),  # direct Azure URL
                "download_url": f"/api/azure/download/{blob_name}"     # your API endpoint for downloading
            }
            for blob_name in blobs
        ]

        return {
            "success": True,
            "count": len(blob_urls),
            "blobs": blob_urls
        }

    except Exception as e:
        print(f"❌ Error listing blobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": f"Failed to list blobs: {str(e)}"}
        )
        
        
@router.delete("/api/azure/delete-all")
async def delete_all_azure_blobs():
    """
    Delete ALL blobs in Azure container (⚠️ irreversible).
    """
    try:
        blobs = azure_storage_service.list_blobs()

        if not blobs:
            return {
                "success": True,
                "deleted_count": 0,
                "message": "Container is already empty"
            }

        deleted = []
        errors = []

        for blob_name in blobs:
            try:
                azure_storage_service.delete_blob(blob_name)
                deleted.append(blob_name)
            except Exception as e:
                errors.append({"name": blob_name, "error": str(e)})

        return {
            "success": len(errors) == 0,
            "deleted_count": len(deleted),
            "deleted": deleted,
            "errors": errors
        }

    except Exception as e:
        print(f"❌ Error deleting all blobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": f"Failed to delete blobs: {str(e)}"}
        )


@router.get("/api/azure/download/{blob_name:path}")
async def download_pdf_from_azure(blob_name: str):
    """
    Download PDF from Azure Blob Storage
    
    Args:
        blob_name: Name of the blob to download (can include path)
    """
    try:
        print(f"🔍 Downloading PDF from Azure: {blob_name}")
        
        # Download PDF from Azure
        success, pdf_content = azure_storage_service.download_pdf_from_azure(blob_name)
        
        if success:
            # Generate filename from blob name
            filename = blob_name.split('/')[-1]  # Get the last part of the path
            
            print(f"✅ PDF downloaded successfully: {filename}")
            
            # Return PDF as file response
            return FileResponse(
                io.BytesIO(pdf_content),
                media_type='application/pdf',
                filename=filename,
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )
        else:
            raise HTTPException(status_code=404, detail="PDF not found in Azure storage")
            
    except Exception as e:
        print(f"❌ Error downloading PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download PDF: {str(e)}")


# Create bills directory if it doesn't exist
BILLS_DIR = Path("bills")
BILLS_DIR.mkdir(exist_ok=True)

def store_error_result_locally(error_data: dict):
    """
    Store error results locally
    """
    try:
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = error_data["user_creds"].get("username", "unknown")
        filename = f"error_{username}_{timestamp}.json"
        
        # Save to bills directory
        filepath = BILLS_DIR / filename
        with open(filepath, 'w') as f:
            json.dump(error_data, f, indent=2)
        
        print(f"❌ Error for {username} at {timestamp} has been saved")
        print(f"📁 Error file saved to: {filepath}")
        
    except Exception as e:
        print(f"Error storing error result: {str(e)}")
        
        
