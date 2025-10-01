# Windows Setup Guide

## 🪟 Running PDF Converter on Windows Port 80

### Option 1: Run as Administrator (Recommended)

1. **Right-click** `run_windows_admin.bat` → **"Run as administrator"**
2. Service akan jalan di port 80
3. Akses: `http://localhost` atau `http://your-server-ip`

### Option 2: Manual Administrator Setup

1. **Open Command Prompt as Administrator**:
   - Press `Win + X` → Select "Command Prompt (Admin)" or "PowerShell (Admin)"
   - Or search "cmd" → Right-click → "Run as administrator"

2. **Navigate to project directory**:
   ```cmd
   cd C:\path\to\pdf_converter
   ```

3. **Install dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

4. **Run service**:
   ```cmd
   python app.py
   ```

### Option 3: Use Different Port (No Admin Required)

Edit `.env` file:
```
SERVICE_PORT=8080
```

Then run normally:
```cmd
python app.py
```

Access: `http://localhost:8080`

## ⚠️ Windows Considerations

### Port 80 Issues:
- **IIS conflict**: If IIS is running, it uses port 80
- **Skype conflict**: Old Skype versions use port 80
- **Other web servers**: Apache, Nginx, etc.

### Check Port Usage:
```cmd
netstat -ano | findstr :80
```

### Stop Conflicting Services:
```cmd
# Stop IIS (if installed)
iisreset /stop

# Or use Services.msc to stop "World Wide Web Publishing Service"
```

## 🔧 Troubleshooting

### "Permission denied" on port 80:
- Run as Administrator
- Or use port 8080/8000 instead

### "Port already in use":
```cmd
# Find what's using port 80
netstat -ano | findstr :80

# Kill process (replace PID with actual process ID)
taskkill /PID 1234 /F
```

### LibreOffice not found:
- Install LibreOffice from: https://www.libreoffice.org/download/
- Or set path in `.env`: `LIBREOFFICE_PATH=C:\Program Files\LibreOffice\program\soffice.exe`

## 🚀 Production Deployment

### Windows Service (Advanced):
1. Install `pywin32`: `pip install pywin32`
2. Use `nssm` (Non-Sucking Service Manager) to create Windows service
3. Or use Task Scheduler to run on startup

### IIS Reverse Proxy (Enterprise):
1. Install IIS with Application Request Routing (ARR)
2. Configure reverse proxy to `http://localhost:8000`
3. PDF Converter runs on port 8000, IIS proxies from port 80

## 📋 Quick Commands

```cmd
# Check if port 80 is free
netstat -ano | findstr :80

# Run with different port
set SERVICE_PORT=8080 && python app.py

# Check service status
curl http://localhost/health
```
