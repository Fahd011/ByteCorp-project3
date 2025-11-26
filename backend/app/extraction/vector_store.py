"""
Vector store creation and management for RAG-based extraction
"""

import tempfile
import shutil
import time
import platform
import gc
from pathlib import Path
from typing import Optional, List

from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import config


def table_to_markdown(table_data: List[List[str]]) -> str:
    """
    Converts a list-of-lists table into a clean Markdown table string.
    Used for enhanced table extraction for providers with complex tables.
    """
    if not table_data or len(table_data) < 2:
        return ""
    
    # Clean and flatten the data
    cleaned_data = []
    for row in table_data:
        # Replace None with "-" for clarity
        cleaned_row = [str(cell).strip() if cell else "-" for cell in row]
        cleaned_data.append(cleaned_row)

    # Calculate max width for each column (ensures proper alignment)
    col_widths = [max(len(str(item)) for item in col) for col in zip(*cleaned_data)]

    markdown_output = []
    
    # 1. Header Row
    header = " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(cleaned_data[0]))
    markdown_output.append(f"| {header} |")
    
    # 2. Separator Row
    separator = " | ".join('-' * width for width in col_widths)
    markdown_output.append(f"| {separator} |")
    
    # 3. Data Rows
    for row in cleaned_data[1:]:
        data_row = " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))
        markdown_output.append(f"| {data_row} |")
        
    return "\n".join(markdown_output)


def create_vector_store_from_pdf(
    pdf_bytes: bytes, 
    temp_dir: str,
    enhance_tables: bool = False,
    table_pages: Optional[List[int]] = None
) -> Chroma:
    """
    Create a Chroma vector store from PDF bytes.
    
    Args:
        pdf_bytes: The PDF content as bytes
        temp_dir: Temporary directory to store the PDF and Chroma DB
        enhance_tables: If True, extract tables as clean markdown (for complex tables)
        table_pages: List of page indices (0-based) to extract tables from
        
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
    
    # Enhanced table extraction (BEFORE chunking)
    if enhance_tables and table_pages:
        try:
            import pdfplumber
            print(f"🔄 Extracting tables from pages {table_pages} using PDFPlumber...")
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx in table_pages:
                    if page_idx < len(pdf.pages):
                        page = pdf.pages[page_idx]
                        tables = page.extract_tables()
                        if tables:
                            # Extract first table on the page
                            markdown_table = table_to_markdown(tables[0])
                            documents.append(Document(
                                page_content=f"***CLEAN MARKDOWN TABLE (Page {page_idx + 1})***\n{markdown_table}",
                                metadata={"source": "table_extract", "page": page_idx}
                            ))
                            print(f"✅ Extracted table from page {page_idx + 1}")
        except ImportError:
            print("⚠️ pdfplumber not installed, skipping table enhancement")
        except Exception as e:
            print(f"⚠️ Error extracting tables: {e}")
    
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
    
    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        azure_deployment=config.AZURE_EMBEDDING_DEPLOYMENT_NAME,
        api_version=config.AZURE_API_VERSION,
        chunk_size=100
    )
    
    db = Chroma.from_documents(
        chunks, embeddings, persist_directory=str(chroma_path)
    )
    print(f"✅ Vector store created at {chroma_path}")
    
    return db


def cleanup_vector_store(vector_store: Optional[Chroma], temp_dir: str):
    """
    Properly cleanup vector store and temporary directory.
    
    Args:
        vector_store: The Chroma vector store instance to cleanup
        temp_dir: Temporary directory path to remove
    """
    try:
        if vector_store is not None:
            try:
                vector_store.delete_collection()
            except:
                pass
            
            if hasattr(vector_store, '_client'):
                try:
                    vector_store._client.clear_system_cache()
                except:
                    pass
            
            del vector_store
        
        # Garbage collection
        gc.collect()
        
        # Platform-specific delay
        delay = 1.5 if platform.system() == "Windows" else 0.3
        time.sleep(delay)
        
        # Delete directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"🗑️ Cleaned up temporary directory: {temp_dir}")
        
    except Exception as e:
        print(f"⚠️ Warning: Failed to cleanup {temp_dir}: {e}")

