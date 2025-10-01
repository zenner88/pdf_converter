import os
import tempfile
import subprocess
import asyncio
import shutil
import uuid
import platform
from pathlib import Path
from typing import Optional, Dict, Any
{{ ... }}
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    # python-dotenv not installed, use environment variables only
    pass

# Configuration from environment variables or .env file
SERVICE_HOST = os.getenv('SERVICE_HOST', '0.0.0.0')
SERVICE_PORT = int(os.getenv('SERVICE_PORT', '8000'))
CONVERSION_TIMEOUT = int(os.getenv('CONVERSION_TIMEOUT', '45'))  # Reduced for high volume
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))  # Configurable via environment
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', str(50 * 1024 * 1024)))  # 50MB default
TEMP_DIR = os.getenv('TEMP_DIR', tempfile.gettempdir())
LOG_DIR = os.getenv('LOG_DIR', 'logs')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', '600'))  # 10 minutes
MAX_FILE_AGE = int(os.getenv('MAX_FILE_AGE', '3600'))  # 1 hour

# Create directories if they don't exist
Path(LOG_DIR).mkdir(exist_ok=True)
Path(TEMP_DIR).mkdir(exist_ok=True)

# High-volume deployment recommendations:
# Target: 20-60 conversions/minute
# - For 20/min: 8-12 workers (avg 25s per conversion)
# - For 40/min: 15-20 workers (avg 20s per conversion) 
# - For 60/min: 25-30 workers (avg 15s per conversion)
# 
# System requirements for high volume:
# - CPU: 16+ cores (2 cores per 3-4 workers)
# - RAM: 32+ GB (1-2GB per worker)
# - SSD storage for temp files
# - LibreOffice limit: Max 15-20 concurrent instances
# - Consider multiple service instances with load balancer

# Setup logging with configurable level
log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'pdf_converter.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log configuration on startup
logger.info(f"PDF Converter starting with configuration:")
logger.info(f"  Service: {SERVICE_HOST}:{SERVICE_PORT}")
logger.info(f"  Workers: {MAX_WORKERS}, Timeout: {CONVERSION_TIMEOUT}s")
logger.info(f"  Max file size: {MAX_FILE_SIZE / (1024*1024):.1f}MB")
logger.info(f"  Temp dir: {TEMP_DIR}")
logger.info(f"  Log dir: {LOG_DIR}")

