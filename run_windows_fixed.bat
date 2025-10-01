@echo off
REM PDF Converter - Windows Fixed Runner
REM Addresses COM initialization and temp directory issues

echo ========================================
echo PDF Converter - Windows Fixed Setup
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
echo 📁 Creating Windows temp directory...
if not exist "temp" mkdir temp
if not exist "logs" mkdir logs
echo ✅ Directories created

echo.
echo 📦 Installing dependencies...
pip install -r requirements.txt
pip install pywin32

echo.
echo 🔧 Setting Windows-specific environment...
set TEMP_DIR=temp
set LOG_DIR=logs
set SERVICE_PORT=80
set MAX_WORKERS=4
set CONVERSION_TIMEOUT=40

echo.
echo 🚀 Starting PDF Converter on port 80...
echo Service will be available at: http://localhost
echo Monitoring dashboard: http://localhost/monitor
echo Press Ctrl+C to stop the service
echo.

python app.py

pause
