#!/usr/bin/env python3
"""
Script to start both the backend and frontend servers
"""
import subprocess
import sys
import os
import time
from pathlib import Path

def start_backend():
    """Start the Flask backend server"""
    backend_dir = Path("ByteCorp-project3")
    if not backend_dir.exists():
        print("❌ Backend directory not found!")
        return None
    
    print("🚀 Starting backend server...")
    try:
        # Change to backend directory and start Flask app
        process = subprocess.Popen(
            [sys.executable, "backend/app.py"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Backend server started on http://localhost:5000")
        return process
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return None

def start_frontend():
    """Start the React frontend server"""
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return None
    
    print("🚀 Starting frontend server...")
    try:
        # Change to frontend directory and start React app
        process = subprocess.Popen(
            ["npm", "start"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Frontend server started on http://localhost:3000")
        return process
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return None

def main():
    print("🎯 Sagiliti Application Starter")
    print("=" * 40)
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("❌ Cannot start frontend without backend")
        return
    
    # Wait a moment for backend to initialize
    time.sleep(2)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print("❌ Failed to start frontend")
        backend_process.terminate()
        return
    
    print("\n🎉 Both servers are running!")
    print("📱 Frontend: http://localhost:3000")
    print("🔧 Backend: http://localhost:5000")
    print("\nPress Ctrl+C to stop both servers")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        print("✅ Servers stopped")

if __name__ == "__main__":
    main()
