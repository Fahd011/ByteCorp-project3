import httpx
from datetime import datetime
from app.db import get_db, SessionLocal
from app.models import BillingResult, Provider, ManualBillResponse
from app.routes.auth import verify_token
from fastapi import Depends, UploadFile, File, Form, APIRouter, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from azure_storage_service import azure_storage_service
import multiprocessing


router = APIRouter()


@router.post("/api/manual-bills/upload")
async def upload_manual_bill(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(...),
    provider_id: str = Form(...),
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Upload a manual bill and trigger automatic PDF extraction"""
    
    # Validate file type
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Get provider information
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Read PDF content
    pdf_content = await pdf_file.read()
    
    # Get current date info for storage path
    now = datetime.now()
    year = now.strftime("%Y")
    month_name = now.strftime("%B")  # e.g. January, February
    
    # Upload to Azure storage
    success, blob_url, blob_name = azure_storage_service.upload_pdf_to_azure(
        pdf_content=pdf_content,
        email="manual_upload",  # Use a generic identifier for manual uploads
        original_filename=pdf_file.filename,
        provider=provider.name
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload PDF to Azure storage")
    
    # Create BillingResult entry for manual upload
    billing_result = BillingResult(
        user_billing_credential_id=None,  # Manual uploads have no credential
        azure_blob_url=blob_name,
        original_filename=pdf_file.filename,
        provider_name=provider.name,
        status="processing",
        year=year,
        month=month_name,
        run_time=datetime.utcnow()
    )
    
    db.add(billing_result)
    db.commit()
    db.refresh(billing_result)
    
    # Trigger automatic PDF extraction IN BACKGROUND (don't await)
    # To:
    process = multiprocessing.Process(
        target=trigger_manual_bill_extraction_wrapper,
        args=(billing_result.id, provider.name)
    )
    process.start()
    
    # Return immediately without waiting for extraction
    return {
        "message": "Bill uploaded successfully. Extraction in progress.",
        "billing_result_id": billing_result.id,
        "status": billing_result.status
    }


@router.get("/api/manual-bills", response_model=List[ManualBillResponse])
def get_manual_bills(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get all manual bills (where user_billing_credential_id is NULL)"""
    
    manual_bills = db.query(BillingResult).filter(
        BillingResult.user_billing_credential_id == None
    ).order_by(BillingResult.created_at.desc()).all()
    
    return manual_bills


def trigger_manual_bill_extraction_wrapper(billing_result_id: str, provider_name: str):
    """Wrapper to run async extraction in background"""
    import asyncio
    
    # Get the billing result from database
    db = SessionLocal()
    try:
        billing_result = db.query(BillingResult).filter(BillingResult.id == billing_result_id).first()
        if billing_result:
            # Run the async function
            asyncio.run(trigger_manual_bill_extraction(billing_result, provider_name))
    except Exception as e:
        print(f"[ERROR] Background extraction failed: {e}")
        # Update status to error
        if billing_result:
            billing_result.status = "error"
            db.commit()
    finally:
        db.close()


async def trigger_manual_bill_extraction(billing_result, provider_name):
    """Automatically extract data from the manually uploaded bill"""
    try:
        # Prepare the billing result data for extraction
        billing_data = {
            "id": billing_result.id,
            "azure_blob_url": billing_result.azure_blob_url,
            "username": billing_result.original_filename,  # Use filename as identifier
            "year": billing_result.year,
            "month": billing_result.month,
            "status": billing_result.status,
            "provider_name": provider_name  # Pass provider name for routing
        }
        
        print(f"[INFO] Starting automatic PDF extraction for manual bill {billing_result.id}")
        
        # Call the PDF extraction API
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                "http://localhost:5000/api/pdf-extraction/upload",
                json={"billing_result": billing_data}
            )
            
            if response.status_code == 200:
                print(f"[✅] Automatic PDF extraction completed successfully for {billing_result.id}")
                extraction_response = response.json()
                #print(f"[INFO] Extraction response: {extraction_response}")
                
                # Get the session_id from the response
                session_id = extraction_response.get("session_id")
                if session_id:
                    # Export to Excel and get the file
                    excel_response = await client.get(f"http://localhost:5000/api/pdf-extraction/export/{session_id}")
                    
                    if excel_response.status_code == 200:
                        # Save Excel file to Azure
                        import json
                        excel_content = excel_response.content
                        filename_base = billing_result.original_filename.replace('.pdf', '')
                        excel_blob_name = f"{filename_base}_extracted_data.xlsx"
                        
                        try:
                            success, excel_blob_url, uploaded_excel_name = azure_storage_service.upload_pdf_to_azure(
                                pdf_content=excel_content,
                                email="manual_upload",
                                original_filename=excel_blob_name,
                                provider=provider_name
                            )
                            
                            if success:
                                print(f"[✅] Excel file uploaded to Azure: {uploaded_excel_name}")
                                
                                # Save JSON data to Azure
                                results = extraction_response.get("results", [])
                                if results and len(results) > 0:
                                    json_data = results[0].get("extracted_data", {})
                                    json_content = json.dumps(json_data, indent=2).encode('utf-8')
                                else:
                                    print("[❌] No extraction results found")
                                    json_data = {}
                                    json_content = json.dumps(json_data, indent=2).encode('utf-8')

                                json_blob_name = f"{filename_base}_extracted_data.json"
                                
                                json_success, json_blob_url, uploaded_json_name = azure_storage_service.upload_pdf_to_azure(
                                    pdf_content=json_content,
                                    email="manual_upload",
                                    original_filename=json_blob_name,
                                    provider=provider_name
                                )
                                
                                if json_success:
                                    print(f"[✅] JSON data uploaded to Azure: {uploaded_json_name}")
                                    
                                    # Update the BillingResult with the new blob URLs
                                    from app.db import SessionLocal
                                    db = SessionLocal()
                                    try:
                                        # Get the billing result and update it
                                        billing_record = db.query(BillingResult).filter(BillingResult.id == billing_result.id).first()
                                        if billing_record:
                                            billing_record.excel_blob_url = uploaded_excel_name
                                            billing_record.json_blob_url = uploaded_json_name
                                            billing_record.status = "completed"
                                            db.commit()
                                            print(f"[✅] Updated BillingResult with Excel and JSON blob URLs")
                                        else:
                                            print(f"[❌] BillingResult not found for ID: {billing_result.id}")
                                    except Exception as db_error:
                                        print(f"[❌] Failed to update BillingResult: {db_error}")
                                        db.rollback()
                                    finally:
                                        db.close()
                                else:
                                    print(f"[❌] Failed to upload JSON data to Azure")
                            else:
                                print(f"[❌] Failed to upload Excel file to Azure")
                        except Exception as azure_error:
                            print(f"[❌] Azure upload error: {azure_error}")
                    else:
                        print(f"[❌] Failed to export Excel file: {excel_response.status_code}")
                else:
                    print(f"[❌] No session_id in extraction response")
            else:
                print(f"[❌] Automatic PDF extraction failed for {billing_result.id}")
                print(f"[ERROR] Status: {response.status_code}, Response: {response.text}")
                
    except Exception as e:
        print(f"[❌] Error in automatic PDF extraction: {str(e)}")
        import traceback
        traceback.print_exc()

