from fastapi import APIRouter, HTTPException, BackgroundTasks
import multiprocessing
from datetime import datetime
from pathlib import Path

from app.models import AgentResult, ErrorResult
from app.agent import run_agent_task
from app.models import AgentRequest

import json

router = APIRouter()

@router.post("/api/agent/run")
async def run_agent(request: AgentRequest, background_tasks: BackgroundTasks):
    """
    POST API to run the agent for multiple users
    """
    
    try:
        # Start agent in background process with the full user_creds array
        process = multiprocessing.Process(
            target=run_agent_task,
            args=(request.user_creds[0], request.signin_url, request.billing_history_url)  # one user at a time
        )
        process.start()
        
        # Update status
        # agent_status["running"] = True
        # agent_status["process"] = process
        
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

@router.post("/api/agent/results")
async def store_agent_results(result: AgentResult):
    """
    POST API to store agent results
    """
    try:
        # Store the result locally
        result_data = {
            "pdf_content": result.pdf_content,
            "user_creds": result.user_creds,
            "timestamp": result.timestamp
        }
        
        # For now, we'll just print a message
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"✅ Bills for {result.user_creds.get('username', 'unknown')} at {timestamp} have been received and ready for upload")
        
        return {
            "message": "Agent results received (not stored locally)",
            "user": result.user_creds.get("username", "unknown"),
            "timestamp": result.timestamp
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store results: {str(e)}")

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
    check_and_update_agent_status()
    
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