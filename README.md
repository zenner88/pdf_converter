# Panduan Menjalankan PDF Converter di Windows

Aplikasi ini adalah layanan konversi DOCX ke PDF yang sederhana namun efisien, dibangun menggunakan FastAPI. Layanan ini mendukung konversi melalui LibreOffice (multi-platform) dan MS Word COM Automation (khusus Windows), serta dilengkapi dengan fitur seperti unggah ke target URL, antrean konversi, dan pemantauan status.

## Daftar Isi
- [Persyaratan](#persyaratan)
- [Instalasi](#instalasi)
- [Konfigurasi](#konfigurasi)
- [Menjalankan Aplikasi](#menjalankan-aplikasi)
    - [Opsi 1: Menggunakan `run_windows_fixed.bat` (Disarankan, Memerlukan Administrator)](#opsi-1-menggunakan-run_windows_fixedbat-disarankan-memerlukan-administrator)
    - [Opsi 2: Manual (Memerlukan Administrator)](#opsi-2-manual-memerlukan-administrator)
    - [Opsi 3: Menggunakan Port Berbeda (Tidak Memerlukan Administrator)](#opsi-3-menggunakan-port-berbeda-tidak-memerlukan-administrator)
- [Troubleshooting](#troubleshooting)
    - [Masalah Port 80](#masalah-port-80)
    - ["Permission denied" pada Port 80](#permission-denied-pada-port-80)
    - ["Port already in use"](#port-already-in-use)
    - [LibreOffice Tidak Ditemukan](#libreoffice-tidak-ditemukan)
- [Endpoint API](#endpoint-api)
- [Deployment Produksi](#deployment-produksi)

---

## Persyaratan

Sebelum menjalankan aplikasi, pastikan sistem Anda memenuhi persyaratan berikut:

1.  **Python 3.7+**:
    *   Unduh dan instal Python dari [python.org](https://www.python.org/downloads/windows/).
    *   Pastikan untuk mencentang opsi "Add Python to PATH" selama instalasi.
2.  **LibreOffice**:
    *   LibreOffice digunakan sebagai mesin konversi utama. Unduh dan instal dari [libreoffice.org](https://www.libreoffice.org/download/).
    *   Pastikan LibreOffice terinstal di jalur default (`C:\Program Files\LibreOffice` atau `C:\Program Files (x86)\LibreOffice`) atau tentukan jalurnya di `.env`.
3.  **(Opsional) Microsoft Word**:
    *   Jika Anda ingin menggunakan MS Word untuk konversi (khusus Windows, lebih andal untuk beberapa format), pastikan Microsoft Word terinstal di sistem Anda.

## Instalasi

Ikuti langkah-langkah ini untuk menyiapkan proyek:

1.  **Clone Repositori**:
    ```bash
    git clone https://github.com/your-repo/pdf_converter.git
    cd pdf_converter
    ```

2.  **Instal Dependensi**:
    Buka `Command Prompt` atau `PowerShell` **sebagai Administrator** (disarankan, terutama jika Anda menggunakan `run_windows_fixed.bat` atau ingin menginstal `pywin32`).

    ```cmd
    pip install -r requirements.txt
    ```
    Skrip `run_windows_fixed.bat` juga akan secara otomatis menginstal `pywin32` jika diperlukan untuk integrasi MS Word.

## Konfigurasi

Anda dapat mengkonfigurasi aplikasi menggunakan file `.env` di root proyek. Salin `.env.example` ke `.env` dan sesuaikan nilai-nilainya:

```ini
# Contoh file .env
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
CONVERSION_TIMEOUT=45
MAX_WORKERS=4
MAX_FILE_SIZE=52428800 # 50MB
TEMP_DIR=temp # Direktori sementara untuk file konversi
LOG_DIR=logs # Direktori untuk file log
LOG_LEVEL=INFO # INFO, WARNING, ERROR, DEBUG
LIBREOFFICE_PATH=C:\Program Files\LibreOffice\program\soffice.exe # Opsional: jika LibreOffice tidak di jalur default
```

**Variabel Penting**:
*   `SERVICE_PORT`: Port tempat layanan akan berjalan. Default: `8000`. Untuk Port 80, Anda perlu hak Administrator.
*   `LIBREOFFICE_PATH`: Jalur lengkap ke executable LibreOffice (`soffice.exe`). Hanya diperlukan jika LibreOffice tidak terdeteksi secara otomatis.
*   `TEMP_DIR` dan `LOG_DIR`: Direktori untuk menyimpan file sementara dan log. Di Windows, `run_windows_fixed.bat` akan membuat direktori `temp` dan `logs` secara lokal jika tidak ada.

## Menjalankan Aplikasi

Ada beberapa cara untuk menjalankan aplikasi di Windows:

### Opsi 1: Menggunakan `run_windows_fixed.bat` (Disarankan, Memerlukan Administrator)

File batch ini melakukan instalasi dependensi dasar, membuat direktori `temp` dan `logs`, dan menjalankan aplikasi di Port 80. Ini juga menangani beberapa masalah umum di Windows (seperti inisialisasi COM untuk MS Word).

1.  **Klik kanan** pada `run_windows_fixed.bat`.
2.  Pilih **"Run as administrator"**.
3.  Layanan akan berjalan di `http://localhost` (Port 80).
    *   Dashboard Pemantauan: `http://localhost/monitor`

### Opsi 2: Manual (Memerlukan Administrator)

Jika Anda ingin menjalankan layanan di Port 80 secara manual:

1.  **Buka Command Prompt sebagai Administrator**:
    *   Tekan `Win + X` → Pilih "Command Prompt (Admin)" atau "PowerShell (Admin)".
    *   Atau cari "cmd" → Klik kanan → "Run as administrator".
2.  **Navigasi ke direktori proyek**:
    ```cmd
    cd C:\path\to\pdf_converter
    ```
3.  **Instal dependensi**:
    ```cmd
    pip install -r requirements.txt
    ```
4.  **Jalankan layanan**:
    ```cmd
    python app.py
    ```
    Layanan akan berjalan di `http://localhost` (Port 80) jika `SERVICE_PORT` di `.env` disetel ke 80 atau tidak disetel.

### Opsi 3: Menggunakan Port Berbeda (Tidak Memerlukan Administrator)

Jika Anda tidak ingin menjalankan sebagai Administrator atau menghadapi masalah Port 80:

1.  **Edit file `.env`**:
    Ubah `SERVICE_PORT` ke port yang berbeda, misalnya 8080:
    ```ini
    SERVICE_PORT=8080
    ```
2.  **Buka Command Prompt atau PowerShell biasa** (tidak perlu Administrator).
3.  **Navigasi ke direktori proyek**:
    ```cmd
    cd C:\path\to\pdf_converter
    ```
4.  **Instal dependensi** (jika belum):
    ```cmd
    pip install -r requirements.txt
    ```
5.  **Jalankan layanan**:
    ```cmd
    python app.py
    ```
    Aplikasi akan berjalan melalui `http://localhost:8080` (atau port yang Anda tentukan).

## Troubleshooting

### Masalah Port 80
Port 80 sering digunakan oleh layanan lain:
*   **Konflik IIS**: Jika IIS (Internet Information Services) berjalan.
*   **Konflik Skype**: Versi lama Skype.
*   **Web server lain**: Apache, Nginx, dll.

**Periksa Penggunaan Port**:
```cmd
netstat -ano | findstr :80
```
Ini akan menunjukkan proses apa yang menggunakan Port 80.

**Hentikan Layanan yang Berkonflik**:
```cmd
# Hentikan IIS (jika terinstal)
iisreset /stop

# Atau gunakan Services.msc untuk menghentikan "World Wide Web Publishing Service"
```

### "Permission denied" pada Port 80
*   Pastikan Anda menjalankan aplikasi **sebagai Administrator**.
*   Atau, gunakan port yang berbeda (misalnya 8080/8000) seperti yang dijelaskan di [Opsi 3](#opsi-3-menggunakan-port-berbeda-tidak-memerlukan-administrator).

### "Port already in use"
*   Gunakan `netstat -ano | findstr :<PORT_NUMBER>` untuk menemukan proses yang menggunakan port tersebut.
*   Bunuh proses tersebut (ganti PID dengan ID proses aktual):
    ```cmd
taskkill /PID <PID_NUMBER> /F
```

### LibreOffice Tidak Ditemukan
*   Pastikan LibreOffice terinstal dengan benar.
*   Jika terinstal di lokasi non-default, tentukan jalurnya di file `.env`:
    ```ini
    LIBREOFFICE_PATH=C:\Jalur\ke\LibreOffice\program\soffice.exe
    ```

## Endpoint API

Berikut adalah beberapa endpoint API utama yang tersedia:

*   **GET `/`**: Health check dasar.
*   **POST `/convert`**: Mengunggah file DOCX dan mengkonversinya ke PDF. Memerlukan `file`, `nomor_urut`, dan `target_url` sebagai form data.
*   **POST `/convertDua`**: Endpoint konversi DOCX ke PDF yang lebih canggih. Memerlukan `file`, `nomor_urut` (opsional), dan `target_url` (opsional) sebagai form data.
*   **GET `/status/{conversion_id}`**: Mendapatkan status konversi tertentu berdasarkan ID.
*   **GET `/download/{conversion_id}`**: Mengunduh PDF yang telah dikonversi setelah selesai.
*   **GET `/pdf/{conversion_id}`**: Mengakses PDF secara langsung.
*   **DELETE `/cleanup/{conversion_id}`**: Membersihkan file konversi yang sudah selesai.
*   **GET `/queue/status`**: Mendapatkan status antrean konversi secara keseluruhan.
*   **GET `/health`**: Health check yang lebih detail dengan informasi sistem.
*   **GET `/monitor`**: Dashboard pemantauan berbasis web (memerlukan `static/monitor.html`).

## Deployment Produksi

Untuk deployment produksi, pertimbangkan opsi berikut:

*   **Windows Service**: Gunakan `pywin32` dan alat seperti `nssm` (Non-Sucking Service Manager) untuk menjalankan aplikasi sebagai layanan Windows.
*   **Task Scheduler**: Konfigurasi Task Scheduler untuk menjalankan aplikasi saat startup.
*   **IIS Reverse Proxy**: Jika Anda sudah memiliki IIS, Anda dapat mengkonfigurasinya sebagai reverse proxy untuk meneruskan permintaan ke aplikasi Python yang berjalan di port internal.