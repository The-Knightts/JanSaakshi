"""
Test script to demonstrate custom prompt support for meeting queries
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Example 1: Default meeting query (no custom prompt)
print("=" * 60)
print("Example 1: Default Meeting Query")
print("=" * 60)

default_query = {
    "question": "Tell me about the meeting"
}

response = requests.post(f"{BASE_URL}/ask", json=default_query)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Source: {data.get('source')}")
    print(f"Records Found: {data.get('records_found')}")
    print(f"Filters Used: {data.get('filters_used')}")
    print("\nAnswer preview (first 200 chars):")
    print(data.get('answer', '')[:200] + "...")
else:
    print(f"Error: {response.text}")

print("\n")

# Example 2: Meeting query with custom prompt
print("=" * 60)
print("Example 2: Meeting Query with Custom Prompt")
print("=" * 60)

custom_query = {
    "question": "meeting",
    "prompt": "What were the key decisions made about infrastructure projects? Focus on budget allocations and deadlines."
}

response = requests.post(f"{BASE_URL}/ask", json=custom_query)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Source: {data.get('source')}")
    print(f"Records Found: {data.get('records_found')}")
    print(f"Filters Used: {data.get('filters_used')}")
    print("\nAnswer preview (first 200 chars):")
    print(data.get('answer', '')[:200] + "...")
else:
    print(f"Error: {response.text}")

print("\n")

# Example 3: Meeting query with date filter and custom prompt
print("=" * 60)
print("Example 3: Meeting Query with Date Filter + Custom Prompt")
print("=" * 60)

filtered_custom_query = {
    "question": "meeting on 2025-01-15",
    "prompt": "Who were the attendees and what projects were discussed?",
    "ward": "Ward 37"
}

response = requests.post(f"{BASE_URL}/ask", json=filtered_custom_query)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Source: {data.get('source')}")
    print(f"Records Found: {data.get('records_found')}")
    print(f"Filters Used: {data.get('filters_used')}")
    print("\nAnswer preview (first 200 chars):")
    print(data.get('answer', '')[:200] + "...")
    print("\nMeeting Data:")
    for meeting in data.get('data', []):
        print(f"  - Meeting ID: {meeting.get('meeting_id')}")
        print(f"    Date: {meeting.get('meeting_date')}")
        print(f"    Ward: {meeting.get('ward')}")
        print(f"    Objective: {meeting.get('objective', 'N/A')[:100]}")
else:
    print(f"Error: {response.text}")

print("\n")
print("=" * 60)
print("Test Complete!")
print("=" * 60)
