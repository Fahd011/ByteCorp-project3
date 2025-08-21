from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import multiprocessing
import os
import json
from datetime import datetime
from typing import Optional
import traceback
import requests
from pathlib import Path
import asyncio
import uuid
from browser_use.llm import ChatOpenAI
from browser_use import Agent
from browser_use.browser import BrowserSession, BrowserProfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="GPT Web Scraper API", version="1.0.0")

# Data models
class AgentRequest(BaseModel):
    user_creds: dict
    signin_url: str
    billing_history_url: str

class AgentResult(BaseModel):
    pdf_content: bytes
    user_creds: dict
    timestamp: str

class ErrorResult(BaseModel):
    error_message: str
    user_creds: dict
    timestamp: str
    traceback: str

# Global variables to track agent status
agent_status = {"running": False, "process": None, "stop_requested": False}
MAX_RETRIES = 3

# Create bills directory if it doesn't exist
BILLS_DIR = Path("bills")
BILLS_DIR.mkdir(exist_ok=True)

# Initialize LLM
llm = ChatOpenAI(model="gpt-4.1-mini")

def run_agent_task(user_creds: dict, signin_url: str, billing_history_url: str):
    """
    Agent runner function that executes the web scraping task using browser-use
    """
    max_attempts = 5
    current_attempt = 1
    
    while current_attempt <= max_attempts:
        try:
            print(f"Agent attempt {current_attempt}/{max_attempts} for user: {user_creds.get('username', 'unknown')}")
            
            # Check if stop was requested
            if agent_status.get("stop_requested", False):
                print(f"Agent stop requested for user: {user_creds.get('username', 'unknown')}")
                return
            
            # Create unique profile path for this session
            unique_profile_path = f'/tmp/browser_profiles/{uuid.uuid4()}'
            os.makedirs(unique_profile_path, exist_ok=True)
            
            # Create browser session with bills folder as downloads path
            browser_session = BrowserSession(
                browser_profile=BrowserProfile(
                    downloads_path=str(BILLS_DIR),  # Downloads go directly to bills folder
                    user_data_dir=unique_profile_path,
                )
            )
            
            # Check stop again before creating agent
            if agent_status.get("stop_requested", False):
                print(f"Agent stop requested before creating agent for user: {user_creds.get('username', 'unknown')}")
                return
            
            # Create the agent with the actual task
            agent = Agent(
                task=f"""
1. Go to {signin_url}.
2. Log in using:
   - Email: {user_creds.get('username')}
   - Password: {user_creds.get('password')}
3. After successful login, go to "Billing and Payment Activity".
   - If unsure, navigate directly to {billing_history_url}.
4. On the billing history page:
   - Find the first "View Bill" button.
   - Click it to download the bill (the download may happen silently).
5. Wait at least 5 seconds after clicking to ensure the download is triggered.
6. Now, go to the top right corner of the page.
   - Click the user icon (showing {user_creds.get('username')}).
   - Select "Sign out" from the dropdown.
7. Confirm that you are signed out:
   - You should be redirected to the **main homepage**.
   - After reaching the homepage and confirming logout, do not click or navigate anywhere. 
     The task is finished. Do not revisit any links or pages after logout. Do not open new tabs.
8. If you see a page that says "Something went wrong", stop the task.

Important:
- Do not revisit the billing history page after logout.
- Do not click on "Pay My Bill" or similar options.
- If no elements are interactable, wait 5 seconds — the page might still be loading. Repeat until page has loaded
- Only download 1 pdf. Never more than 1
""",
                llm=llm,
                browser_session=browser_session,
                headless=True,
            )
            
            # Check stop again before running
            if agent_status.get("stop_requested", False):
                print(f"Agent stop requested before running for user: {user_creds.get('username', 'unknown')}")
                return
            
            # Run the agent
            print(f"Starting browser automation for user: {user_creds.get('username', 'unknown')} (Attempt {current_attempt})")
            
            # Run the async agent in the current thread
            result = asyncio.run(agent.run())
            
            # Check if stop was requested during execution
            if agent_status.get("stop_requested", False):
                print(f"Agent stop requested during execution for user: {user_creds.get('username', 'unknown')}")
                return
            
            print(f"Agent completed successfully for user: {user_creds.get('username', 'unknown')} on attempt {current_attempt}")
            print(f"Result: {result}")
            
            # Print success message as requested
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            username = user_creds.get('username', 'unknown')
            print(f"✅ Bills for {username} at {timestamp} have been received and ready for upload")
            
            # Clean up the profile directory
            try:
                import shutil
                shutil.rmtree(unique_profile_path)
                print(f"Cleaned up profile directory: {unique_profile_path}")
            except Exception as cleanup_error:
                print(f"Warning: Could not clean up profile directory: {cleanup_error}")
            
            # Success! Exit the retry loop
            break
            
        except Exception as e:
            print(f"Agent attempt {current_attempt} failed for user: {user_creds.get('username', 'unknown')} with error: {str(e)}")
            
            # Clean up the profile directory on error
            try:
                if 'unique_profile_path' in locals():
                    import shutil
                    shutil.rmtree(unique_profile_path)
                    print(f"Cleaned up profile directory after error: {unique_profile_path}")
            except Exception as cleanup_error:
                print(f"Warning: Could not clean up profile directory after error: {cleanup_error}")
            
            # If this was the last attempt, store the final error
            if current_attempt == max_attempts:
                print(f"All {max_attempts} attempts failed for user: {user_creds.get('username', 'unknown')}")
                
                # Handle errors and store error information
                error_data = {
                    "error_message": f"Failed after {max_attempts} attempts. Last error: {str(e)}",
                    "user_creds": user_creds,
                    "timestamp": datetime.now().isoformat(),
                    "traceback": traceback.format_exc(),
                    "attempts_made": max_attempts,
                    "status": "failed"
                }
                
                store_error_result_locally(error_data)
            else:
                # Wait a bit before retrying (exponential backoff)
                wait_time = min(2 ** current_attempt, 30)  # Max 30 seconds wait
                print(f"Waiting {wait_time} seconds before retry...")
                import time
                time.sleep(wait_time)
            
            current_attempt += 1
    
    # Update status when done (moved outside the while loop)
    agent_status["running"] = False
    agent_status["process"] = None
    agent_status["stop_requested"] = False


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

