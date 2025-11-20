"""
CenterPoint Energy bill extraction using RAG
"""

import tempfile
from typing import Dict, Any, Optional

from langchain_openai import AzureChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

from config import config
from app.extraction.vector_store import create_vector_store_from_pdf, cleanup_vector_store
from app.prompts.extraction_prompts import CENTERPOINT_SYSTEM_PROMPT, CENTERPOINT_EXTRACTION_PROMPT


def extract_centerpoint_bill_data(vector_store: Chroma) -> Optional[Dict[str, Any]]:
    """
    Extract complete CenterPoint Energy bill in single pass using RAG + structured output.
    Returns data matching the CenterPoint Energy schema (UtilityBillExtraction).
    """
    # Import CenterPoint schema
    from app.schemas.centerpoint_schema import UtilityBillExtraction as CenterPointUtilityBill
    
    # Create comprehensive prompt for CenterPoint-specific extraction
    prompt = ChatPromptTemplate.from_messages([
        ("system", CENTERPOINT_SYSTEM_PROMPT),
        ("human", CENTERPOINT_EXTRACTION_PROMPT)
    ])
    
    # Retrieve relevant chunks
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
    
    context = "\n\n".join([doc.page_content for doc in unique_docs[:20]])
    
    # Use Azure OpenAI with structured output
    llm = AzureChatOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        azure_deployment=config.AZURE_CHAT_DEPLOYMENT_NAME,
        api_version="2024-08-01-preview",
        temperature=0.1
    )
    
    structured_llm = llm.with_structured_output(CenterPointUtilityBill)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"context": context})
        print("✅ CenterPoint Energy bill data extracted successfully")
        return result.model_dump()
        
    except Exception as e:
        print(f"❌ Error extracting CenterPoint Energy bill data: {e}")
        import traceback
        traceback.print_exc()
        return None


async def extract_centerpoint_from_pdf_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    RAG extraction for CenterPoint Energy bills (meter-based).
    
    Args:
        pdf_bytes: The PDF content as bytes
        
    Returns:
        Dictionary containing the extracted CenterPoint Energy bill data
    """
    temp_dir = tempfile.mkdtemp(prefix="centerpoint_rag_extraction_")
    vector_store = None
    
    try:
        print(f"\n{'='*60}")
        print(f"Starting RAG extraction for CenterPoint Energy bill")
        print(f"Temporary directory: {temp_dir}")
        print(f"{'='*60}\n")
        
        # Create vector store from PDF
        vector_store = create_vector_store_from_pdf(pdf_bytes, temp_dir)
        
        # Single-pass extraction using CenterPoint Energy schema
        print("\n--- Extracting CenterPoint Energy Bill Data ---")
        centerpoint_bill_data = extract_centerpoint_bill_data(vector_store)
        
        if not centerpoint_bill_data:
            print("❌ Critical error: Failed to extract CenterPoint Energy bill data.")
            return {}
        
        print(f"\n{'='*60}")
        print(f"✅ CenterPoint Energy RAG extraction completed successfully")
        print(f"{'='*60}\n")
        
        return centerpoint_bill_data
        
    except Exception as e:
        print(f"\n❌ Error during CenterPoint Energy RAG extraction: {e}")
        import traceback
        traceback.print_exc()
        return {}
        
    finally:
        cleanup_vector_store(vector_store, temp_dir)

