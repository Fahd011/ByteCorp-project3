from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, APIRouter
import json
import os
import tempfile
import shutil
from typing import List, Dict, Any, Optional
import PyPDF2
import openai
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
from openai import AzureOpenAI
from app.rag_extraction import extract_from_pdf_bytes
from config import config


router = APIRouter()

# --- PYDANTIC MODELS FOR DATA_MODEL.JSON SCHEMA ---

class Provider(BaseModel):
    name: str
    country: str

class BillingAddress(BaseModel):
    addressType: str = "FULL"
    streetLine1: str
    streetLine2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: str
    recipient: Optional[str] = None

class ServiceAddress(BaseModel):
    addressType: str = "FULL"
    streetLine1: str
    city: str
    state: str
    postalCode: str
    country: str

class ChargeItem(BaseModel):
    chargeNameAsPrinted: str
    chargeType: str = "DEBIT"
    chargeAmount: float
    chargeCurrencyCode: str = "USD"
    usageUnit: Optional[str] = None
    chargeRate: Optional[float] = None
    unitsPerRate: Optional[float] = None
    chargeGroupHeading: Optional[str] = None

class MeterCharge(BaseModel):
    chargeNameAsPrinted: str
    chargeAmount: float

class Usage(BaseModel):
    periodStartDate: str
    periodEndDate: str
    measuredUsage: float
    usageUnit: str
    numberOfDaysInPeriod: int

class MeterData(BaseModel):
    serviceType: str
    serviceAddress: ServiceAddress
    meterNumber: Optional[str] = None
    periodStartDate: str
    periodEndDate: str
    totalUsage: Optional[float] = None
    totalUsageUnit: Optional[str] = None
    demandKW: Optional[float] = None
    charges: List[MeterCharge] = []
    usages: List[Usage] = []

class AccountDataItem(BaseModel):
    accountNumber: str
    billingAddress: BillingAddress
    periodStartDate: str
    periodEndDate: str
    dueDate: str
    statementDate: Optional[str] = None
    disconnectDate: Optional[str] = None
    outstandingBalance: Optional[float] = None
    currencyCode: str = "USD"
    totalCharges: float
    meterData: List[MeterData] = []

class RemitToAddress(BaseModel):
    addressType: str = "FULL"
    streetLine1: str
    city: str
    state: str
    postalCode: str
    country: str

class PaymentCoupon(BaseModel):
    amountDue: float
    dueDate: str
    remitToAddress: RemitToAddress
    scanline: Optional[str] = None

class DisconnectNotice(BaseModel):
    pastDueAmount: Optional[float] = None
    disconnectDate: Optional[str] = None
    reconnectionFee: Optional[float] = None
    currencyCode: Optional[str] = None

class UtilityBillExtraction(BaseModel):
    type: str = "BILL"
    provider: Provider
    currencyCode: str = "USD"
    statementDate: str
    previousStatementDate: Optional[str] = None
    dueDate: str
    periodStartDate: str
    periodEndDate: str
    totalCharges: float
    amountDue: float
    previousBalance: Optional[float] = None
    lastPaymentAmount: Optional[float] = None
    lastPaymentDate: Optional[str] = None
    charges: List[ChargeItem] = []
    accountData: List[AccountDataItem] = []
    paymentCoupon: Optional[PaymentCoupon] = None
    disconnectNotice: Optional[DisconnectNotice] = None
    messages: List[str] = []
    dataIngestionMethod: Optional[str] = None
    sourceType: Optional[str] = None

# Note: Data model is now defined using Pydantic models above (UtilityBillExtraction)

# Initialize OpenAI client
openai_client = AzureOpenAI(
    api_key=config.AZURE_OPENAI_API_KEY,
    api_version=config.AZURE_API_VERSION,
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT
)

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