@app.post("/api/agent/run")
async def run_agent(request: AgentRequest, background_tasks: BackgroundTasks):
    """
    POST API to run the agent
    """
    if agent_status["running"]:
        raise HTTPException(status_code=400, detail="Agent is already running")
    
    try:
        # Start agent in background process
        process = multiprocessing.Process(
            target=run_agent_task,
            args=(request.user_creds, request.signin_url, request.billing_history_url)
        )
        process.start()
        
        # Update status
        agent_status["running"] = True
        agent_status["process"] = process
        
        return {
            "message": "Agent started successfully",
            "status": "running",
            "user": request.user_creds.get("username", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")

@app.post("/api/agent/stop")
async def stop_agent():
    """
    POST API to stop the agent with force kill of all browser processes
    """
    if not agent_status["running"]:
        raise HTTPException(status_code=400, detail="Agent is not running")
    
    try:
        # Set stop flag
        agent_status["stop_requested"] = True
        
        # Try to terminate the process
        if agent_status["process"] and agent_status["process"].is_alive():
            print("Attempting to terminate agent process...")
            agent_status["process"].terminate()
            
            # Wait a bit for graceful termination
            agent_status["process"].join(timeout=10)
            
            # Force kill if still alive
            if agent_status["process"].is_alive():
                print("Force killing agent process...")
                agent_status["process"].kill()
                agent_status["process"].join(timeout=5)
        
        # Force kill all browser processes (this is the key part)
        try:
            import subprocess
            import platform
            import psutil
            
            print("Force killing all browser processes...")
            
            if platform.system() == "Windows":
                # Kill Chrome/Chromium processes on Windows
                subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True)
                subprocess.run(["taskkill", "/f", "/im", "chromium.exe"], capture_output=True)
                subprocess.run(["taskkill", "/f", "/im", "msedge.exe"], capture_output=True)
                
                # Also kill any remaining browser processes
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        proc_name = proc.info['name'].lower()
                        if any(browser in proc_name for browser in ['chrome', 'chromium', 'edge', 'firefox']):
                            print(f"Killing browser process: {proc.info['name']} (PID: {proc.info['pid']})")
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
            else:
                # Kill Chrome/Chromium processes on Unix-like systems
                subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
                subprocess.run(["pkill", "-f", "chromium"], capture_output=True)
                subprocess.run(["pkill", "-f", "firefox"], capture_output=True)
                
                # Also kill any remaining browser processes
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        proc_name = proc.info['name'].lower()
                        if any(browser in proc_name for browser in ['chrome', 'chromium', 'firefox']):
                            print(f"Killing browser process: {proc.info['name']} (PID: {proc.info['pid']})")
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
            print("Force killed all browser processes")
            
        except Exception as kill_error:
            print(f"Warning: Could not force kill browser processes: {kill_error}")
        
        # Reset status
        agent_status["running"] = False
        agent_status["process"] = None
        
        return {
            "message": "Agent stopped and all browser processes terminated",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        # Reset status even on error
        agent_status["running"] = False
        agent_status["process"] = None
        agent_status["stop_requested"] = False
        raise HTTPException(status_code=500, detail=f"Failed to stop agent: {str(e)}")

@app.post("/api/agent/results")
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
        
        # The result is not being stored locally, this function is now redundant
        # For now, we'll just print a message
        print(f"✅ Agent results received for user: {result.user_creds.get('username', 'unknown')}")
        
        return {
            "message": "Agent results received (not stored locally)",
            "user": result.user_creds.get("username", "unknown"),
            "timestamp": result.timestamp
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store results: {str(e)}")

@app.post("/api/agent/error")
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

@app.get("/api/health")
async def health_check():
    """
    Health test API to check if FastAPI is responsive
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_status": agent_status["running"],
        "message": "FastAPI is running and responsive"
    }

@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "message": "GPT Web Scraper API",
        "version": "1.0.0",
        "endpoints": [
            "POST /api/agent/run - Start the agent",
            "POST /api/agent/stop - Stop the agent", 
            "POST /api/agent/results - Store agent results",
            "POST /api/agent/error - Store agent errors",
            "GET /api/health - Health check"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
