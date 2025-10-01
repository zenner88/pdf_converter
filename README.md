# Simple PDF Converter

Converter DOCX ke PDF yang simple, cepat, dan stabil dengan dukungan parallel processing.

## Fitur Utama

✅ **MS Word fallback** - Otomatis fallback jika LibreOffice gagal  
✅ **Parallel processing** - Bisa handle beberapa konversi bersamaan  
✅ **Timeout protection** - Tidak akan hang, ada timeout 60 detik  
✅ **Async processing** - Non-blocking, response cepat  
✅ **Auto cleanup** - File temporary otomatis dibersihkan  
✅ **Status tracking** - Monitor progress setiap konversi  

## Installation

### Prerequisites
- Python 3.7+
- LibreOffice (recommended) atau MS Word (Windows)

### Quick Setup
```bash
# Clone repository
git clone https://github.com/zenner88/pdf_converter.git
cd pdf_converter

# Option 1: Automatic installation
python install_deps.py

# Option 2: Manual installation
pip install -r requirements.txt

# Option 3: Minimal installation (for testing only)
pip install requests python-docx

# Run service
python start.py
```

### Troubleshooting Installation

#### Missing 'requests' module:
```bash
# Fix for test_workers.py error
pip install requests python-docx

# Or install all dependencies
pip install -r requirements.txt
```

#### Permission errors:
```bash
# Use user installation
pip install --user -r requirements.txt

# Or use virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

#### LibreOffice not found:
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# CentOS/RHEL
sudo yum install libreoffice

# Manual path (if needed)
export LIBREOFFICE_PATH="/usr/bin/libreoffice"
```

## Quick Start

```bash
# Start server
python app.py

# Atau dengan uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Server akan berjalan di `http://localhost:8000`

## API Endpoints

### 1. Health Check
```
GET /
```
Response:
```json
{
  "service": "Simple PDF Converter",
  "status": "running",
  "available_engines": ["LibreOffice", "MS Word"],
  "max_workers": 4
}
```

### 2. Convert DOCX to PDF (Standard)
```
POST /convert
Content-Type: multipart/form-data
Body: file (DOCX file)
```
Response:
```json
{
  "conversion_id": "uuid-string",
  "status": "queued",
  "message": "Conversion started"
}
```

### 3. Convert DOCX to PDF (Enhanced API)
```
POST /convertDua
Content-Type: multipart/form-data
Body: 
  - file (DOCX file)
  - nomor_urut (string, optional)
  - target_url (string, optional)
```
Response:
```json
{
  "success": true,
  "message": "Conversion request received",
  "nomor_urut": "your-nomor-urut",
  "status": "queued",
  "conversion_id": "conversion-id"
}
```

### 4. Check Status
```
GET /status/{conversion_id}
```
Response:
```json
{
  "id": "uuid-string",
  "filename": "document.docx",
  "status": "completed",
  "engine_used": "LibreOffice",
  "created_time": "2024-01-01T10:00:00",
  "start_time": "2024-01-01T10:00:01",
  "end_time": "2024-01-01T10:00:05"
}
```

Status values: `queued`, `processing`, `completed`, `failed`

### 5. Download PDF (Standard)
```
GET /download/{conversion_id}
```
Returns: PDF file with original filename

### 6. Direct PDF Access (Enhanced)
```
GET /pdf/{conversion_id}
```
Returns: PDF file directly

### 7. Cleanup Files
```
DELETE /cleanup/{conversion_id}
```
Menghapus file temporary setelah download

### 8. Queue Status (Enhanced)
```
GET /queue/status
```
Response:
```json
{
  "success": true,
  "service_status": "online",
  "total_conversions": 10,
  "queued": 2,
  "processing": 1,
  "completed": 6,
  "failed": 1,
  "queue_size": 3,
  "estimated_wait_minutes": 2,
  "available_engines": ["LibreOffice"],
  "message": "Service siap digunakan"
}
```

### 9. Health Check (Detailed)
```
GET /health
```
Response:
```json
{
  "status": "healthy",
  "service": "Simple PDF Converter",
  "engines_available": 1,
  "engines": ["LibreOffice"],
  "active_conversions": 0,
  "timestamp": "2024-01-01T10:00:00"
}
```

## Configuration

### Configuration Options

#### Option 1: Using .env file (Recommended)
```bash
# Copy example file
cp .env.example .env

# Edit configuration
nano .env
```

