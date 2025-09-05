from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, APIRouter
import json
import os
import tempfile
import shutil
from typing import List, Dict, Any
import PyPDF2
import openai
import pandas as pd
from datetime import datetime
import uuid
from pydantic import BaseModel
from azure_storage_service import azure_storage_service
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env")


router = APIRouter()

# Load data model
def load_data_model():
    """Load the data model from JSON file"""
    import os
    data_model_path = os.getenv("DATA_MODEL_PATH", "../data_model.json")
    try:
        with open(data_model_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Data model file not found at {data_model_path}")

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ExtractionResult(BaseModel):
    filename: str
    extracted_data: Dict[str, Any]
    status: str
    error: str = None

class BillingResultRequest(BaseModel):
    billing_result: Dict[str, Any]

# Store extraction results in memory (in production, use a database)
extraction_results: Dict[str, List[ExtractionResult]] = {}

def extract_text_from_pdf(pdf_file_path: str) -> str:
    """Extract text from PDF file using PyPDF2 with pdfplumber fallback"""
    try:
        # Try PyPDF2 first
        with open(pdf_file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"PyPDF2 failed, trying pdfplumber: {str(e)}")
        try:
            # Fallback to pdfplumber
            import pdfplumber
            with pdfplumber.open(pdf_file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
            return text
        except Exception as e2:
            raise HTTPException(status_code=400, detail=f"Error extracting text from PDF with both PyPDF2 and pdfplumber: {str(e2)}")

def extract_data_with_openai(text: str, data_model: dict) -> Dict[str, Any]:
    """Extract structured data from PDF text using OpenAI"""
    
    # Create a comprehensive prompt for data extraction
    prompt = f"""
    You are an expert at extracting structured data from utility bills. 
    
    Please extract the following information from the provided utility bill text and return it as a JSON object.
    
    Data Model:
    {json.dumps(data_model, indent=2)}
    
    Utility Bill Text:
    {text}
    
    Instructions:
    1. Extract all the information according to the data model structure
    2. Convert monetary amounts to numbers (remove $ and commas)
    3. Convert dates to MM/DD/YYYY format
    4. If a field is not found, set it to null
    5. Return ONLY valid JSON without any additional text or explanations
    
    Return the extracted data as a JSON object following the data model structure:
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a data extraction specialist. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        # Extract JSON from response
        content = response.choices[0].message.content.strip()
        
        # Try to parse the JSON response
        try:
            # Remove any markdown formatting if present
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            extracted_data = json.loads(content.strip())
            return extracted_data
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI response as JSON: {str(e)}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

@router.post("/api/pdf-extraction/upload")
async def upload_files(request: BillingResultRequest):
    """Process PDF from Azure blob storage using billing result data"""
    
    billing_result = request.billing_result
    azure_blob_name = billing_result.get("azure_blob_url")
    
    if not azure_blob_name:
        raise HTTPException(status_code=400, detail="No Azure blob name found in billing result")
    
    # Create a unique session ID for this batch
    session_id = billing_result.get("id");
    extraction_results[session_id] = []
    
    try:
        # Download PDF from Azure blob storage
        print(f"🔍 Downloading PDF from Azure blob: {azure_blob_name}")
        print(f"📋 Billing result data: {billing_result}")
        success, pdf_content = azure_storage_service.download_pdf_from_azure(azure_blob_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to download PDF from Azure blob: {azure_blob_name}")
        
        # Create bills directory if it doesn't exist
        bills_dir = Path("bills")
        bills_dir.mkdir(exist_ok=True)
        
        # Extract filename from blob name
        filename = azure_blob_name.split('/')[-1]
        
        # Save PDF content to bills folder
        pdf_file_path = bills_dir / filename
        with open(pdf_file_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        print(f" PDF saved to: {pdf_file_path}")
        
        # Extract text from PDF
        text = extract_text_from_pdf(str(pdf_file_path))
        
        # Load data model
        data_model = load_data_model()
        
        # Extract structured data using OpenAI
        extracted_data = extract_data_with_openai(text, data_model)
        
        # Store result with billing context
        result = ExtractionResult(
            filename=filename,
            extracted_data=extracted_data,
            status="success"
        )
        extraction_results[session_id].append(result)
        
        # Clean up the PDF file after processing
        os.unlink(pdf_file_path)
        print(f"🗑️ Deleted PDF file: {pdf_file_path}")
        
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