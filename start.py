#!/usr/bin/env python3
"""
Simple startup script for PDF Converter
"""
import uvicorn
import sys
import os

def main():
    """Start the PDF converter service"""
    
    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    print("🚀 Starting Simple PDF Converter...")
    print("📁 Working directory:", current_dir)
    print("🌐 Server will be available at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    print("⚡ Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 PDF Converter stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