Example `.env` file:
```bash
# Service Configuration
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000

# Worker Configuration (Optimized for your server)
MAX_WORKERS=4
CONVERSION_TIMEOUT=40

# File and Directory Settings
MAX_FILE_SIZE=52428800
TEMP_DIR=/tmp
LOG_DIR=logs
LOG_LEVEL=INFO

# Optional LibreOffice path
# LIBREOFFICE_PATH=/usr/bin/libreoffice
```

#### Option 2: Environment Variables
```bash
# Core settings
export MAX_WORKERS=4                        # Jumlah worker parallel (default: 4)
export CONVERSION_TIMEOUT=40                 # Timeout per konversi (detik)
export MAX_FILE_SIZE=52428800               # Max ukuran file (50MB)
export LIBREOFFICE_PATH="/path/to/soffice"   # Optional, auto-detect jika tidak diset

# Advanced settings
export TEMP_DIR="/tmp"                      # Directory untuk file temporary
export LOG_DIR="logs"                       # Directory untuk log files
export LOG_LEVEL="INFO"                     # Logging level
```

### Worker Configuration Guide

**Rekomendasi berdasarkan spesifikasi sistem:**

| System Specs | CPU Cores | RAM | Recommended Workers | Max Workers |
|--------------|-----------|-----|-------------------|-------------|
| **Light** | 2-4 cores | 4-8GB | 2-4 workers | 6 workers |
| **Medium** | 4-8 cores | 8-16GB | 4-8 workers | 10 workers |
| **Heavy** | 8+ cores | 16+ GB | 8-12 workers | 15 workers |

**⚠️ Important Notes:**
- LibreOffice may have stability issues with >10 concurrent instances
- Each worker uses ~100-500MB RAM depending on document size
- Monitor CPU and memory usage when increasing workers
- Use `/health` endpoint to monitor system resources

### Dynamic Worker Adjustment
```bash
# Start with conservative workers
export MAX_WORKERS=4
python start.py

# Monitor performance
curl http://localhost:8000/health

# Increase if needed
export MAX_WORKERS=8
# Restart service
```

## Usage Example

### Python requests (Standard)
```python
import requests
import time

# Upload file
with open('document.docx', 'rb') as f:
    response = requests.post('http://localhost:8000/convert', 
                           files={'file': f})
    conversion_id = response.json()['conversion_id']

# Check status
while True:
    status = requests.get(f'http://localhost:8000/status/{conversion_id}').json()
    if status['status'] == 'completed':
        break
    elif status['status'] == 'failed':
        print(f"Conversion failed: {status.get('error', 'Unknown error')}")
        break
    time.sleep(1)

# Download PDF
pdf_response = requests.get(f'http://localhost:8000/download/{conversion_id}')
with open('output.pdf', 'wb') as f:
    f.write(pdf_response.content)

# Cleanup
requests.delete(f'http://localhost:8000/cleanup/{conversion_id}')
```

### Python requests (Enhanced API)
```python
import requests
import time

# Upload file with enhanced format
with open('document.docx', 'rb') as f:
    data = {
        'nomor_urut': 'DOC_001_2024',
        'target_url': 'http://callback.url/webhook'
    }
    response = requests.post('http://localhost:8000/convertDua', 
                           files={'file': f}, data=data)
    result = response.json()
    conversion_id = result['conversion_id']

# Check queue status
queue_status = requests.get('http://localhost:8000/queue/status').json()
print(f"Queue status: {queue_status['message']}")

# Monitor conversion
while True:
    status = requests.get(f'http://localhost:8000/status/{conversion_id}').json()
    if status['status'] == 'completed':
        break
    elif status['status'] == 'failed':
        print(f"Conversion failed: {status.get('error', 'Unknown error')}")
        break
    time.sleep(1)

# Download PDF directly
pdf_response = requests.get(f'http://localhost:8000/pdf/{conversion_id}')
with open('output.pdf', 'wb') as f:
    f.write(pdf_response.content)

# Cleanup
requests.delete(f'http://localhost:8000/cleanup/{conversion_id}')
```

### cURL Examples

#### Standard API
```bash
# Convert
curl -X POST -F "file=@document.docx" http://localhost:8000/convert

# Check status
curl http://localhost:8000/status/your-conversion-id

# Download
curl -O -J http://localhost:8000/download/your-conversion-id

# Cleanup
curl -X DELETE http://localhost:8000/cleanup/your-conversion-id
```

