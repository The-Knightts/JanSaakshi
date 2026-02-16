"""
Quick test script for main_real_app.py
Run this to verify the API is working correctly
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("=" * 60)
    print("Testing /health endpoint...")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_ask():
    """Test ask endpoint"""
    print("=" * 60)
    print("Testing /ask endpoint...")
    print("=" * 60)
    
    # Test 1: Simple query
    print("\n1. Simple query:")
    response = requests.post(f"{BASE_URL}/ask", json={
        "question": "What meetings are available?"
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"Meetings found: {data.get('count')}")
    if data.get('summary'):
        print(f"Summary preview: {data.get('summary')[:200]}...")
    print()
    
    # Test 2: Query with custom prompt
    print("\n2. Query with custom prompt:")
    response = requests.post(f"{BASE_URL}/ask", json={
        "question": "Bombay Gymkhana",
        "prompt": "What infrastructure projects were discussed?"
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"Meetings found: {data.get('count')}")
    print()

def test_list_meetings():
    """Test meetings list endpoint"""
    print("=" * 60)
    print("Testing /meetings endpoint...")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/meetings?limit=5")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"Meetings count: {data.get('count')}")
    
    if data.get('meetings'):
        print("\nFirst meeting:")
        meeting = data['meetings'][0]
        print(f"  ID: {meeting.get('meeting_id')}")
        print(f"  Date: {meeting.get('meeting_date')}")
        print(f"  Ward: {meeting.get('ward')}")
        print(f"  Venue: {meeting.get('venue')}")
    print()

if __name__ == "__main__":
    print("\n🚀 JanSaakshi API Test Suite\n")
    
    try:
        test_health()
        test_list_meetings()
        test_ask()
        
        print("=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API")
        print("Make sure the server is running:")
        print("  uvicorn main_real_app:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
