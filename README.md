# Simple PDF Converter

Converter DOCX ke PDF yang simple, cepat, dan stabil dengan dukungan parallel processing.

## Fitur Utama

✅ **LibreOffice sebagai engine utama** - Lebih stabil dan tidak mudah hang  
✅ **MS Word fallback** - Otomatis fallback jika LibreOffice gagal  
✅ **Parallel processing** - Bisa handle beberapa konversi bersamaan  
✅ **Timeout protection** - Tidak akan hang, ada timeout 60 detik  
✅ **Async processing** - Non-blocking, response cepat  
✅ **Auto cleanup** - File temporary otomatis dibersihkan  
✅ **Status tracking** - Monitor progress setiap konversi  

## Requirements

- Python 3.8+
- LibreOffice (recommended) atau MS Word (Windows)
- Dependencies: FastAPI, uvicorn, psutil, aiofiles

## Installation

```bash
# Clone atau copy project
cd pdf_converter

# Install dependencies
pip install -r requirements.txt

# Install LibreOffice (Ubuntu/Debian)
sudo apt-get install libreoffice

# Install LibreOffice (Windows)
# Download dari https://www.libreoffice.org/download/download/
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

### 3. Convert DOCX to PDF (Sidinar Dashboard Compatible)
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

### 6. Direct PDF Access (Sidinar Compatible)
```
GET /pdf/{conversion_id}
```
Returns: PDF file directly

### 7. Cleanup Files
```
DELETE /cleanup/{conversion_id}
```
Menghapus file temporary setelah download

### 8. Queue Status (Sidinar Compatible)
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

Edit di `app.py`:

```python
CONVERSION_TIMEOUT = 60  # Timeout per konversi (detik)
MAX_WORKERS = 4          # Jumlah worker parallel
MAX_FILE_SIZE = 50 * 1024 * 1024  # Max ukuran file (50MB)
```

Environment variables:
```bash
export LIBREOFFICE_PATH="/path/to/soffice"  # Optional, auto-detect jika tidak diset
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

### Python requests (Sidinar Dashboard Compatible)
```python
import requests
import time

# Upload file with Sidinar format
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

#### Sidinar Dashboard Compatible API
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

## Sidinar Dashboard Integration

### Konfigurasi Sidinar Dashboard

Ubah URL converter service di `NaskahkeluarController.php`:

```php
// Ganti dari:
$convertUrl = 'http://svc.sidinarbnn.my.id/convertDua';

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

### Performance tuning
- Kurangi `MAX_WORKERS` jika server lemah
- Tingkatkan `CONVERSION_TIMEOUT` untuk file besar
- Monitor memory usage dengan `htop`
- Check queue status: `curl http://localhost:8000/queue/status`

### Sidinar Dashboard Issues
- Pastikan URL converter service benar
- Check network connectivity antara Sidinar dan converter
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
