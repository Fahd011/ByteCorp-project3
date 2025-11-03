"""
RAG-based extraction for Xcel Energy utility bills using LangChain and ChromaDB.
"""

import os
import json
import tempfile
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
from config import config
from pydantic import BaseModel, Field

# LangChain components for RAG
from langchain_openai import ChatOpenAI, AzureChatOpenAI

# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


# --- PYDANTIC MODELS ---

class Provider(BaseModel):
    """Information about the utility provider."""
    name: str = Field(description="The name of the utility provider, e.g., 'Xcel Energy'.")
    country: str = Field(description="The country where the provider operates, e.g., 'USA'.")


class BillingAddress(BaseModel):
    """Represents a billing address."""
    addressType: str = Field(description="Type of address, e.g., 'FULL' or 'PARTIAL'.", default="FULL")
    streetLine1: str = Field(description="The primary street address line.")
    streetLine2: Optional[str] = Field(description="The secondary street address line (if any).", default=None)
    city: Optional[str] = Field(description="The city of the address.", default=None)
    state: Optional[str] = Field(description="The state or province of the address.", default=None)
    postalCode: Optional[str] = Field(description="The postal or ZIP code.", default=None)
    country: str = Field(description="The country of the address, e.g., 'USA'.")
    recipient: Optional[str] = Field(description="The name of the person or company receiving the bill.", default=None)


class AccountDataItem(BaseModel):
    """A single account data entry."""
    accountNumber: str = Field(description="The unique account number for the customer.")
    billingAddress: BillingAddress


class ChargeItem(BaseModel):
    """A single line item from the *summary* charges table."""
    chargeNameAsPrinted: str = Field(description="The description of the charge as printed on the bill (e.g., 'Electricity Service').")
    chargeAmount: float = Field(description="The monetary value of this specific charge.")
    chargeCurrencyCode: str = Field(description="Currency code for this charge, e.g., 'USD'.", default="USD")
    premisesNumber: Optional[str] = Field(description="The premises number associated with this charge, if available.", default=None)


class DisconnectNotice(BaseModel):
    """Information related to a disconnection notice, if present."""
    pastDueAmount: Optional[float] = Field(default=None)
    disconnectDate: Optional[str] = Field(default=None)
    reconnectionFee: Optional[float] = Field(default=None)
    currencyCode: Optional[str] = Field(default=None)


# --- SERVICE-SPECIFIC DETAILS ---

class PremiseLineItem(BaseModel):
    """A single detailed line item charge (e.g., 'Energy Charge Summer')."""
    description: str
    usageUnits: Optional[str] = None
    rate: Optional[str] = None
    amount: float


class MeterReading(BaseModel):
    """Detailed meter reading information for a specific service."""
    meterNumber: str
    usageType: Optional[str] = None
    previousReading: Optional[float] = None
    currentReading: Optional[float] = None
    usage: Optional[float] = None
    usageUnits: Optional[str] = None
    readStartDate: Optional[str] = None
    readEndDate: Optional[str] = None
    readDays: Optional[int] = None
    nextReadDate: Optional[str] = None


class GasAdjustmentItem(BaseModel):
    """Conversion or adjustment factors for natural gas readings."""
    description: str
    formula: Optional[str] = None
    resultValue: Optional[float] = None
    resultUnits: Optional[str] = None


class UsageSummary(BaseModel):
    """Summary of usage averages for electricity/gas."""
    category: str
    currentUsage: Optional[float] = None
    previousUsage: Optional[float] = None
    currentCost: Optional[float] = None
    previousCost: Optional[float] = None
    currentTemperature: Optional[float] = None
    previousTemperature: Optional[float] = None


class ServiceBreakdown(BaseModel):
    """Details for a single service (Electricity or Gas) at a premise."""
    InvoiceNumber: str
    serviceType: str
    serviceAddress: str
    meterNumber: Optional[str] = None
    readStartDate: Optional[str] = None
    readEndDate: Optional[str] = None
    readDays: Optional[int] = None
    total: float
    lineItems: List[PremiseLineItem]
    

    # Nested service-specific data
    meterReadings: Optional[List[MeterReading]] = None
    gasAdjustments: Optional[List[GasAdjustmentItem]] = None
    usageSummary: Optional[List[UsageSummary]] = None


class PremiseDetails(BaseModel):
    """All extracted details for a single, unique premise."""
    premisesNumber: str
    premisesTotal: float
    services: List[ServiceBreakdown]


class PremisesList(BaseModel):
    """Holds the list of all premise numbers found."""
    premise_numbers: List[str]


# --- EXTENDED SECTIONS ---

