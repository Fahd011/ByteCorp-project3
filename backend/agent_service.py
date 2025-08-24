"""
Agent Service - Abstract layer for agent operations
This service provides a clean interface for agent operations and can be easily extended
for different agent types and cloud storage providers.
"""

import time
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from datetime import datetime, timedelta

# Import configuration
from config import config

class AgentService:
    """Abstract service for agent operations"""
    
    def __init__(self, storage_provider: str = None):
        """
        Initialize agent service
        
        Args:
            storage_provider: Storage provider ("local", "azure", "aws", etc.)
        """
        self.storage_provider = storage_provider or config.STORAGE_PROVIDER
    
    async def run_agent(self, credential, db: Session) -> Dict[str, Any]:
        """
        Run agent for a specific credential if billing cycle matches (yesterday).
        If yesterday == billing_cycle_day → agent runs.
        Else → it skips with a message.
        If no cycle day in CSV → also skips safely.
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

            # Update state → running
            credential.last_state = "running"
            credential.last_run_time = datetime.utcnow()
            credential.last_error = None
            db.commit()
            
            print(f"[INFO] Running agent for {credential.email} …")

            # Do the work
            await self._execute_agent_work(credential)

            # Update state → completed
            credential.last_state = "completed"
            credential.last_run_time = datetime.utcnow()
            credential.last_error = None
            db.commit()

            return {
                "success": True,
                "message": "Agent completed successfully",
                "credential_id": credential.id
            }

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
    
    async def _execute_agent_work(self, credential):
        """
        Execute the actual agent work by calling the agent API endpoint.
        """
        print("credential.email:", credential.email)
        print("credential.password:", credential.password)

        import httpx
        async with httpx.AsyncClient() as client:
            payload = {
                "user_creds": [{"username": credential.email, "password": credential.password,"credential_id": credential.id}],
                "signin_url": credential.login_url,
                "billing_history_url": credential.billing_url
            }
            response = await client.post("http://localhost:5000/api/agent/run", json=payload)
            response_data = response.json()
            print("API response:", response_data)
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
    
    def _upload_to_local(self, file_data: bytes, filename: str) -> str:
        """Upload file to local storage"""
        # Create uploads directory if it doesn't exist
        os.makedirs("./uploads", exist_ok=True)
        
        # Generate unique filename
        unique_filename = f"uploads/{uuid.uuid4()}_{filename}"
        
        # Write file
        with open(unique_filename, "wb") as f:
            f.write(file_data)
        
        return unique_filename
    
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
        """Download file from local storage"""
        with open(file_path, "rb") as f:
            return f.read()
    
    def _download_from_azure(self, file_path: str) -> bytes:
        """Download file from Azure Blob Storage"""
        # TODO: Implement Azure Blob Storage download
        # This is a placeholder for future Azure integration
        raise NotImplementedError("Azure storage not yet implemented")

# Global agent service instance
agent_service = AgentService(storage_provider="local")

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
