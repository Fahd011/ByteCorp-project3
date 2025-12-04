from datetime import datetime
from app.db import get_db, get_db_context
from app.models import BillingResult, Provider, ManualBillResponse, UserBillingCredential
from app.routes.auth import verify_token
from fastapi import Depends, UploadFile, File, Form, APIRouter, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from azure_storage_service import azure_storage_service
import threading
import json
import tempfile
from pathlib import Path
import pandas as pd
from app.extraction.extractor_router import extract_bill_by_provider
from app.audit_logger import AuditLogger

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
    
    # Log manual bill upload
    AuditLogger.log_manual_bill_upload(
        billing_result_id=billing_result.id,
        filename=pdf_file.filename,
        provider_name=provider.name,
        month=month_name,
        year=year
    )

    # Trigger automatic PDF extraction IN BACKGROUND (don't await)
    # To:
    thread = threading.Thread(
        target=trigger_manual_bill_extraction_wrapper,
        args=(billing_result.id, provider.name),
        daemon=True  # Important: thread dies when main process dies
    )
    thread.start()
    
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
    """Get all manual bills (where user_billing_credential_id is NULL) with login_url from UserBillingCredential when available"""
    
    # Query manual bills (where user_billing_credential_id is NULL)
    manual_bills = db.query(BillingResult).filter(
        BillingResult.user_billing_credential_id == None
    ).order_by(BillingResult.created_at.desc()).all()
    
    # Optimize: Batch fetch all matching credentials in a single query to avoid N+1 problem
    # Get unique provider names from manual bills
    provider_names = {bill.provider_name for bill in manual_bills if bill.provider_name}
    
    # Fetch all matching credentials for the user in a single query
    provider_to_login_url = {}
    if provider_names:
        matching_credentials = db.query(UserBillingCredential).filter(
            UserBillingCredential.user_id == user_id,
            UserBillingCredential.utility_co_name.in_(provider_names),
            UserBillingCredential.is_deleted == False
        ).all()
        
        # Create a map of provider name to login_url, taking the first one found for each provider
        for cred in matching_credentials:
            if cred.utility_co_name not in provider_to_login_url:
                provider_to_login_url[cred.utility_co_name] = cred.login_url
    
    # Build the response with login_urls from the in-memory map
    result = []
    for billing_result in manual_bills:
        login_url = provider_to_login_url.get(billing_result.provider_name) if billing_result.provider_name else None
        
        bill_dict = {
            "id": billing_result.id,
            "original_filename": billing_result.original_filename,
            "provider_name": billing_result.provider_name,
            "azure_blob_url": billing_result.azure_blob_url,
            "excel_blob_url": billing_result.excel_blob_url,
            "json_blob_url": billing_result.json_blob_url,
            "status": billing_result.status,
            "year": billing_result.year,
            "month": billing_result.month,
            "run_time": billing_result.run_time,
            "created_at": billing_result.created_at,
            "login_url": login_url
        }
        result.append(ManualBillResponse(**bill_dict))
    
    return result


