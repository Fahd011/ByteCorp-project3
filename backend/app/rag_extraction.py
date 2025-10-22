"""
RAG-based extraction for Xcel Energy utility bills using LangChain and ChromaDB.
"""

import os
import json
import tempfile
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path

from pydantic import BaseModel, Field

# LangChain components for RAG
from langchain_openai import ChatOpenAI
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
    chargeNameAsPrinted: str = Field(description="The description of the charge as printed on the bill (e.g., 'PREMISES DESCRIPTOR').")
    chargeAmount: float = Field(description="The monetary value of this specific charge.")
    chargeCurrencyCode: str = Field(description="Currency code for this charge, e.g., 'USD'.", default="USD")
    premisesNumber: Optional[str] = Field(description="The premises number associated with this charge, if available.", default=None)


class DisconnectNotice(BaseModel):
    """Information related to a disconnection notice, if present."""
    pastDueAmount: Optional[float] = Field(description="The overdue amount specified in the notice.", default=None)
    disconnectDate: Optional[str] = Field(description="The date of potential disconnection in YYYY-MM-DD format.", default=None)
    reconnectionFee: Optional[float] = Field(description="The fee to reconnect service.", default=None)
    currencyCode: Optional[str] = Field(description="Currency code for the fees, e.g., 'USD'.", default=None)


class PremiseLineItem(BaseModel):
    """A single detailed line item charge (e.g., 'Energy Charge Summer' or 'City Fees')."""
    description: str = Field(description="The description of the charge as printed, e.g., 'Basic Service Chg' or 'State Tax'.")
    usageUnits: Optional[str] = Field(description="The usage and units, e.g., '117 kWh' or '0 therms'.", default=None)
    rate: Optional[str] = Field(description="The rate applied, e.g., '$0.130690' or '6.000%'.", default=None)
    amount: float = Field(description="The final dollar amount for this line item.")


class ServiceBreakdown(BaseModel):
    """Details for a single service (Electricity or Gas) at a premise."""
    serviceType: str = Field(description="The type of service, e.g., 'ELECTRICITY' or 'NATURAL GAS'.")
    serviceAddress: str = Field(description="The full service address for this premise.")
    meterNumber: Optional[str] = Field(description="The meter number for this service.", default=None)
    readPeriod: Optional[str] = Field(description="The billing period for these charges, e.g., '08/25/25 - 09/25/25'.", default=None)
    lineItems: List[PremiseLineItem] = Field(description="A list of all detailed charges, including taxes.")
    total: float = Field(description="The total amount for this service (e.g., 'Total' for Electricity).")


class PremiseDetails(BaseModel):
    """All extracted details for a single, unique premise."""
    premisesNumber: str = Field(description="The unique identifier for the premise, e.g., '304679358'.")
    InvoiceNumber: str = Field(description="The invoice number for this service.")
    services: List[ServiceBreakdown] = Field(description="A list of service breakdowns (e.g., one for Electricity, one for Gas).")
    premisesTotal: float = Field(description="The final 'Premises Total' amount, which sums all services for this premise.")


class PremisesList(BaseModel):
    """A simple model to hold the list of all premise numbers found."""
    premise_numbers: List[str] = Field(description="A list of all unique premise numbers found in the document.")


class UtilityBill(BaseModel):
    """The complete, structured data extracted from a utility bill."""
    type: str = Field(description="The type of document.", default="BILL")
    provider: Provider
    currencyCode: str = Field(description="The main currency code for the bill, e.g., 'USD'.", default="USD")
    statementDate: str = Field(description="The main date of the bill statement in YYYY-MM-DD format.")
    previousStatementDate: Optional[str] = Field(description="The date of the previous statement in YYYY-MM-DD format.", default=None)
    dueDate: str = Field(description="The date by which the payment is due in YYYY-MM-DD format.")
    periodStartDate: Optional[str] = Field(description="The start date of the billing period in YYYY-MM-DD format.", default=None)
    periodEndDate: Optional[str] = Field(description="The end date of the billing period in YYYY-MM-DD format.", default=None)
    
    totalCharges: float = Field(description="The total of new charges for the current period (e.g., 'Current Charges').")
    amountDue: float = Field(description="The total amount due for this billing period (e.g., 'Amount Due').")
    previousBalance: Optional[float] = Field(description="The balance carried over from the previous statement.", default=None)
    lastPaymentAmount: Optional[float] = Field(description="The amount of the last payment received.", default=None)
    lastPaymentDate: Optional[str] = Field(description="The date the last payment was received in YYYY-MM-DD format.", default=None)

    accountData: List[AccountDataItem] = Field(description="A list of account data objects, typically containing one entry.")
    
    charges: List[ChargeItem] = Field(description="A detailed list of all line item charges from the 'Premises Summary' table.")
    
    premiseDetails: Optional[List[PremiseDetails]] = Field(
        description="A list of detailed breakdowns for each individual premise.", 
        default=None
    )


# --- EXTRACTION FUNCTIONS ---

def extract_bill_summary(vector_store: Chroma) -> Optional[UtilityBill]:
    """Uses RAG to find summary info and populate the main UtilityBill model."""
    print(f"🔄 Running extraction for: {UtilityBill.__name__} (Summary)")
    
    # Retrieve all chunks for comprehensive extraction
    all_chunks = vector_store.get(include=["documents"])
    context_text = "\n\n---\n\n".join([doc for doc in all_chunks['documents']])

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
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

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
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

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(PremiseDetails)
    
    prompt_template = """
    You will be given context from a utility bill that contains the detailed breakdown
    for a specific premise. Based ONLY on this context, extract the following
    information for PREMISE NUMBER: {premise_num}.
    
    1.  Find the 'ELECTRICITY SERVICE DETAILS' and 'NATURAL GAS SERVICE DETAILS'.
    2.  For each service, extract the invoice number, service address, meter number, and read period.
    3.  For each service, extract *all* line items from 'ELECTRICITY CHARGES'/'NATURAL GAS CHARGES'
        and all taxes (e.g., 'City Fees', 'State Tax').
    4.  Extract the 'Total' for each service.
    5.  Find the final 'Premises Total' for this premise (it's often at the end
        of the natural gas section).
    
    Format the output perfectly according to the JSON schema.

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
    
    embeddings = OpenAIEmbeddings(
        chunk_size=100  # Process up to 100 chunks per request
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

