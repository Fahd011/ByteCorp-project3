"""
Xcel Energy bill extraction using RAG
"""

import tempfile
from typing import Dict, Any, List, Optional

from langchain_openai import AzureChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

from config import config
from app.schemas.xcel_bill_schema import UtilityBill, PremiseDetails, PremisesList
from app.extraction.vector_store import create_vector_store_from_pdf, cleanup_vector_store
from app.prompts.extraction_prompts import (
    XCEL_SUMMARY_PROMPT,
    XCEL_PREMISES_PROMPT,
    XCEL_PREMISE_DETAILS_PROMPT
)


def get_llm():
    """Create and return Azure OpenAI LLM instance"""
    return AzureChatOpenAI(
        azure_deployment=config.AZURE_CHAT_DEPLOYMENT_NAME,
        openai_api_version=config.AZURE_API_VERSION,
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        temperature=0
    )


def extract_bill_summary(vector_store: Chroma) -> Optional[UtilityBill]:
    """Extract bill summary information using RAG"""
    print(f"🔄 Running extraction for: {UtilityBill.__name__} (Summary)")
    
    all_chunks = vector_store.get(include=["documents"])
    context_text = "\n\n---\n\n".join([doc for doc in all_chunks['documents']])

    llm = get_llm()
    structured_llm = llm.with_structured_output(UtilityBill)
    
    prompt = ChatPromptTemplate.from_template(XCEL_SUMMARY_PROMPT)
    chain = prompt | structured_llm
    
    try:
        response = chain.invoke({"context": context_text})
        print(f"✅ Success for: {UtilityBill.__name__} (Summary)")
        return response
    except Exception as e:
        print(f"❌ Error during extraction for {UtilityBill.__name__}: {e}")
        return None


def get_all_premises_numbers(vector_store: Chroma) -> List[str]:
    """Find all unique premise numbers from the bill"""
    print("🔄 Finding all unique premise numbers...")
    
    all_chunks = vector_store.get(include=["documents"])
    context_text = "\n\n---\n\n".join([doc for doc in all_chunks['documents']])

    llm = get_llm()
    structured_llm = llm.with_structured_output(PremisesList)
    
    prompt = ChatPromptTemplate.from_template(XCEL_PREMISES_PROMPT)
    chain = prompt | structured_llm
    
    try:
        response = chain.invoke({"context": context_text})
        print(f"✅ Found {len(response.premise_numbers)} premises.")
        return response.premise_numbers
    except Exception as e:
        print(f"❌ Error finding premise numbers: {e}")
        return []


def extract_premise_details(premise_num: str, vector_store: Chroma) -> Optional[PremiseDetails]:
    """Extract detailed information for a single premise"""
    print(f"🔄 Extracting details for premise: {premise_num}...")
    
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 30})
    query = f"All details for premise {premise_num}, including electricity and natural gas charges, meter readings, and service address."
    relevant_chunks = retriever.invoke(query)
    context_text = "\n\n---\n\n".join([doc.page_content for doc in relevant_chunks])

    llm = get_llm()
    structured_llm = llm.with_structured_output(PremiseDetails)
    
    prompt = ChatPromptTemplate.from_template(XCEL_PREMISE_DETAILS_PROMPT)
    chain = prompt | structured_llm
    
    try:
        response = chain.invoke({"context": context_text, "premise_num": premise_num})
        print(f"✅ Success for premise: {premise_num}")
        return response
    except Exception as e:
        print(f"❌ Error during extraction for {premise_num}: {e}")
        return None


async def extract_xcel_from_pdf_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Main extraction function for Xcel Energy bills.
    
    Args:
        pdf_bytes: The PDF content as bytes
        
    Returns:
        Dictionary containing the extracted utility bill data
    """
    temp_dir = tempfile.mkdtemp(prefix="xcel_rag_extraction_")
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

        # Deduplicate premise numbers
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
        cleanup_vector_store(vector_store, temp_dir)