app = FastAPI(title="Simple PDF Converter", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for conversion tasks
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Conversion status tracking
conversion_status: Dict[str, Dict[str, Any]] = {}


class ConversionEngine:
    """Base class for conversion engines"""
    
    def __init__(self):
        self.name = "base"
    
    async def convert(self, input_path: str, output_path: str) -> bool:
        """Convert DOCX to PDF. Returns True if successful."""
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """Check if this engine is available on the system"""
        raise NotImplementedError


class LibreOfficeEngine(ConversionEngine):
    """LibreOffice headless conversion engine"""
    
    def __init__(self):
        super().__init__()
        self.name = "LibreOffice"
        self.executable = self._find_executable()
    
    def _find_executable(self) -> Optional[str]:
        """Find LibreOffice executable"""
        # Check environment variable first
        if os.environ.get('LIBREOFFICE_PATH'):
            return os.environ.get('LIBREOFFICE_PATH')
        
        # Common paths for different OS
        if platform.system() == "Windows":
            paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
        else:
            # Linux/macOS
            paths = [
                "/usr/bin/libreoffice",
                "/usr/local/bin/libreoffice",
                "/opt/libreoffice/program/soffice",
                "/Applications/LibreOffice.app/Contents/MacOS/soffice"
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
        
        # Try system PATH
        try:
            result = subprocess.run(['which', 'libreoffice'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    def is_available(self) -> bool:
        """Check if LibreOffice is available"""
        return self.executable is not None
    
    async def convert(self, input_path: str, output_path: str) -> bool:
        """Convert using LibreOffice headless"""
        if not self.executable:
            return False
        
        try:
            output_dir = os.path.dirname(output_path)
            
            # LibreOffice command
            cmd = [
                self.executable,
                '--headless',
                '--invisible',
                '--nodefault',
                '--nolockcheck',
                '--nologo',
                '--norestore',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                input_path
            ]
            
            logger.info(f"Running LibreOffice: {' '.join(cmd)}")
            
            # Run with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=CONVERSION_TIMEOUT
                )
                
                if process.returncode == 0:
                    # LibreOffice creates filename.pdf, we might need to rename
                    input_name = Path(input_path).stem
                    expected_pdf = os.path.join(output_dir, f"{input_name}.pdf")
                    
                    if os.path.exists(expected_pdf):
                        if expected_pdf != output_path:
                            shutil.move(expected_pdf, output_path)
                        return True
                
                logger.error(f"LibreOffice failed: {stderr.decode()}")
                return False
                
            except asyncio.TimeoutError:
                logger.error("LibreOffice conversion timed out")
                process.kill()
                return False
                
        except Exception as e:
            logger.error(f"LibreOffice conversion error: {e}")
            return False


class MSWordEngine(ConversionEngine):
    """MS Word COM automation engine (Windows only)"""
    
    def __init__(self):
        super().__init__()
        self.name = "MS Word"
    
    def is_available(self) -> bool:
        """Check if MS Word is available (Windows only)"""
        if platform.system() != "Windows":
            return False
        
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Quit()
            return True
        except:
            return False
    
    async def convert(self, input_path: str, output_path: str) -> bool:
        """Convert using MS Word COM automation"""
        if platform.system() != "Windows":
            return False
        
        try:
            from docx2pdf import convert
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor, 
                lambda: convert(input_path, output_path)
            )
            
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            logger.error(f"MS Word conversion error: {e}")
            return False


# Initialize engines
libre_engine = LibreOfficeEngine()
word_engine = MSWordEngine()

# Available engines in priority order
engines = [libre_engine, word_engine]
available_engines = [engine for engine in engines if engine.is_available()]

logger.info(f"Available engines: {[engine.name for engine in available_engines]}")
logger.info(f"Configuration: {MAX_WORKERS} workers, {CONVERSION_TIMEOUT}s timeout")

# Calculate theoretical capacity
if available_engines:
    theoretical_max = (MAX_WORKERS * 60) / CONVERSION_TIMEOUT
    realistic_throughput = theoretical_max * 0.7  # Account for overhead
    logger.info(f"Theoretical capacity: {theoretical_max:.1f} conversions/minute")
    logger.info(f"Realistic throughput: {realistic_throughput:.1f} conversions/minute")
    
    if realistic_throughput < 20:
        logger.warning(f"Current config may not handle high volume (20+ conversions/min)")
        logger.warning(f"Consider increasing MAX_WORKERS or reducing CONVERSION_TIMEOUT")
else:
    logger.error("No conversion engines available!")

# Cleanup old conversions periodically
async def cleanup_old_conversions():
    """Clean up old conversion files and status"""
    while True:
        try:
            current_time = datetime.now()
            expired_conversions = []
            
            for conv_id, status in conversion_status.items():
                # Remove conversions older than configured age
                if (current_time - status["created_time"]).total_seconds() > MAX_FILE_AGE:
                    expired_conversions.append(conv_id)
            
            for conv_id in expired_conversions:
                status = conversion_status[conv_id]
                # Clean up files
                for path in [status.get("input_path"), status.get("output_path")]:
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception as e:
                            logger.warning(f"Failed to cleanup {path}: {e}")
                
                # Remove from status
                del conversion_status[conv_id]
                logger.info(f"Cleaned up expired conversion: {conv_id}")
            
            # Sleep for configured interval before next cleanup
            await asyncio.sleep(CLEANUP_INTERVAL)
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            await asyncio.sleep(600)

# Start cleanup task
@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup"""
    asyncio.create_task(cleanup_old_conversions())
    logger.info("PDF Converter service started")
    logger.info(f"Available conversion engines: {[engine.name for engine in available_engines]}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("PDF Converter service shutting down")
    # Clean up any remaining files
    for status in conversion_status.values():
        for path in [status.get("input_path"), status.get("output_path")]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass


async def convert_file(input_path: str, output_path: str, conversion_id: str) -> bool:
    """Convert DOCX to PDF using available engines"""
    
    conversion_status[conversion_id]["status"] = "processing"
    conversion_status[conversion_id]["start_time"] = datetime.now()
    
    if not available_engines:
        conversion_status[conversion_id]["error"] = "No conversion engines available"
        conversion_status[conversion_id]["status"] = "failed"
        return False
    
    # Try each engine in order
    for engine in available_engines:
        try:
            logger.info(f"Trying {engine.name} for conversion {conversion_id}")
            conversion_status[conversion_id]["current_engine"] = engine.name
            
            success = await engine.convert(input_path, output_path)
            
            if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                conversion_status[conversion_id]["status"] = "completed"
                conversion_status[conversion_id]["engine_used"] = engine.name
                conversion_status[conversion_id]["end_time"] = datetime.now()
                logger.info(f"Conversion {conversion_id} completed with {engine.name}")
                return True
            else:
                logger.warning(f"{engine.name} failed for conversion {conversion_id}")
                
        except Exception as e:
            logger.error(f"{engine.name} error for conversion {conversion_id}: {e}")
            continue
    
    # All engines failed
    conversion_status[conversion_id]["status"] = "failed"
    conversion_status[conversion_id]["error"] = "All conversion engines failed"
    conversion_status[conversion_id]["end_time"] = datetime.now()
    return False


@app.get("/")
async def root():
    """Health check endpoint"""
    active_conversions = len([s for s in conversion_status.values() if s["status"] in ["queued", "processing"]])
    
    return {
        "service": "Simple PDF Converter",
        "status": "running",
        "available_engines": [engine.name for engine in available_engines],
        "max_workers": MAX_WORKERS,
        "active_conversions": active_conversions,
        "worker_utilization": f"{(active_conversions / MAX_WORKERS * 100):.1f}%" if MAX_WORKERS > 0 else "0%"
    }


@app.post("/convert")
async def convert_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Convert DOCX to PDF"""
    
    # Validate file
    if not file.filename.lower().endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only DOCX files are supported")
    
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max size: {MAX_FILE_SIZE} bytes")
    
    # Generate unique ID
    conversion_id = str(uuid.uuid4())
    
    # Create temp files
    temp_input = os.path.join(TEMP_DIR, f"{conversion_id}_input.docx")
    temp_output = os.path.join(TEMP_DIR, f"{conversion_id}_output.pdf")
    
    try:
        # Save uploaded file
        async with aiofiles.open(temp_input, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Initialize conversion status
        conversion_status[conversion_id] = {
            "id": conversion_id,
            "filename": file.filename,
            "status": "queued",
            "created_time": datetime.now(),
            "input_path": temp_input,
            "output_path": temp_output
        }
        
        # Start conversion in background
        background_tasks.add_task(convert_file, temp_input, temp_output, conversion_id)
        
        return JSONResponse({
            "conversion_id": conversion_id,
            "status": "queued",
            "message": "Conversion started"
        })
        
    except Exception as e:
        # Cleanup on error
        for path in [temp_input, temp_output]:
            if os.path.exists(path):
                os.remove(path)
        
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process upload")


@app.post("/convertDua")
async def convert_dua(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    nomor_urut: str = Form(None),
    target_url: str = Form(None)
):
    """Convert DOCX to PDF - Enhanced API endpoint"""
    
    # Validate file
    if not file.filename.lower().endswith('.docx'):
        return JSONResponse(
            status_code=400,
            content={"error": "Only DOCX files are supported"}
        )
    
    if file.size and file.size > MAX_FILE_SIZE:
        return JSONResponse(
            status_code=400,
            content={"error": f"File too large. Max size: {MAX_FILE_SIZE} bytes"}
        )
    
    # Generate conversion ID using nomor_urut if provided
    if nomor_urut:
        conversion_id = nomor_urut
    else:
        conversion_id = str(uuid.uuid4())
    
    # Create temp files with specific naming
    temp_input = os.path.join(TEMP_DIR, f"{conversion_id}.docx")
    temp_output = os.path.join(TEMP_DIR, f"{conversion_id}.pdf")
    
    try:
        # Save uploaded file
        async with aiofiles.open(temp_input, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"ConvertDua: Processing file {file.filename} -> {conversion_id}")
        
        # Initialize conversion status
        conversion_status[conversion_id] = {
            "id": conversion_id,
            "filename": file.filename,
            "nomor_urut": nomor_urut,
            "target_url": target_url,
            "status": "queued",
            "created_time": datetime.now(),
            "input_path": temp_input,
            "output_path": temp_output
        }
        
        # Start conversion in background
        background_tasks.add_task(convert_file, temp_input, temp_output, conversion_id)
        
        # Return enhanced response format
        return JSONResponse({
            "success": True,
            "message": "Conversion request received",
            "nomor_urut": nomor_urut,
            "status": "queued",
            "conversion_id": conversion_id
        })
        
    except Exception as e:
        # Cleanup on error
        for path in [temp_input, temp_output]:
            if os.path.exists(path):
                os.remove(path)
        
        logger.error(f"ConvertDua error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to process conversion request",
                "message": str(e)
            }
        )


@app.get("/status/{conversion_id}")
async def get_status(conversion_id: str):
    """Get conversion status"""
    if conversion_id not in conversion_status:
        raise HTTPException(status_code=404, detail="Conversion not found")
    
    status = conversion_status[conversion_id].copy()
    
    # Remove file paths from response
    status.pop("input_path", None)
    status.pop("output_path", None)
    
    # Convert datetime to string
    for key in ["created_time", "start_time", "end_time"]:
        if key in status and status[key]:
            status[key] = status[key].isoformat()
    
    return status


@app.get("/download/{conversion_id}")
async def download_pdf(conversion_id: str):
    """Download converted PDF"""
    if conversion_id not in conversion_status:
        raise HTTPException(status_code=404, detail="Conversion not found")
    
    status = conversion_status[conversion_id]
    
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Conversion not completed")
    
    output_path = status["output_path"]
    
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    # Generate download filename
    original_name = Path(status["filename"]).stem
    pdf_filename = f"{original_name}.pdf"
    
    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=pdf_filename
    )


@app.get("/pdf/{conversion_id}")
async def get_pdf_direct(conversion_id: str):
    """Direct PDF access - Enhanced endpoint"""
    if conversion_id not in conversion_status:
        # Try to find PDF file directly in temp directory
        pdf_path = os.path.join(TEMP_DIR, f"{conversion_id}.pdf")
        if os.path.exists(pdf_path):
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"{conversion_id}.pdf"
            )
        raise HTTPException(status_code=404, detail="PDF not found")
    
    status = conversion_status[conversion_id]
    output_path = status["output_path"]
    
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=f"{conversion_id}.pdf"
    )


