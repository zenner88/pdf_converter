# Dokumentasi API PDF Converter

Berikut adalah daftar endpoint API yang tersedia untuk layanan konversi PDF.

## API Utama

### 1. `POST /convert`
-   **Deskripsi**: Mengonversi file DOCX yang diunggah menjadi PDF dan mengirimkannya ke `target_url`.
-   **Parameter (`form-data`)**:
    -   `file` (file): File `.docx` yang akan dikonversi.
    -   `nomor_urut` (string): ID unik untuk melacak konversi.
    -   `target_url` (string): URL callback tempat PDF yang dikonversi akan diunggah.
-   **Respons Sukses (`JSON`)**:
    ```json
    {
      "conversion_id": "some_unique_id",
      "status": "queued",
      "message": "Conversion started",
      "nomor_urut": "some_unique_id"
    }
    ```

### 2. `POST /convertDua`
-   **Deskripsi**: Varian dari endpoint `/convert` dengan parameter opsional.
-   **Parameter (`form-data`)**:
    -   `file` (file): File `.docx` yang akan dikonversi.
    -   `nomor_urut` (string, opsional): ID unik. Jika tidak disediakan, UUID akan dibuat.
    -   `target_url` (string, opsional): URL callback.
-   **Respons Sukses (`JSON`)**:
    ```json
    {
      "success": true,
      "message": "Conversion request received",
      "nomor_urut": "some_unique_id",
      "status": "queued",
      "conversion_id": "some_unique_id"
    }
    ```

### 3. `GET /status/{conversion_id}`
-   **Deskripsi**: Memeriksa status dari proses konversi yang sedang berjalan.
-   **Parameter (`path`)**:
    -   `conversion_id` (string): ID yang dikembalikan oleh `/convert` atau `/convertDua`.
-   **Respons Sukses (`JSON`)**:
    ```json
    {
      "id": "some_unique_id",
      "status": "completed",
      "filename": "document.docx"
    }
    ```

### 4. `GET /download/{conversion_id}`
-   **Deskripsi**: Mengunduh file PDF yang telah berhasil dikonversi.
-   **Parameter (`path`)**:
    -   `conversion_id` (string): ID dari konversi yang telah selesai.
-   **Respons Sukses**:
    -   File `application/pdf`.

### 5. `GET /pdf/{conversion_id}`
-   **Deskripsi**: Mengakses atau menampilkan file PDF secara langsung di browser.
-   **Parameter (`path`)**:
    -   `conversion_id` (string): ID dari konversi yang telah selesai.
-   **Respons Sukses**:
    -   File `application/pdf`.

### 6. `DELETE /cleanup/{conversion_id}`
-   **Deskripsi**: Menghapus file sementara (input `.docx` dan output `.pdf`) yang terkait dengan sebuah konversi.
-   **Parameter (`path`)**:
    -   `conversion_id` (string): ID dari konversi yang ingin dibersihkan.
-   **Respons Sukses (`JSON`)**:
    ```json
    { "message": "Cleanup completed" }
    ```

## API Pemantauan

Endpoint ini berguna untuk memantau kesehatan dan status layanan secara terprogram.

### 1. `GET /`
-   **Deskripsi**: Health check dasar untuk memverifikasi bahwa layanan sedang berjalan.
-   **Respons (`JSON`)**: Menampilkan status dasar layanan dan mesin konversi yang tersedia.

### 2. `GET /health`
-   **Deskripsi**: Memberikan laporan kesehatan terperinci, termasuk penggunaan CPU/memori dan statistik pekerja.
-   **Respons (`JSON`)**: Objek komprehensif dengan metrik sistem dan kinerja.

### 3. `GET /queue/status`
-   **Deskripsi**: Mendapatkan status antrean konversi secara keseluruhan (jumlah antrean, sedang diproses, selesai, gagal).
-   **Respons (`JSON`)**: Statistik mendetail tentang antrean konversi.

### 4. `GET /monitor/data`
-   **Deskripsi**: Endpoint gabungan yang menyediakan semua data pemantauan dari `/health` dan `/queue/status` dalam satu panggilan API. Paling efisien untuk pemantauan eksternal.
-   **Respons (`JSON`)**: Objek terstruktur tunggal yang berisi semua metrik pemantauan yang relevan.
    ```json
    {
      "service": {
        "status": "healthy",
        "engines": ["LibreOffice", "MS Word"],
        "high_volume_ready": "Yes",
        "message": "Service ready"
      },
      "workers": {
        "active": 2,
        "max": 4,
        "utilization": "50.0%"
      },
      "system": {
        "cpu_percent": "15.2",
        "memory_percent": "45.8",
        "cpu_cores": 8
      },
      "performance": {
        "realistic_throughput_per_minute": 26.7,
        "current_queue_wait_minutes": 1
      },
      "queue": {
        "total": 10,
        "size": 5,
        "queued": 3,
        "processing": 2,
        "completed": 5,
        "failed": 0
      },
      "timestamp": "2025-12-05T10:00:00.000Z"
    }
    ```
