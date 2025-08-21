import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

def test_run_agent():
    """Test running the agent"""
    print("\n🚀 Testing agent run endpoint...")
    
    payload = {
        "user_creds": {
            "username": "testuser@example.com",
            "password": "testpass123"
        },
        "signin_url": "https://duke-energy.com/signin",
        "billing_history_url": "https://duke-energy.com/billing/history"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/agent/run", json=payload)
        print(f"✅ Agent run: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"❌ Agent run failed: {e}")
        return None

def test_stop_agent():
    """Test stopping the agent"""
    print("\n🛑 Testing agent stop endpoint...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/agent/stop")
        print(f"✅ Agent stop: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Agent stop failed: {e}")

def test_store_results():
    """Test storing agent results"""
    print("\n💾 Testing store results endpoint...")
    
    payload = {
        "pdf_content": b"dummy_pdf_content_for_testuser",
        "user_creds": {
            "username": "testuser@example.com",
            "password": "testpass123"
        },
        "timestamp": "2024-01-01T12:00:00"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/agent/results", json=payload)
        print(f"✅ Store results: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Store results failed: {e}")

def test_store_error():
    """Test storing agent errors"""
    print("\n❌ Testing store error endpoint...")
    
    payload = {
        "error_message": "Test error message",
        "user_creds": {
            "username": "testuser@example.com",
            "password": "testpass123"
        },
        "timestamp": "2024-01-01T12:00:00",
        "traceback": "Traceback (most recent call last):\n  File 'test.py', line 1, in <module>\n    raise Exception('Test error')\nException: Test error"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/agent/error", json=payload)
        print(f"✅ Store error: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Store error failed: {e}")

def main():
    """Run all tests"""
    print("🧪 Starting API tests...\n")
    
    # Test health first
    test_health()
    
    # Test running agent
    result = test_run_agent()
    
    if result and result.get("status") == "running":
        print("\n⏳ Waiting 3 seconds for agent to process...")
        time.sleep(3)
        
        # Test health while agent is running
        print("\n🔍 Testing health while agent is running...")
        test_health()
        
        # Test stopping agent
        test_stop_agent()
    
    # Test storing results and errors
    test_store_results()
    test_store_error()
    
    # Final health check
    print("\n🔍 Final health check...")
    test_health()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
