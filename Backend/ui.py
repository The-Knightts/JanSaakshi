import webbrowser
import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import threading

def start_browser():
    """Open the UI in default browser after a short delay"""
    time.sleep(2)  # Give server time to start
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("🚀 Starting JanSaakshi UI Launcher...")
    print("📱 Opening browser to http://127.0.0.1:8000")
    
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=start_browser, daemon=True)
    browser_thread.start()
    
    # Import and run the main FastAPI app
    from main import app
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