class PaymentInfo(BaseModel):
    """Represents how the customer pays their bill."""
    paymentMethod: Optional[str] = None
    autoPay: Optional[bool] = None
    remitToAddress: Optional[str] = None


class ContactInfo(BaseModel):
    """Contact details for customer support."""
    phoneNumber: Optional[str] = None
    faxNumber: Optional[str] = None
    website: Optional[str] = None
    mailingAddress: Optional[str] = None


class NoticeInfo(BaseModel):
    """Informational or regulatory notices printed on the bill."""
    title: Optional[str] = None
    message: str
    referenceURL: Optional[str] = None


# --- FINAL MASTER MODEL ---

class UtilityBill(BaseModel):
    """The complete, structured data extracted from a utility bill."""
    type: str = Field(default="BILL")
    provider: Provider
    currencyCode: str = Field(default="USD")

    statementNumber: str
    statementDate: str
    previousStatementDate: Optional[str] = None
    dueDate: str
    periodStartDate: Optional[str] = None
    periodEndDate: Optional[str] = None

    totalCharges: float
    amountDue: float
    previousBalance: Optional[float] = None
    lastPaymentAmount: Optional[float] = None
    lastPaymentDate: Optional[str] = None

    accountData: List[AccountDataItem]
    charges: List[ChargeItem]
    premiseDetails: Optional[List[PremiseDetails]] = None

    # Optional extended fields
    paymentInfo: Optional[PaymentInfo] = None
    contactInfo: Optional[ContactInfo] = None
    notices: Optional[List[NoticeInfo]] = None
    disconnectNotice: Optional[DisconnectNotice] = None

    
    # --- NEWLY ADDED FIELD ---
    # This will be populated manually in the main() function after the initial extraction.
    premiseDetails: Optional[List[PremiseDetails]] = Field(
        description="A list of detailed breakdowns for each individual premise.", 
        default=None
    )

# --- EXTRACTION FUNCTIONS ---

# Azure OpenAI Configuration for chat models
AZURE_OPENAI_ENDPOINT = config.AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY = config.AZURE_OPENAI_API_KEY
AZURE_CHAT_DEPLOYMENT_NAME = config.AZURE_CHAT_DEPLOYMENT_NAME
AZURE_API_VERSION = config.AZURE_API_VERSION

def extract_bill_summary(vector_store: Chroma) -> Optional[UtilityBill]:
    """Uses RAG to find summary info and populate the main UtilityBill model."""
    print(f"🔄 Running extraction for: {UtilityBill.__name__} (Summary)")
    
    # Retrieve all chunks for comprehensive extraction
    all_chunks = vector_store.get(include=["documents"])
    context_text = "\n\n---\n\n".join([doc for doc in all_chunks['documents']])

    # llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    llm = AzureChatOpenAI(
        azure_deployment=AZURE_CHAT_DEPLOYMENT_NAME,
        openai_api_version=AZURE_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        temperature=0
    )
    structured_llm = llm.with_structured_output(UtilityBill)
    
    prompt_template = """
    Based ONLY on the following context from a single utility bill, extract ALL requested information.
    Fill out the entire JSON schema provided.
    
    - For `totalCharges`, use the 'Current Charges' value.
    - For `amountDue`, use the 'Amount Due' value.
    - `charges` should be a list of ALL line items from the 'PREMISES SUMMARY' table.
    - Infer dates like `previousStatementDate` from context (e.g., 'As of 08/26' for previous balance).
    - If a payment was received, extract the amount. If it says 'No Payments Received', `lastPaymentAmount` should be 0.0.
    - If no information is present for a field, leave it as null (it will be handled by the schema).
    - The bill is from the USA, so the currency is 'USD' and country is 'USA'.
    - DO NOT attempt to fill in 'premiseDetails'. Leave it as null.

    Context:
    {context}
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | structured_llm
    
    try:
        response = chain.invoke({"context": context_text})
        print(f"✅ Success for: {UtilityBill.__name__} (Summary)")
        return response
    except Exception as e:
        print(f"❌ Error during extraction for {UtilityBill.__name__}: {e}")
        return None


def get_all_premises_numbers(vector_store: Chroma) -> List[str]:
    """
    Query the document to find all unique premise numbers
    from the summary page.
    """
    print("🔄 Finding all unique premise numbers...")
    
    all_chunks = vector_store.get(include=["documents"])
    context_text = "\n\n---\n\n".join([doc for doc in all_chunks['documents']])

    # llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    llm = AzureChatOpenAI(
        azure_deployment=AZURE_CHAT_DEPLOYMENT_NAME,
        openai_api_version=AZURE_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        temperature=0
    )
    structured_llm = llm.with_structured_output(PremisesList)
    
    prompt_template = """
    Based ONLY on the provided context, find the 'PREMISES SUMMARY' table.
    Extract *all* of the 'PREMISES NUMBER' values from that table.
    Return only the list of premise number strings.

    Context:
    {context}
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | structured_llm
    
    try:
        response = chain.invoke({"context": context_text})
        print(f"✅ Found {len(response.premise_numbers)} premises.")
        return response.premise_numbers
    except Exception as e:
        print(f"❌ Error finding premise numbers: {e}")
        return []


