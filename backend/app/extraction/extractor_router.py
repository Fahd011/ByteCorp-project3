"""
Main router for bill extraction based on provider
"""

from typing import Dict, Any

from app.extraction.xcel_extractor import extract_xcel_from_pdf_bytes
from app.extraction.duke_extractor import extract_duke_from_pdf_bytes
from app.extraction.green_mountain_extractor import extract_green_mountain_from_pdf_bytes
from app.extraction.centerpoint_extractor import extract_centerpoint_from_pdf_bytes


EXTRACTION_MAPPING = {
    "Xcel Energy": extract_xcel_from_pdf_bytes,
    "Duke Energy": extract_duke_from_pdf_bytes,
    "Green Mountain Energy": extract_green_mountain_from_pdf_bytes,
    "CenterPoint Energy": extract_centerpoint_from_pdf_bytes,
}


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
    
    for key, func in EXTRACTION_MAPPING.items():
        if key in provider_name:
            print(f"🔄 Using RAG extraction for {provider_name}")
            return await func(pdf_content)
    
    error_msg = f"No RAG extraction method configured for provider: {provider_name}"
    print(f"❌ {error_msg}")
    raise ValueError(error_msg)

