from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, APIRouter
import json
import os
import tempfile
import shutil
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
import uuid
from pydantic import BaseModel, Field
from azure_storage_service import azure_storage_service
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env")
from fastapi.responses import FileResponse
import threading
from config import config
from app.extraction.extractor_router import extract_bill_by_provider
from app.schemas.duke_bill_schema import UtilityBillExtraction


router = APIRouter()

class ExtractionResult(BaseModel):
    filename: str
    extracted_data: Dict[str, Any]
    status: str
    error: str = None

class BillingResultRequest(BaseModel):
    billing_result: Dict[str, Any]

# Store extraction results in memory (in production, use a database)
extraction_results: Dict[str, List[ExtractionResult]] = {}

# Add a global dictionary to store usernames for sessions
session_usernames = {}

@router.post("/api/pdf-extraction/upload")
async def upload_files(request: BillingResultRequest):
    """Process PDF from Azure blob storage using billing result data"""
    
    billing_result = request.billing_result
    azure_blob_name = billing_result.get("azure_blob_url")
    username = billing_result.get("username", "unknown")
    provider_name = billing_result.get("provider_name", "")
    
    if not azure_blob_name:
        raise HTTPException(status_code=400, detail="No Azure blob name found in billing result")
    
    # Create a unique session ID for this batch
    session_id = billing_result.get("id");
    extraction_results[session_id] = []
    
    # Store username for this session
    session_usernames[session_id] = username
    
    try:
        # Download PDF from Azure blob storage
        print(f"🔍 Downloading PDF from Azure blob: {azure_blob_name}")
        print(f"📋 Billing result data: {billing_result}")
        print(f"🏢 Provider: {provider_name}")
        success, pdf_content = azure_storage_service.download_pdf_from_azure(azure_blob_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to download PDF from Azure blob: {azure_blob_name}")
        
        # Extract filename from blob name
        filename = azure_blob_name.split('/')[-1]
        
        # Extract bill data using RAG
        extracted_data = await extract_bill_by_provider(provider_name, pdf_content)
        
        # Store result with billing context
        result = ExtractionResult(
            filename=filename,
            extracted_data=extracted_data,
            status="success"
        )
        extraction_results[session_id].append(result)
        
        print(f"✅ Successfully processed PDF: {filename}")
        
    except Exception as e:
        # Log error to console
        import traceback
        print(f"Error processing Azure blob {azure_blob_name}:", str(e))
        traceback.print_exc()
        
        # Store error result
        filename = azure_blob_name.split('/')[-1] if azure_blob_name else "unknown"
        result = ExtractionResult(
            filename=filename,
            extracted_data={},
            status="error",
            error=str(e) if str(e) else repr(e)
        )
        extraction_results[session_id].append(result)
    
    return {
        "session_id": session_id,
        "message": f"Processed 1 file from Azure blob",
        "billing_result": billing_result,
        "results": extraction_results[session_id]
    }

@router.get("/api/pdf-extraction/results/{session_id}")
async def get_results(session_id: str):
    """Get extraction results for a session"""
    if session_id not in extraction_results:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "results": extraction_results[session_id]
    }

@router.get("/api/pdf-extraction/export/{session_id}")
async def export_to_excel(session_id: str):
    """Export extracted data to Excel file"""
    if session_id not in extraction_results:
        raise HTTPException(status_code=404, detail="Session not found")
    
    results = extraction_results[session_id]
    
    if not results:
        raise HTTPException(status_code=400, detail="No data to export")
    
    try:
        # Prepare data for Excel export
        excel_data = []
        
        for result in results:
            if result.status == "success":
                # Flatten the nested data structure for Excel
                row = {
                    "filename": result.filename,
                    "status": result.status
                }
                
                # Recursively flatten the extracted data
                def flatten_dict(d, parent_key='', sep='_'):
                    items = []
                    for k, v in d.items():
                        new_key = f"{parent_key}{sep}{k}" if parent_key else k
                        if isinstance(v, dict):
                            items.extend(flatten_dict(v, new_key, sep=sep).items())
                        elif isinstance(v, list):
                            for i, item in enumerate(v):
                                if isinstance(item, dict):
                                    items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                                else:
                                    items.append((f"{new_key}_{i}", item))
                        else:
                            items.append((new_key, v))
                    return dict(items)
                
                # Flatten the extracted data
                flattened_data = flatten_dict(result.extracted_data)
                row.update(flattened_data)
                excel_data.append(row)
            else:
                # Handle failed extractions
                excel_data.append({
                    "filename": result.filename,
                    "status": result.status,
                    "error": result.error
                })
        
        # Create DataFrame and export to Excel
        df = pd.DataFrame(excel_data)
        
        # Get username and clean it for filename
        username = session_usernames.get(session_id, session_id)
        clean_username = username.replace('@', '_').replace('+', '_').replace('.', '_').replace(' ', '_')
        
        # Create Excel filename with username
        excel_filename = f"extracted_{clean_username}_bill.xlsx"
        print(f"📁 Final filename: {excel_filename}")
        # Use tempfile for cross-platform compatibility
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            excel_path = tmp_file.name
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Extracted Data', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Extracted Data']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Return file and schedule cleanup
        def cleanup_file():
            try:
                os.unlink(excel_path)
            except:
                pass
        
        # Schedule cleanup after 5 minutes
        timer = threading.Timer(300, cleanup_file)
        timer.start()
        
        return FileResponse(
            excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=excel_filename
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating Excel file: {str(e)}")

@router.get("/api/pdf-extraction/")
async def root():
    """Root endpoint"""
    return {
        "message": "Utility Bill Extractor API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "POST /api/pdf-extraction/upload - Upload PDF files for extraction",
            "results": "GET /api/pdf-extraction/results/{session_id} - Get extraction results",
            "export": "GET /api/pdf-extraction/export/{session_id} - Export results to Excel"
        }
    }