#### Enhanced API
```bash
# Convert with metadata
curl -X POST \
  -F "file=@document.docx" \
  -F "nomor_urut=DOC_001_2024" \
  -F "target_url=http://callback.url/webhook" \
  http://localhost:8000/convertDua

# Check queue status
curl http://localhost:8000/queue/status

# Download PDF directly
curl -O http://localhost:8000/pdf/DOC_001_2024

# Health check
curl http://localhost:8000/health
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   ThreadPool     │    │  LibreOffice    │
│   (Async API)   │───▶│   (4 workers)    │───▶│   (Primary)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        ▼
                                │               ┌─────────────────┐
                                └──────────────▶│   MS Word       │
                                                │   (Fallback)    │
                                                └─────────────────┘
```

## Keunggulan vs Project Lama

| Aspek | Project Lama | Project Baru |
|-------|-------------|-------------|
| **Complexity** | 1174 lines | ~300 lines |
| **Dependencies** | 7 packages | 7 packages |
| **Primary Engine** | MS Word | LibreOffice |
| **Fallback** | LibreOffice | MS Word |
| **Architecture** | Complex validation | Simple & focused |
| **Error Handling** | Over-engineered | Essential only |
| **Performance** | Heavy | Lightweight |
| **Maintenance** | Difficult | Easy |

## Client Application Integration

### Client Configuration

Ubah URL converter service di aplikasi client:

```php
// Ganti dari:
$convertUrl = 'http://old-service.com/convertDua';

// Menjadi:
$convertUrl = 'http://your-server:8000/convertDua';
```

### Testing Integration

```bash
# Install dependencies untuk testing
pip install python-docx requests

# Run integration test
python test_integration.py
```

### Docker Deployment

```bash
# Build dan run dengan Docker
docker-compose up -d

# Check logs
docker-compose logs -f pdf-converter

# Stop service
docker-compose down
```

## Troubleshooting

### LibreOffice tidak terdeteksi
```bash
# Check instalasi
libreoffice --version

# Set path manual
export LIBREOFFICE_PATH="/usr/bin/libreoffice"
```

### Conversion gagal
- Check log file: `logs/pdf_converter.log`
- Check error log: `logs/pdf_converter_errors.log`
- Pastikan file DOCX tidak corrupt
- Coba dengan file DOCX yang lebih simple
- Test dengan: `python test_integration.py`

### Performance Tuning

#### Worker Optimization
```bash
# Check current performance
curl http://localhost:8000/health

# Monitor worker utilization
watch -n 2 'curl -s http://localhost:8000/ | jq .worker_utilization'

# System resource monitoring
htop  # or top
```

#### Scaling Guidelines
- **Increase workers** jika:
  - Worker utilization > 80%
  - CPU usage < 80%
  - Memory usage < 80%
  - Queue size consistently > 5

- **Decrease workers** jika:
  - CPU usage > 90%
  - Memory usage > 90%
  - Frequent conversion failures
  - System becomes unresponsive

#### Recommended Settings
```bash
# For high-volume production (16+ cores, 32+ GB RAM)
export MAX_WORKERS=12
export CONVERSION_TIMEOUT=90

# For medium production (8 cores, 16 GB RAM)
export MAX_WORKERS=6
export CONVERSION_TIMEOUT=60

# For development/testing (4 cores, 8 GB RAM)
export MAX_WORKERS=3
export CONVERSION_TIMEOUT=45
```

### Client Integration Issues
- Pastikan URL converter service benar
- Check network connectivity antara client dan converter
- Monitor logs di kedua service
- Test endpoint secara manual dengan cURL

## Production Deployment

### Systemd Service
```bash
# Copy ke /etc/systemd/system/pdf-converter.service
[Unit]
Description=PDF Converter Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/pdf_converter
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 50M;
    }
}
```

## Testing

### Manual Testing
```bash
# Start service
python start.py

# Run integration tests
python test_integration.py
```

### Load Testing
```bash
# Install ab (Apache Bench)
sudo apt-get install apache2-utils

# Test with multiple concurrent requests
ab -n 100 -c 10 -T 'multipart/form-data; boundary=1234567890' \
   -p test_data.txt http://localhost:8000/convertDua
```

## Monitoring

### Health Checks
- Health endpoint: `GET /health`
- Queue status: `GET /queue/status`
- Service status: `GET /`

### Logs
- Main log: `logs/pdf_converter.log`
- Error log: `logs/pdf_converter_errors.log`
- Access log: Handled by uvicorn

### Metrics
- Active conversions
- Queue size
- Engine availability
- Processing time
- Success/failure rates

## License

MIT License - Silakan digunakan dan dimodifikasi sesuai kebutuhan.
