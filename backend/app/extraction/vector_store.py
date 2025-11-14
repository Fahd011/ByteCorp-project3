"""
Vector store creation and management for RAG-based extraction
"""

import tempfile
import shutil
import time
import platform
import gc
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import config


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

