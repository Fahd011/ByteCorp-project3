"""
Agent Service - Abstract layer for agent operations
This service provides a clean interface for agent operations and can be easily extended
for different agent types and cloud storage providers.
"""

import time
import os
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from pathlib import Path

from datetime import datetime, timedelta

# Import configuration
from config import config
from azure_storage_service import azure_storage_service

# Directory to store account numbers
ACCOUNTS_DIR = Path("xcel_accounts")
ACCOUNTS_DIR.mkdir(exist_ok=True)

class AgentService:
    """Abstract service for agent operations"""
    
    def __init__(self, storage_provider: str = None):
        """
        Initialize agent service
        
        Args:
            storage_provider: Storage provider ("local", "azure", "aws", etc.)
        """
        self.storage_provider = storage_provider or config.STORAGE_PROVIDER
    
    def _is_xcel_energy(self, credential) -> bool:
        """Check if credential is for Xcel Energy"""
        if not credential.utility_co_name:
            return False
        return "xcel" in credential.utility_co_name.lower()
    
    def _get_accounts_file_path(self, credential_id: str) -> Path:
        """Get the path to the account numbers file for a credential"""
        return ACCOUNTS_DIR / f"{credential_id}_accounts.json"
    
    def _load_account_numbers(self, credential_id: str) -> Optional[List[str]]:
        """Load account numbers from file if exists"""
        accounts_file = self._get_accounts_file_path(credential_id)
        if accounts_file.exists():
            try:
                with open(accounts_file, 'r') as f:
                    data = json.load(f)
                    return data.get("account_numbers", [])
            except Exception as e:
                print(f"[❌] Error reading accounts file: {str(e)}")
                return None
        return None
    
    def _save_account_numbers(self, credential_id: str, account_numbers: List[str]):
        """Save account numbers to file"""
        accounts_file = self._get_accounts_file_path(credential_id)
        try:
            with open(accounts_file, 'w') as f:
                json.dump({
                    "credential_id": credential_id,
                    "account_numbers": account_numbers,
                    "collected_at": datetime.utcnow().isoformat()
                }, f, indent=2)
            print(f"[✅] Saved {len(account_numbers)} account numbers to {accounts_file}")
        except Exception as e:
            print(f"[❌] Error saving accounts file: {str(e)}")
    
    async def run_agent(self, credential, db: Session) -> Dict[str, Any]:
        """
        Run agent for a specific credential if billing cycle matches (yesterday).
        For Xcel Energy: handles two-phase execution (collect accounts, then download bills)
        """
        try:
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)

            # Skip if no billing cycle set
            if not credential.billing_cycle_day:
                return {
                    "success": False,
                    "message": "No billing cycle date set",
                    "credential_id": credential.id
                }

            # Run only if yesterday was the billing cycle date
            if yesterday.day != credential.billing_cycle_day:
                return {
                    "success": False,
                    "message": f"Skipping. Billing cycle day is {credential.billing_cycle_day}, yesterday was {yesterday.day}",
                    "credential_id": credential.id
                }

            # Check if this is Xcel Energy
            if self._is_xcel_energy(credential):
                return await self._run_xcel_energy_agent(credential, db)
            else:
                return await self._run_standard_agent(credential, db)

        except Exception as e:
            credential.last_state = "error"
            credential.last_error = str(e)
            credential.last_run_time = datetime.utcnow()
            db.commit()

            return {
                "success": False,
                "message": f"Agent failed: {str(e)}",
                "credential_id": credential.id,
                "error": str(e)
            }
    
    async def _run_standard_agent(self, credential, db: Session) -> Dict[str, Any]:
        """Run standard agent for non-Xcel Energy providers"""
        # Update state → running
        credential.last_state = "running"
        credential.last_run_time = datetime.utcnow()
        credential.last_error = None
        db.commit()
        
        print(f"[INFO] Running standard agent for {credential.email} …")

        # Do the work
        await self._execute_agent_work(credential, account_number=None)

        credential.last_state = "completed"
        db.commit()

        return {
            "success": True,
            "message": "Agent completed successfully",
            "credential_id": credential.id
        }
    
    async def _run_xcel_energy_agent(self, credential, db: Session) -> Dict[str, Any]:
        """
        Run Xcel Energy agent with two-phase execution:
        Phase 1: Collect all account numbers (if not already collected)
        Phase 2: Download bill for each account number
        """
        # Check if account numbers file exists
        account_numbers = self._load_account_numbers(credential.id)
        
        if not account_numbers or len(account_numbers) == 0:
            # Phase 1: Collect account numbers
            print(f"[INFO] Phase 1: Collecting account numbers for {credential.email} …")
            
            credential.last_state = "running"
            credential.last_run_time = datetime.utcnow()
            credential.last_error = None
            db.commit()
            
            # Run agent in collection mode
            collected_accounts = await self._collect_xcel_account_numbers(credential)
            
            if collected_accounts:
                # Save account numbers to file
                self._save_account_numbers(credential.id, collected_accounts)
                
                print(f"[✅] Collected {len(collected_accounts)} account numbers: {collected_accounts}")
                
                # Immediately proceed to Phase 2
                account_numbers = collected_accounts
            else:
                credential.last_state = "error"
                credential.last_error = "Failed to collect account numbers"
                db.commit()
                
                return {
                    "success": False,
                    "message": "Failed to collect account numbers",
                    "credential_id": credential.id,
                    "phase": "collection"
                }
        
        # Phase 2: Download bills for each account number
        print(f"[INFO] Phase 2: Downloading bills for {len(account_numbers)} accounts …")
        
        credential.last_state = "running"
        db.commit()
        
        results = []
        for account_number in account_numbers:
            print(f"[INFO] Processing account {account_number} …")
            
            try:
                await self._execute_agent_work(credential, account_number=account_number)
                results.append({
                    "account_number": account_number,
                    "success": True
                })
                print(f"[✅] Successfully processed account {account_number}")
            except Exception as e:
                results.append({
                    "account_number": account_number,
                    "success": False,
                    "error": str(e)
                })
                print(f"[❌] Failed to process account {account_number}: {str(e)}")
        
        # Check if all succeeded
        all_success = all(r["success"] for r in results)
        
        if all_success:
            credential.last_state = "completed"
        else:
            credential.last_state = "error"
            failed_accounts = [r['account_number'] for r in results if not r['success']]
            credential.last_error = f"Some accounts failed: {failed_accounts}"
        
        db.commit()
        
        return {
            "success": all_success,
            "message": f"Processed {len(results)} accounts",
            "credential_id": credential.id,
            "phase": "download",
            "results": results
        }
    
    async def _collect_xcel_account_numbers(self, credential) -> List[str]:
        """
        Execute agent to collect account numbers for Xcel Energy.
        Returns list of account numbers.
        """
        import httpx
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            payload = {
                "user_creds": [{
                    "username": credential.email,
                    "password": credential.password,
                    "credential_id": credential.id
                }],
                "signin_url": credential.login_url,
                "billing_history_url": credential.billing_url,
                "mode": "collect_accounts"
            }
            
            try:
                response = await client.post("http://localhost:5000/api/agent/run-xcel-collection", json=payload)
                response.raise_for_status()
                response_data = response.json()
                
                # Extract account numbers from response
                account_numbers = response_data.get("account_numbers", [])
                return account_numbers
            except Exception as e:
                print(f"[❌] Error collecting account numbers: {str(e)}")
                return []
    
    async def _execute_agent_work(self, credential, account_number: Optional[str] = None):
        """
        Execute the actual agent work by calling the agent API endpoint.
        
        Args:
            credential: The credential to use
            account_number: Optional account number for Xcel Energy multi-account support
        """
        import httpx
        async with httpx.AsyncClient(timeout=300.0) as client:
            payload = {
                "user_creds": [{
                    "username": credential.email,
                    "password": credential.password,
                    "credential_id": credential.id
                }],
                "signin_url": credential.login_url,
                "billing_history_url": credential.billing_url
            }
            
            # Add account number if provided (for Xcel Energy)
            if account_number:
                payload["account_number"] = account_number
            
            response = await client.post("http://localhost:5000/api/agent/run", json=payload)
            response_data = response.json()
        
        # You can handle the response here, e.g., save PDF, update credential, etc.
        pass

    
    def _generate_sample_pdf(self, credential):
        """
        Generate a sample PDF content for demonstration
        In a real implementation, this would be the actual PDF from the billing portal
        """
        # This is a simple text-based PDF simulation
        # In reality, you'd use a library like reportlab or PyPDF2 to create actual PDFs
        pdf_content = f"""
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 200
>>
stream
BT
/F1 12 Tf
72 720 Td
(Sample Bill for {credential.email}) Tj
0 -20 Td
(Client: {credential.client_name or 'N/A'}) Tj
0 -20 Td
(Utility: {credential.utility_co_name or 'N/A'}) Tj
0 -20 Td
(Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF
""".encode('utf-8')
        
        return pdf_content
    
    def upload_file(self, file_data: bytes, filename: str, file_type: str = "pdf") -> str:
        """
        Upload file to storage provider
        
        Args:
            file_data: File content as bytes
            filename: Name of the file
            file_type: Type of file (pdf, csv, etc.)
            
        Returns:
            URL or path to uploaded file
        """
        if self.storage_provider == "local":
            return self._upload_to_local(file_data, filename)
        elif self.storage_provider == "azure":
            return self._upload_to_azure(file_data, filename)
        else:
            raise ValueError(f"Unsupported storage provider: {self.storage_provider}")
    
    def upload_manual_credential_file(self, file_data: bytes, user_id: str, credential_id: str, filename: str) -> str:
        """
        Upload manual credential file to Azure storage
        
        Args:
            file_data: File content as bytes
            user_id: User ID
            credential_id: Credential ID
            filename: Name of the file
            
        Returns:
            Blob name in Azure storage
        """
        success, blob_url, blob_name = azure_storage_service.upload_manual_credential_pdf(
            file_data, user_id, credential_id, filename
        )
        
        if not success:
            raise Exception("Failed to upload file to Azure storage")
        
        return blob_name
    
    def _upload_to_local(self, file_data: bytes, filename: str) -> str:
        """Upload file to local storage - DEPRECATED, use Azure storage instead"""
        raise NotImplementedError("Local storage is deprecated. Please use Azure storage instead.")
    
    def _upload_to_azure(self, file_data: bytes, filename: str) -> str:
        """Upload file to Azure Blob Storage"""
        # TODO: Implement Azure Blob Storage upload
        # This is a placeholder for future Azure integration
        raise NotImplementedError("Azure storage not yet implemented")
    
    def download_file(self, file_path: str) -> bytes:
        """
        Download file from storage provider
        
        Args:
            file_path: Path or URL to the file
            
        Returns:
            File content as bytes
        """
        if self.storage_provider == "local":
            return self._download_from_local(file_path)
        elif self.storage_provider == "azure":
            return self._download_from_azure(file_path)
        else:
            raise ValueError(f"Unsupported storage provider: {self.storage_provider}")
    
    def _download_from_local(self, file_path: str) -> bytes:
        """Download file from local storage - DEPRECATED, use Azure storage instead"""
        raise NotImplementedError("Local storage is deprecated. Please use Azure storage instead.")
    
    def _download_from_azure(self, file_path: str) -> bytes:
        """Download file from Azure Blob Storage"""
        # TODO: Implement Azure Blob Storage download
        # This is a placeholder for future Azure integration
        raise NotImplementedError("Azure storage not yet implemented")

# Global agent service instance
agent_service = AgentService(storage_provider="azure")

# Factory function to create agent service with different providers
def create_agent_service(storage_provider: str = "local") -> AgentService:
    """
    Factory function to create agent service
    
    Args:
        storage_provider: Storage provider to use
        
    Returns:
        Configured AgentService instance
    """
    return AgentService(storage_provider=storage_provider)