@app.delete("/cleanup/{conversion_id}")
async def cleanup_conversion(conversion_id: str):
    """Clean up conversion files"""
    if conversion_id not in conversion_status:
        raise HTTPException(status_code=404, detail="Conversion not found")
    
    status = conversion_status[conversion_id]
    
    # Remove files
    for path in [status.get("input_path"), status.get("output_path")]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to remove {path}: {e}")
    
    # Remove from status tracking
    del conversion_status[conversion_id]
    
    return {"message": "Cleanup completed"}


@app.get("/queue/status")
async def queue_status():
    """Get overall queue status - Enhanced endpoint"""
    total = len(conversion_status)
    completed = sum(1 for s in conversion_status.values() if s["status"] == "completed")
    processing = sum(1 for s in conversion_status.values() if s["status"] == "processing")
    failed = sum(1 for s in conversion_status.values() if s["status"] == "failed")
    queued = total - completed - processing - failed
    
    # Calculate estimated wait time (rough estimate)
    avg_processing_time = 30  # seconds per conversion
    estimated_wait_minutes = max(0, (queued + processing) * avg_processing_time // 60)
    
    # High volume status indicators
    current_throughput = (MAX_WORKERS * 60) / CONVERSION_TIMEOUT * 0.7
    is_high_volume_ready = current_throughput >= 20
    
    if (queued + processing) == 0:
        status_message = "Service siap digunakan"
    elif (queued + processing) < 5:
        status_message = "Antrian sedikit"
    elif (queued + processing) < 15:
        status_message = "Antrian sedang"
    elif (queued + processing) < 30:
        status_message = "Antrian panjang"
    else:
        status_message = "Antrian sangat panjang - pertimbangkan scaling"
    
    return {
        "success": True,
        "service_status": "online" if available_engines else "offline",
        "total_conversions": total,
        "queued": queued,
        "processing": processing,
        "completed": completed,
        "failed": failed,
        "queue_size": queued + processing,
        "estimated_wait_minutes": estimated_wait_minutes,
        "available_engines": [engine.name for engine in available_engines],
        "current_throughput_per_minute": round(current_throughput, 1),
        "high_volume_ready": is_high_volume_ready,
        "message": status_message
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    # Get system resource info
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    active_conversions = len([s for s in conversion_status.values() if s["status"] in ["queued", "processing"]])
    
    return {
        "status": "healthy",
        "service": "Simple PDF Converter",
        "engines_available": len(available_engines),
        "engines": [engine.name for engine in available_engines],
        "active_conversions": active_conversions,
        "max_workers": MAX_WORKERS,
        "worker_utilization": f"{(active_conversions / MAX_WORKERS * 100):.1f}%" if MAX_WORKERS > 0 else "0%",
        "system_resources": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "cpu_cores": psutil.cpu_count()
        },
        "performance_metrics": {
            "theoretical_max_per_minute": round((MAX_WORKERS * 60) / CONVERSION_TIMEOUT, 1),
            "realistic_throughput_per_minute": round((MAX_WORKERS * 60) / CONVERSION_TIMEOUT * 0.7, 1),
            "current_queue_wait_minutes": round(active_conversions * (CONVERSION_TIMEOUT / 60) / MAX_WORKERS, 1) if MAX_WORKERS > 0 else 0
        },
        "recommendations": {
            "current_load": "high" if active_conversions > MAX_WORKERS * 0.8 else "medium" if active_conversions > MAX_WORKERS * 0.5 else "low",
            "suggested_action": "Consider increasing workers" if active_conversions > MAX_WORKERS * 0.8 and cpu_percent < 80 and memory.percent < 80 else "Current workers sufficient",
            "high_volume_ready": "Yes" if (MAX_WORKERS * 60) / CONVERSION_TIMEOUT * 0.7 >= 20 else "No - increase workers"
        },
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
