#!/usr/bin/env python3
"""
Simple startup script for the GPT Web Scraper FastAPI application
"""

import uvicorn
from main import app

if __name__ == "__main__":
    print("🚀 Starting GPT Web Scraper FastAPI...")
    print("📍 API will be available at: http://localhost:8000")
    print("📖 API documentation at: http://localhost:8000/docs")
    print("🔍 Health check at: http://localhost:8000/api/health")
    print("\nPress Ctrl+C to stop the server\n")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
