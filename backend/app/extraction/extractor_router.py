"""
Main router for bill extraction based on provider
"""

from typing import Dict, Any

from app.extraction.xcel_extractor import extract_xcel_from_pdf_bytes
from app.extraction.duke_extractor import extract_duke_from_pdf_bytes


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
        return await extract_xcel_from_pdf_bytes(pdf_content)
    elif "Duke Energy" in provider_name:
        print("🔄 Using RAG extraction for Duke Energy (meter-based schema)")
        return await extract_duke_from_pdf_bytes(pdf_content)
    else:
        error_msg = f"No RAG extraction method configured for provider: {provider_name}"
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)

