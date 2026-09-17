"""
ExportOS — Backend Server Runner

Run this script to start the ExportOS FastAPI backend server:
    python run.py
"""

import os
import sys
import uvicorn

# Ensure the backend directory is in the Python search path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if __name__ == "__main__":
    print("==================================================")
    print(" 🚀 Starting ExportOS Backend Server...")
    print(" 🌐 Local API:   http://localhost:8000")
    print(" 📑 API Docs:    http://localhost:8000/api/docs")
    print(" 🩺 Healthcheck: http://localhost:8000/api/health")
    print("==================================================")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
