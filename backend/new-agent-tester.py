import json
import time
import requests
import os
from datetime import datetime
import calendar

# Browser Use Cloud API Configuration
API_KEY = os.getenv("BROWSER_USE_API_KEY", "bu_jUbzwS8q0G2I-u9cQxqe120wEDWZZVMMgSebTpjjois")
BASE_URL = 'https://api.browser-use.com/api/v1'
HEADERS = {'Authorization': f'Bearer {API_KEY}'}

def create_task(instructions: str):
    """Create a new browser automation task"""
    response = requests.post(f'{BASE_URL}/run-task', headers=HEADERS, json={'task': instructions})
    response.raise_for_status()
    return response.json()['id']

def get_task_status(task_id: str):
    """Get current task status"""
    response = requests.get(f'{BASE_URL}/task/{task_id}/status', headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_task_details(task_id: str):
    """Get full task details including output"""
    response = requests.get(f'{BASE_URL}/task/{task_id}', headers=HEADERS)
    response.raise_for_status()
    return response.json()

def wait_for_completion(task_id: str, poll_interval: int = 2):
    """Poll task status until completion with real-time step monitoring"""
    count = 0
    unique_steps = []
    
    print(f"[INFO] Monitoring task {task_id}...")
    
    while True:
        try:
            details = get_task_details(task_id)
            new_steps = details.get('steps', [])
            
            # Print only new steps that haven't been seen before
            if new_steps != unique_steps:
                for step in new_steps:
                    if step not in unique_steps:
                        print(f"[STEP] {json.dumps(step, indent=2)}")
                unique_steps = new_steps
            
            count += 1
            status = details.get('status', 'unknown')
            
            if status in ['finished', 'failed', 'stopped']:
                print(f"[INFO] Task completed with status: {status}")
                return details
                
            time.sleep(poll_interval)
            
        except Exception as e:
            print(f"[ERROR] Error monitoring task: {e}")
            time.sleep(poll_interval)

def download_output_files(task_details, download_dir="./duke_bills"):
    """Download any output files from the completed task"""
    output_files = task_details.get('output_files', [])
    
    if not output_files:
        print("[INFO] No output files found in task result")
        return []
    
    print(f"[INFO] Found {len(output_files)} output files")
    print(f"[DEBUG] Output files structure: {output_files}")
    
    # Ensure download directory exists
    os.makedirs(download_dir, exist_ok=True)
    
    downloaded_files = []
    
    for file_info in output_files:
        # Handle both dict and string formats
        if isinstance(file_info, dict):
            file_name = file_info.get('file_name', 'unknown')
            file_id = file_info.get('id', 'unknown')
        else:
            # If it's a string, use it as the filename
            file_name = str(file_info)
            file_id = str(file_info)
        
        if file_name.lower().endswith('.pdf'):
            try:
                print(f"[INFO] Downloading PDF: {file_name}")
                
                # Get download URL for the file
                file_response = requests.get(
                    f"{BASE_URL}/task/{task_details['id']}/output-file/{file_id}", 
                    headers=HEADERS
                )
                file_response.raise_for_status()
                
                # Download the actual file content
                file_url = file_response.json().get('download_url')
                if not file_url:
                    print(f"[ERROR] No download URL found for {file_name}")
                    continue
                
                file_content_response = requests.get(file_url)
                file_content_response.raise_for_status()
                
                # Create organized folder structure
                now = datetime.now()
                year = now.strftime("%Y")
                month_name = calendar.month_name[now.month]
                
                year_folder = os.path.join(download_dir, year)
                month_folder = os.path.join(year_folder, month_name)
                os.makedirs(month_folder, exist_ok=True)
                
                # Generate filename with timestamp
                safe_time = now.strftime("%d-%m-%y_%I-%M%p")
                local_filename = file_name
                local_path = os.path.join(month_folder, local_filename)
                
                # Save file locally
                with open(local_path, "wb") as f:
                    f.write(file_content_response.content)
                
                print(f"[SUCCESS] Downloaded and saved: {local_path}")
                downloaded_files.append(local_path)
                
            except Exception as e:
                print(f"[ERROR] Failed to download {file_name}: {e}")
        else:
            print(f"[INFO] Skipping non-PDF file: {file_name}")
    
    return downloaded_files

def run_duke_energy_task(email: str, password: str, signin_url: str, billing_history_url: str, account_number: str):
    """Run the complete Duke Energy billing automation task"""
    print(f"[INFO] Running Duke Energy billing automation task for account {account_number}")
    
    # Create the task instructions
    task_instructions = f"""
1. Go to {signin_url}
2. Wait for the page to fully load (this site is slow)
3. Log-in with:
• email : {email}
• password : {password}

5. Wait until the Billing Accounts text is visible. If not, wait 5 seconds and check again.
6. Select the account number: {account_number}
7. Navigate to {billing_history_url} or click the billing tab
8. Wait until the text "Billing History" is visible and navigate to the statements tab
9. If "Oops, something went wrong." appears, STOP the task with status "Failed"
10. Click only the download button in the FIRST row
11. Wait until the bill PDF finishes downloading
12. Use the 'done' action to mark the task as finished with message "Successfully downloaded bill for account {account_number}"
"""


    
    print("[INFO] Starting Duke Energy billing automation task...")
    print(f"[INFO] Email: {email}")
    print(f"[INFO] Sign-in URL: {signin_url}")
    print(f"[INFO] Billing URL: {billing_history_url}")
    
    try:
        # Create the task
        task_id = create_task(task_instructions)
        print(f"[SUCCESS] Task created with ID: {task_id}")
        
        # Monitor task completion
        task_details = wait_for_completion(task_id)
        
        # Check final status
        final_status = task_details.get('status')
        print(f"[INFO] Final task status: {final_status}")
        
        if final_status == 'finished':
            print("[SUCCESS] Task completed successfully!")
            
            # Download any output files
            downloaded_files = download_output_files(task_details)
            
            if downloaded_files:
                print(f"[SUCCESS] Downloaded {len(downloaded_files)} PDF files")
                for file_path in downloaded_files:
                    print(f"  - {file_path}")
            else:
                print("[WARNING] No PDF files were downloaded")
                
        elif final_status == 'failed':
            print("[ERROR] Task failed!")
            print(f"[ERROR] Task output: {task_details.get('output', 'No output available')}")
            
        elif final_status == 'stopped':
            print("[WARNING] Task was stopped!")
            print(f"[WARNING] Task output: {task_details.get('output', 'No output available')}")
            
        else:
            print(f"[WARNING] Unknown task status: {final_status}")
            
        return task_details
        
    except Exception as e:
        print(f"[ERROR] Task execution failed: {e}")
        return None

def main():
    """Main function to run the Duke Energy automation"""
    print("Starting Duke Energy Billing Automation")
    # Example credentials and URLs - replace with actual values
    email = "winslow_manager@reeapartments.com"
    password = "SummerHeat@"
    signin_url = "https://my.xcelenergy.com/MyAccount/MA_SBLoginInit"
    billing_history_url = "https://my.xcelenergy.com/MyAccount/s/billing-and-payment"
    account_numbers = ["0013107267", "0013103769"]
    # Check if API key is set
    if API_KEY == "your_api_key_here":
        print("[ERROR] Please set the BROWSER_USE_API_KEY environment variable")
        print("Example: export BROWSER_USE_API_KEY='your_actual_api_key'")
        return
    
    print("=" * 60)
    print("Duke Energy Billing Automation - Browser Use Cloud")
    print("=" * 60)
    
    # Run the automation task
    for account_number in account_numbers:
        result = run_duke_energy_task(email, password, signin_url, billing_history_url, account_number)
    
    if result:
        print("\n" + "=" * 60)
        print("Task completed!")
        print(f"Final output: {result.get('output', 'No output')}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Task failed!")
        print("=" * 60)

if __name__ == "__main__":
    main()
