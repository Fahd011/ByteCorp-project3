"""
Green Mountain Energy bill extraction using RAG
"""

import logging
import tempfile
from typing import Dict, Any, Optional

from langchain_openai import AzureChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

from config import config
from app.extraction.vector_store import create_vector_store_from_pdf, cleanup_vector_store
from app.prompts.extraction_prompts import GREEN_MOUNTAIN_SYSTEM_PROMPT, GREEN_MOUNTAIN_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


def extract_green_mountain_bill_data(vector_store: Chroma) -> Optional[Dict[str, Any]]:
    """
    Extract complete Green Mountain Energy bill in single pass using RAG + structured output.
    Returns data matching the Green Mountain Energy schema (UtilityBillExtraction).
    """
    # Import Green Mountain schema
    from app.schemas.green_mountain_schema import UtilityBillExtraction as GreenMountainUtilityBill
    
    # Create comprehensive prompt for Green Mountain-specific extraction
    prompt = ChatPromptTemplate.from_messages([
        ("system", GREEN_MOUNTAIN_SYSTEM_PROMPT),
        ("human", GREEN_MOUNTAIN_EXTRACTION_PROMPT)
    ])
    
    # Use all chunks for comprehensive context (important for multi-meter bills)
    all_chunks = vector_store.get(include=["documents"])
    context_text = "\n\n---\n\n".join([doc for doc in all_chunks['documents']])
    logger.info(f"Context created with {len(all_chunks['documents'])} chunks.")
    
    # Use Azure OpenAI with structured output
    llm = AzureChatOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        azure_deployment=config.AZURE_CHAT_DEPLOYMENT_NAME,
        api_version="2024-08-01-preview",
        temperature=0
    )
    
    structured_llm = llm.with_structured_output(GreenMountainUtilityBill)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"context": context_text})
        logger.info("Green Mountain Energy bill data extracted successfully")
        return result.model_dump()
        
    except Exception:
        logger.exception("Error extracting Green Mountain Energy bill data")
        return None


async def extract_green_mountain_from_pdf_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    RAG extraction for Green Mountain Energy bills (meter-based with table enhancement).
    
    Args:
        pdf_bytes: The PDF content as bytes
        
    Returns:
        Dictionary containing the extracted Green Mountain Energy bill data
    """
    temp_dir = tempfile.mkdtemp(prefix="green_mountain_rag_extraction_")
    vector_store = None
    
    try:
        logger.info("="*60)
        logger.info("Starting RAG extraction for Green Mountain Energy bill")
        logger.info(f"Temporary directory: {temp_dir}")
        logger.info("="*60)
        
        # Create vector store from PDF with table enhancement for Page 2
        vector_store = create_vector_store_from_pdf(
            pdf_bytes, 
            temp_dir,
            enhance_tables=True,
            table_pages=[1]  # Page 2 (0-indexed) contains the charges table
        )
        
        # Single-pass extraction using Green Mountain schema
        logger.info("Extracting Green Mountain Energy Bill Data")
        green_mountain_bill_data = extract_green_mountain_bill_data(vector_store)
        
        if not green_mountain_bill_data:
            logger.error("Critical error: Failed to extract Green Mountain Energy bill data.")
            return {}
        
        logger.info("="*60)
        logger.info("Green Mountain Energy RAG extraction completed successfully")
        logger.info("="*60)
        
        return green_mountain_bill_data
        
    except Exception:
        logger.exception("Error during Green Mountain Energy RAG extraction")
        return {}
        
    finally:
        cleanup_vector_store(vector_store, temp_dir)