def extract_text_from_pdf(pdf_file_path: str) -> str:
    """Extract text from PDF file using pdfplumber first (preferred) with PyPDF2 fallback"""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_file_path) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages[:5]])
        # print(text)
        return text
    except Exception as e:
        print(f"pdfplumber failed, trying PyPDF2: {str(e)}")
        try:
            import PyPDF2
            with open(pdf_file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages[:5]:
                    text += page.extract_text() or ""
            return text
        except Exception as e2:
            raise HTTPException(
                status_code=400,
                detail=f"Error extracting text from PDF with both pdfplumber and PyPDF2: {str(e2)}"
            )

def extract_data_with_openai(text: str) -> Dict[str, Any]:
    """Extract structured data from PDF text using Azure OpenAI with structured output"""
    
    # Create a comprehensive prompt for data extraction
    prompt = f"""
You are an expert in extracting structured data from utility bills.

Your task:
- Extract bill data following the exact JSON schema structure.
- Capture all relevant entities:
  • Provider information (name, country)
  • Statement dates, due dates, period dates
  • Financial amounts (total charges, amount due, previous balance, payments)
  • Charges → each line item (customer charge, tiered energy charges, riders, late fees, taxes)
  • Account data with billing address
  • Meter data → meter number, service address, usage readings, charges per meter
  • Usages → start/end dates, measured usage, billed kWh/therms, number of days
  • Disconnect notices → past due amounts, disconnect dates, reconnection fees
  • Payment coupon → amount due, remit-to address, scanline
  • Messages or notices from the bill

Formatting Rules:
1. Monetary values → numbers only (remove $ and commas).
2. Dates → "YYYY-MM-DD" format.
3. If a field is missing or not found, omit it (use defaults defined in schema).
4. Taxes must be included as charges (e.g. "Sales Tax").
5. For serviceType, use: "ELECTRICITY", "GAS", or "WATER".
6. For chargeType, use: "DEBIT" or "CREDIT".

Utility Bill Text:
{text}
"""
    
    try:
        # Use Azure OpenAI with structured output (Pydantic model)
        response = openai_client.beta.chat.completions.parse(
            model=config.AZURE_CHAT_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a data extraction specialist for utility bills. Extract all information accurately following the schema."},
                {"role": "user", "content": prompt}
            ],
            response_format=UtilityBillExtraction,
            temperature=0.1
        )
        
        # Get the parsed structured output
        extracted_bill = response.choices[0].message.parsed
        
        if extracted_bill is None:
            raise HTTPException(status_code=500, detail="Failed to parse bill data from OpenAI response")
        
        # Convert Pydantic model to dict
        return extracted_bill.model_dump()
            
    except Exception as e:
        print(f"Error in extract_data_with_openai: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

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
        
        # Route to appropriate extraction method based on provider
        if provider_name == "Xcel Energy":
            print("🔄 Using RAG-based extraction for Xcel Energy")
            extracted_data = await extract_from_pdf_bytes(pdf_content)
        else:
            print("🔄 Using OpenAI extraction for standard providers")
            # Create bills directory if it doesn't exist
            bills_dir = Path("bills")
            bills_dir.mkdir(exist_ok=True)
            
            # Save PDF content to bills folder
            pdf_file_path = bills_dir / filename
            with open(pdf_file_path, 'wb') as pdf_file:
                pdf_file.write(pdf_content)
            
            print(f"📄 PDF saved to: {pdf_file_path}")
            
            # Extract text from PDF
            text = extract_text_from_pdf(str(pdf_file_path))
            
            # Extract structured data using Azure OpenAI
            extracted_data = extract_data_with_openai(text)
            
            # Clean up the PDF file after processing
            os.unlink(pdf_file_path)
            print(f"🗑️ Deleted PDF file: {pdf_file_path}")
        
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
        
        # Clean up PDF file if it was created
        if 'pdf_file_path' in locals():
            try:
                os.unlink(pdf_file_path)
                print(f"🗑️ Deleted PDF file after error: {pdf_file_path}")
            except:
                pass
        
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