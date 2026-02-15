"""
JanSaakshi Startup Script
Run this once to initialize everything
"""

import os
import sys

def main():
    print("=" * 80)
    print("JanSaakshi - Civic Transparency Platform Setup")
    print("=" * 80)
    
    # Initialize database
    print("\n[1/3] Initializing database...")
    from init_db import init_database
    init_database()
    
    print("\n[2/3] Checking dependencies...")
    try:
        import fastapi
        import requests
        import mistralai
        print("✓ All dependencies installed")
    except ImportError as e:
        print(f"✗ Missing package: {e}")
        print("Run: pip install fastapi uvicorn requests mistralai python-dotenv")
        return
    
    print("\n[3/3] Setup complete!")
    print("\n" + "=" * 80)
    print("To run the application:")
    print("=" * 80)
    print("\n1. Start the backend (in Terminal 1):")
    print("   uvicorn main:app --reload")
    print("\n2. Start the UI (in Terminal 2):")
    print("   python ui.py")
    print("\n" + "=" * 80)
    
if __name__ == "__main__":
    main()
