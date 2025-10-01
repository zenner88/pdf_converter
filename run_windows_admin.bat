@echo off
REM PDF Converter - Windows Administrator Runner
REM Run this as Administrator to use port 80

echo ========================================
echo PDF Converter - Windows Setup
echo ========================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running as Administrator
) else (
    echo ❌ NOT running as Administrator
    echo.
    echo Please right-click this file and select "Run as administrator"
    echo Or run Command Prompt as Administrator and run: python app.py
    pause
    exit /b 1
)

echo.
echo 🔍 Checking Python installation...
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Python is installed
) else (
    echo ❌ Python not found in PATH
    echo Please install Python or add it to PATH
    pause
    exit /b 1
)

echo.
echo 📦 Installing dependencies...
pip install -r requirements.txt

echo.
echo 🚀 Starting PDF Converter on port 80...
echo Service will be available at: http://localhost
echo Press Ctrl+C to stop the service
echo.

python app.py

pause