@router.post("/api/manual-bills/bulk-upload")
async def upload_manual_bills_bulk(
    background_tasks: BackgroundTasks,
    pdf_files: List[UploadFile] = File(...),
    provider_id: str = Form(...),
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Upload multiple manual bills and trigger automatic PDF extraction in chunks"""
    
    # Validate provider
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Validate all files are PDFs
    for pdf_file in pdf_files:
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail=f"File '{pdf_file.filename}' is not a PDF"
            )
    
    if len(pdf_files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Get current date info
    now = datetime.now()
    year = now.strftime("%Y")
    month_name = now.strftime("%B")
    
    billing_result_ids = []
    uploaded_files = []
    
    # Create all billing result records first
    for pdf_file in pdf_files:
        # Read PDF content
        pdf_content = await pdf_file.read()
        
        # Upload to Azure storage
        success, blob_url, blob_name = azure_storage_service.upload_pdf_to_azure(
            pdf_content=pdf_content,
            email="manual_upload",
            original_filename=pdf_file.filename,
            provider=provider.name
        )
        
        if not success:
            continue  # Skip failed uploads
        
        # Create billing result record
        billing_result = BillingResult(
            azure_blob_url=blob_name,
            status="processing",
            year=year,
            month=month_name,
            original_filename=pdf_file.filename,
            provider_name=provider.name,
            user_billing_credential_id=None
        )
        
        db.add(billing_result)
        db.flush()  # Get the ID
        
        # Log manual bill upload
        AuditLogger.log_manual_bill_upload(
            billing_result_id=billing_result.id,
            filename=pdf_file.filename,
            provider_name=provider.name,
            month=month_name,
            year=year
        )
        
        billing_result_ids.append(billing_result.id)
        uploaded_files.append({
            "id": billing_result.id,
            "filename": pdf_file.filename
        })
    
    db.commit()
    
    # Start bulk extraction in background
    thread = threading.Thread(
        target=trigger_bulk_extraction_wrapper,
        args=(billing_result_ids, provider.name)
    )
    thread.start()
    
    return {
        "message": f"Successfully uploaded {len(uploaded_files)} bills. Extraction in progress.",
        "uploaded_count": len(uploaded_files),
        "uploaded_files": uploaded_files,
        "failed_count": len(pdf_files) - len(uploaded_files)
    }


def trigger_manual_bill_extraction_wrapper(billing_result_id: str, provider_name: str):
    """Wrapper to run async extraction in background"""
    import asyncio
    
    # Get the billing result from database
    try:
        with get_db_context() as db:
            billing_result = db.query(BillingResult).filter(BillingResult.id == billing_result_id).first()
            if billing_result:
                # Run the async function
                asyncio.run(trigger_manual_bill_extraction(billing_result, provider_name))
    except Exception as e:
        print(f"[ERROR] Background extraction failed: {e}")
        # Update status to error
        try:
            with get_db_context() as db:
                billing_result = db.query(BillingResult).filter(BillingResult.id == billing_result_id).first()
                if billing_result:
                    billing_result.status = "error"
                    db.commit()
        except:
            pass


async def trigger_manual_bill_extraction(billing_result, provider_name):
    """Automatically extract data from the manually uploaded bill"""
    try:
        print(f"[INFO] Starting automatic PDF extraction for manual bill {billing_result.id}")
        
        # Download PDF from Azure
        print(f"🔍 Downloading PDF from Azure blob: {billing_result.azure_blob_url}")
        success, pdf_content = azure_storage_service.download_pdf_from_azure(billing_result.azure_blob_url)
        
        if not success:
            raise Exception(f"Failed to download PDF from Azure blob: {billing_result.azure_blob_url}")
        
        print(f"✅ PDF downloaded successfully from Azure")

        # Log extraction start
        AuditLogger.agent_action(
            entity_type="manual_bill",
            action="extract_start",
            entity_id=billing_result.id,
            entity_name=billing_result.original_filename,
            status="pending",
            details={
                "provider": provider_name,
                "filename": billing_result.original_filename
            }
        )
        
        # Extract bill data using RAG
        extracted_data = await extract_bill_by_provider(provider_name, pdf_content)
        
        if extracted_data:
            print(f"[✅] Extraction completed successfully")
            
            # Create Excel file from extracted data
            filename_base = billing_result.original_filename.replace('.pdf', '')
            
            # Flatten the nested data structure for Excel
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
            
            # Create DataFrame
            flattened_data = flatten_dict(extracted_data)
            df = pd.DataFrame([flattened_data])
            
            # Create Excel file in memory
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_excel:
                excel_path = tmp_excel.name
            
            try:
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Extracted Data', index=False)
                
                # Read Excel content
                with open(excel_path, 'rb') as f:
                    excel_content = f.read()
                
                # Upload Excel to Azure
                excel_blob_name = f"{filename_base}_extracted_data.xlsx"
                success, excel_blob_url, uploaded_excel_name = azure_storage_service.upload_pdf_to_azure(
                    pdf_content=excel_content,
                    email="manual_upload",
                    original_filename=excel_blob_name,
                    provider=provider_name
                )
                
                if success:
                    print(f"[✅] Excel file uploaded to Azure: {uploaded_excel_name}")
                    
                    # Upload JSON to Azure
                    json_content = json.dumps(extracted_data, indent=2).encode('utf-8')
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
                        try:
                            with get_db_context() as db:
                                billing_record = db.query(BillingResult).filter(BillingResult.id == billing_result.id).first()
                                if billing_record:
                                    billing_record.excel_blob_url = uploaded_excel_name
                                    billing_record.json_blob_url = uploaded_json_name
                                    billing_record.status = "completed"
                                    
                                    # Extract account number from JSON data
                                    account_number = None
                                    if extracted_data.get('accountData') and len(extracted_data['accountData']) > 0:
                                        account_number = extracted_data['accountData'][0].get('accountNumber')
                                    billing_record.account_number = account_number
                                    
                                    db.commit()
                                    print(f"[✅] Updated BillingResult with Excel and JSON blob URLs")
                                    # Log extraction success
                                    AuditLogger.agent_action(
                                        entity_type="manual_bill",
                                        action="extract_complete",
                                        entity_id=billing_result.id,
                                        entity_name=billing_result.original_filename,
                                        status="success",
                                        details={
                                            "provider": provider_name,
                                            "excel_url": uploaded_excel_name,
                                            "json_url": uploaded_json_name
                                        }
                                    )
                                else:
                                    print(f"[❌] BillingResult not found for ID: {billing_result.id}")
                        except Exception as db_error:
                            print(f"[❌] Failed to update BillingResult: {db_error}")
                    else:
                        print(f"[❌] Failed to upload JSON data to Azure")
                else:
                    print(f"[❌] Failed to upload Excel file to Azure")
            finally:
                # Cleanup temp Excel file
                Path(excel_path).unlink()
        else:
            print(f"[❌] No data extracted from PDF")
                
    except Exception as e:
        print(f"[❌] Error in automatic PDF extraction: {str(e)}")
        import traceback
        traceback.print_exc()

        # Log extraction failure
        AuditLogger.agent_action(
            entity_type="manual_bill",
            action="extract_complete",
            entity_id=billing_result.id,
            entity_name=billing_result.original_filename,
            status="failure",
            details={
                "provider": provider_name,
                "error": str(e)
            }
        )

        # Update billing result status to error
        try:
            with get_db_context() as db:
                billing_record = db.query(BillingResult).filter(BillingResult.id == billing_result.id).first()
                if billing_record:
                    billing_record.status = "error"
                    db.commit()
        except:
            pass


def trigger_bulk_extraction_wrapper(billing_result_ids: List[str], provider_name: str):
    """Wrapper to run bulk extraction in chunks with threading"""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    import time
    
    CHUNK_SIZE = 10
    
    print(f"\n{'='*80}")
    print(f"🚀 Starting bulk extraction for {len(billing_result_ids)} bills")
    print(f"📦 Processing in chunks of {CHUNK_SIZE}")
    print(f"{'='*80}\n")
    
    # Split into chunks of 10
    chunks = [billing_result_ids[i:i + CHUNK_SIZE] 
              for i in range(0, len(billing_result_ids), CHUNK_SIZE)]
    
    total_chunks = len(chunks)
    
    for chunk_idx, chunk in enumerate(chunks, 1):
        print(f"\n{'─'*80}")
        print(f"📦 Processing Chunk {chunk_idx}/{total_chunks} ({len(chunk)} bills)")
        print(f"{'─'*80}\n")
        
        start_time = time.time()
        
        # Process this chunk with threading (up to 10 threads)
        with ThreadPoolExecutor(max_workers=len(chunk)) as executor:
            futures = []
            
            for billing_result_id in chunk:
                future = executor.submit(
                    process_single_bill,
                    billing_result_id,
                    provider_name
                )
                futures.append(future)
            
            # Wait for all threads in this chunk to complete
            for future in futures:
                try:
                    future.result()  # This blocks until the thread completes
                except Exception as e:
                    print(f"❌ Thread error: {e}")
        
        elapsed = time.time() - start_time
        print(f"\n✅ Chunk {chunk_idx}/{total_chunks} completed in {elapsed:.2f} seconds")
    
    print(f"\n{'='*80}")
    print(f"🎉 Bulk extraction completed! Processed {len(billing_result_ids)} bills in {total_chunks} chunks")
    print(f"{'='*80}\n")


def process_single_bill(billing_result_id: str, provider_name: str):
    """Process a single bill extraction (to be run in a thread)"""
    import asyncio
    
    try:
        with get_db_context() as db:
            billing_result = db.query(BillingResult).filter(
                BillingResult.id == billing_result_id
            ).first()
            
            if billing_result:
                print(f"🔄 [{billing_result.original_filename}] Starting extraction...")
                asyncio.run(trigger_manual_bill_extraction(billing_result, provider_name))
                print(f"✅ [{billing_result.original_filename}] Extraction complete")
            else:
                print(f"❌ Billing result {billing_result_id} not found")
                
    except Exception as e:
        print(f"❌ [{billing_result_id}] Extraction failed: {e}")
        try:
            with get_db_context() as db:
                billing_result = db.query(BillingResult).filter(
                    BillingResult.id == billing_result_id
                ).first()
                if billing_result:
                    billing_result.status = "error"
                    db.commit()
        except:
            pass