def extract_premise_details(premise_num: str, vector_store: Chroma) -> Optional[PremiseDetails]:
    """
    For a single premise number, find its detailed breakdown pages
    and extract all information into the PremiseDetails model.
    """
    print(f"🔄 Extracting details for premise: {premise_num}...")
    
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 30})
    query = f"All details for premise {premise_num}, including electricity and natural gas charges, meter readings, and service address."
    relevant_chunks = retriever.invoke(query)
    context_text = "\n\n---\n\n".join([doc.page_content for doc in relevant_chunks])

    # llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    llm = AzureChatOpenAI(
        azure_deployment=AZURE_CHAT_DEPLOYMENT_NAME,
        openai_api_version=AZURE_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        temperature=0
    )
    structured_llm = llm.with_structured_output(PremiseDetails)
    
    prompt_template = """
    You will be given context from a utility bill that contains the detailed breakdown
    for a specific premise. Based ONLY on this context, extract the following
    information for PREMISE NUMBER: {premise_num}.

    1.  Find the 'ELECTRICITY SERVICE DETAILS' and 'NATURAL GAS SERVICE DETAILS'.
    2.  For each service, extract:
        - Invoice number
        - Service address
        - Meter number
        - Read period or read start/end dates (e.g., '08/25/25 - 09/24/25').
    3.  For each service, extract all line items under 'ELECTRICITY CHARGES' or 'NATURAL GAS CHARGES',
        including all taxes (City Fees, State Tax, etc.).
    4.  Extract the 'Total' for each service.
    5.  Extract the 'Premises Total' for this premise (usually at the end of the gas section).
    6.  Also extract the 'YOUR MONTHLY ELECTRICITY USAGE' and 'YOUR MONTHLY NATURAL GAS USAGE'
        daily averages section found near the graphs at the top of each page.
        - For each category, extract:
            • Temperature (this year and last year)
            • Usage (Electricity kWh / Gas Therms)
            • Cost ($)
        - Map these to the following fields:
            category: 'Electricity' or 'Gas'
            currentUsage, previousUsage, currentCost, previousCost, currentTemperature, previousTemperature
    7.  Ensure that these are stored in the nested field 'usageSummary' under each corresponding service.
    8.  Return the result in the exact JSON schema provided.
        
    Context:
    {context}
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | structured_llm
    
    try:
        response = chain.invoke({"context": context_text, "premise_num": premise_num})
        print(f"✅ Success for premise: {premise_num}")
        return response
    except Exception as e:
        print(f"❌ Error during extraction for {premise_num}: {e}")
        return None


def create_vector_store_from_pdf(pdf_bytes: bytes, temp_dir: str) -> Chroma:
    """
    Create a Chroma vector store from PDF bytes.
    
    Args:
        pdf_bytes: The PDF content as bytes
        temp_dir: Temporary directory to store the PDF and Chroma DB
        
    Returns:
        Chroma vector store instance
    """
    # Save PDF to temporary file
    pdf_path = Path(temp_dir) / "temp_bill.pdf"
    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)
    
    # Load PDF documents
    print(f"📄 Loading PDF from temporary file...")
    loader = PyPDFLoader(str(pdf_path))
    documents = loader.load()
    print(f"✅ Loaded {len(documents)} pages from PDF")
    
    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✅ Split into {len(chunks)} chunks")
    
    # Create Chroma database in temp directory
    chroma_path = Path(temp_dir) / "chroma"
    print(f"🔄 Creating embeddings for {len(chunks)} chunks...")
    
    # embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        chunk_size=100
    )
    
    db = Chroma.from_documents(
        chunks, embeddings, persist_directory=str(chroma_path)
    )
    print(f"✅ Vector store created at {chroma_path}")
    
    return db


async def extract_from_pdf_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Main extraction function that processes PDF bytes and returns extracted data.
    
    Args:
        pdf_bytes: The PDF content as bytes
        
    Returns:
        Dictionary containing the extracted utility bill data
    """
    # Create temporary directory for this extraction
    temp_dir = tempfile.mkdtemp(prefix="rag_extraction_")
    vector_store = None
    
    try:
        print(f"\n{'='*60}")
        print(f"Starting RAG extraction for Xcel Energy bill")
        print(f"Temporary directory: {temp_dir}")
        print(f"{'='*60}\n")
        
        # Create vector store from PDF
        vector_store = create_vector_store_from_pdf(pdf_bytes, temp_dir)
        
        # Step 1: Extract the Bill Summary
        print("\n--- 1. Extracting Bill Summary ---")
        final_bill = extract_bill_summary(vector_store)
        
        if not final_bill:
            print("❌ Critical error: Failed to extract bill summary.")
            return {}
        
       # Step 2: Get the list of all premises to process
        print("\n--- 2. Finding Premise Numbers ---")
        premise_numbers = get_all_premises_numbers(vector_store)

        # Deduplicate premise numbers in case the LLM returns duplicates
        if premise_numbers:
            premise_numbers = list(set(premise_numbers))
            print(f"✅ After deduplication: {len(premise_numbers)} unique premises.")
        
        all_details = []
        if not premise_numbers:
            print("⚠️ Warning: No premise numbers found. The final JSON will only contain summary data.")
        else:
            # Step 3: Loop and extract details for each premise
            print(f"\n--- 3. Extracting Details for {len(premise_numbers)} Premises ---")
            for num in premise_numbers:
                details = extract_premise_details(num, vector_store)
                if details:
                    all_details.append(details)
            print(f"--- ✅ Successfully extracted details for {len(all_details)} premises ---")
        
        # Step 4: Combine Summary and Details
        print("\n--- 4. Combining Summary and Details ---")
        final_bill.premiseDetails = all_details
        
        # Convert to dictionary
        result = final_bill.model_dump()
        
        print(f"\n{'='*60}")
        print(f"✅ RAG extraction completed successfully")
        print(f"{'='*60}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error during RAG extraction: {e}")
        import traceback
        traceback.print_exc()
        return {}
        
    finally:
        try:
            if vector_store is not None:
                try:
                    vector_store.delete_collection()
                except:
                    pass
                
                # Clear cache and delete reference
                if hasattr(vector_store, '_client'):
                    try:
                        vector_store._client.clear_system_cache()
                    except:
                        pass
                
                del vector_store
            
            # Garbage collection
            import gc
            gc.collect()
            
            # Platform-specific delay
            import time
            import platform
            delay = 1.5 if platform.system() == "Windows" else 0.3
            time.sleep(delay)
            
            # Delete directory
            shutil.rmtree(temp_dir, ignore_errors=True)  # ignore_errors works well on Linux
            print(f"🗑️ Cleaned up temporary directory: {temp_dir}")
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to cleanup {temp_dir}: {e}")


# ============================================================================
# SHARED EXTRACTION ROUTER
# ============================================================================

async def extract_bill_by_provider(provider_name: str, pdf_content: bytes) -> Dict[str, Any]:
    """
    Route to appropriate RAG extraction method based on provider.
    
    Args:
        provider_name: Name of the utility provider
        pdf_content: PDF file content as bytes
        
    Returns:
        Dictionary containing extracted bill data
        
    Raises:
        ValueError: If no extraction method is configured for the provider
    """
    print(f"🏢 Provider: {provider_name}")
    
    if provider_name == "Xcel Energy":
        print("🔄 Using RAG extraction for Xcel Energy (premise-based schema)")
        return await extract_from_pdf_bytes(pdf_content)
    elif "Duke Energy" in provider_name:
        print("🔄 Using RAG extraction for Duke Energy (meter-based schema)")
        return await extract_duke_from_pdf_bytes(pdf_content)
    else:
        error_msg = f"No RAG extraction method configured for provider: {provider_name}"
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)


# ============================================================================
# DUKE ENERGY RAG EXTRACTION (Meter-based, no premises)
# ============================================================================

async def extract_duke_from_pdf_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    RAG extraction for Duke Energy bills (meter-based, no premises).
    Uses the same RAG approach but with Duke's simpler schema structure.
    
    Args:
        pdf_bytes: The PDF content as bytes
        
    Returns:
        Dictionary containing the extracted Duke Energy bill data
    """
    # Create temporary directory for this extraction
    temp_dir = tempfile.mkdtemp(prefix="duke_rag_extraction_")
    vector_store = None
    
    try:
        print(f"\n{'='*60}")
        print(f"Starting RAG extraction for Duke Energy bill")
        print(f"Temporary directory: {temp_dir}")
        print(f"{'='*60}\n")
        
        # Create vector store from PDF
        vector_store = create_vector_store_from_pdf(pdf_bytes, temp_dir)
        
        # Single-pass extraction using Duke schema
        print("\n--- Extracting Duke Energy Bill Data ---")
        duke_bill_data = extract_duke_bill_data(vector_store)
        
        if not duke_bill_data:
            print("❌ Critical error: Failed to extract Duke bill data.")
            return {}
        
        print(f"\n{'='*60}")
        print(f"✅ Duke RAG extraction completed successfully")
        print(f"{'='*60}\n")
        
        return duke_bill_data
        
    except Exception as e:
        print(f"\n❌ Error during Duke RAG extraction: {e}")
        import traceback
        traceback.print_exc()
        return {}
        
    finally:
        # Cleanup: Properly close ChromaDB client before deleting files
        try:
            if vector_store is not None:
                # Delete the collection and close the client
                try:
                    vector_store.delete_collection()
                except:
                    pass
                
                # Access the underlying client and reset
                if hasattr(vector_store, '_client'):
                    try:
                        vector_store._client.clear_system_cache()
                    except:
                        pass
            
            # Small delay to ensure file handles are released on Windows
            import time
            time.sleep(0.5)
            
            # Remove temporary directory
            shutil.rmtree(temp_dir)
            print(f"🗑️ Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"⚠️ Warning: Failed to cleanup temporary directory {temp_dir}: {e}")
            print(f"   You may need to manually delete this directory later.")


def extract_duke_bill_data(vector_store: Chroma) -> Optional[Dict[str, Any]]:
    """
    Extract complete Duke Energy bill in single pass using RAG + structured output.
    Returns data matching the Duke/OpenAI schema (UtilityBillExtraction).
    """
    
    # Import Duke schema from pdf_extraction dynamically to avoid circular imports
    from app.routes.pdf_extraction import UtilityBillExtraction as DukeUtilityBill
    
    # Create comprehensive prompt for Duke-specific extraction
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting structured data from Duke Energy utility bills.

Extract ALL information following the exact schema structure provided. Be thorough and accurate.

Key sections to extract:
1. Provider information (name, country)
2. Statement dates, due dates, period dates
3. Financial amounts (total charges, amount due, previous balance, payments)
4. Charges → each line item (customer charge, energy charges by tier, riders, late fees, taxes)
5. Account data with billing address
6. Meter data → for each meter: meter number, service address, usage readings, charges per meter
7. Usages → start/end dates, measured usage, billed kWh/therms, number of days
8. Disconnect notices → past due amounts, disconnect dates, reconnection fees if present
9. Payment coupon → amount due, remit-to address, scanline
10. Messages or notices from the bill

Formatting Rules:
- Monetary values → numbers only (remove $ and commas)
- Dates → "YYYY-MM-DD" format
- If a field is missing or not found, omit it
- Taxes must be included as charges (e.g. "Sales Tax")
- For serviceType, use: "ELECTRICITY", "GAS", or "WATER"
- For chargeType, use: "DEBIT" or "CREDIT"
"""),
        ("human", "Extract all data from this Duke Energy utility bill:\n\n{context}")
    ])
    
    # Retrieve relevant chunks - get more context for Duke bills
    retriever = vector_store.as_retriever(search_kwargs={"k": 15})
    
    # Get comprehensive context
    queries = [
        "Extract all bill information including charges, totals, dates, and account details",
        "Extract meter readings, usage information, and service addresses",
        "Extract payment information, notices, and any disconnect warnings"
    ]
    
    all_docs = []
    for query in queries:
        docs = retriever.invoke(query)
        all_docs.extend(docs)
    
    # Deduplicate documents by content
    seen_content = set()
    unique_docs = []
    for doc in all_docs:
        if doc.page_content not in seen_content:
            seen_content.add(doc.page_content)
            unique_docs.append(doc)
    
    context = "\n\n".join([doc.page_content for doc in unique_docs[:20]])  # Use top 20 unique chunks
    
    # Use Azure OpenAI with structured output
    llm = AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        azure_deployment=AZURE_CHAT_DEPLOYMENT_NAME,
        api_version="2024-08-01-preview",
        temperature=0.1
    )
    
    structured_llm = llm.with_structured_output(DukeUtilityBill)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"context": context})
        print("✅ Duke bill data extracted successfully")
        
        # Convert Pydantic model to dict
        return result.model_dump()
        
    except Exception as e:
        print(f"❌ Error extracting Duke bill data: {e}")
        import traceback
        traceback.print_exc()
        return None

