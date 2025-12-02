# AI Document Understanding API - Setup Guide

## 🚀 Quick Start with Docker

### Prerequisites
- Docker & Docker Compose installed
- **Ollama** installed locally (for AI extraction)

### 1. Install Ollama (Free Local AI)

**Windows:**
```bash
# Download from https://ollama.com/download
# Or use winget
winget install Ollama.Ollama
```

**Mac/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull the AI Model

```bash
# Pull Llama 3.2 (free, runs locally)
ollama pull llama3.2
```

### 3. Start Ollama Server

```bash
# Start Ollama (it runs on http://localhost:11434)
ollama serve
```

### 4. Build and Run the Application

```bash
# Build and start all services
docker-compose up --build
```

This will start:
- **API** (Django) on `http://localhost:8000`
- **Redis** (message broker) on `localhost:6379`
- **Celery Worker** (async processing)

### 5. Run Migrations

```bash
# In a new terminal
docker-compose exec api python manage.py migrate
```

### 6. Create Superuser (Optional)

```bash
docker-compose exec api python manage.py createsuperuser
```

---

## 📋 Environment Variables

Create a `.env` file in the project root:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Email (for authentication)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com

# Celery & Redis
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# OCR
TESSERACT_CMD=/usr/bin/tesseract

# AI (Ollama)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2
```

---

## 🎯 How It Works

### Document Processing Flow:

1. **Upload Document** → `POST /api/documents/`
2. **Trigger Extraction** → `POST /api/documents/{id}/extract/`
3. **Celery Worker** processes async:
   - **OCR** extracts text (Tesseract)
   - **AI** extracts structured data (Ollama + Llama 3.2)
4. **Check Status** → `GET /api/documents/jobs/{job_id}/`
5. **Get Results** → `GET /api/documents/jobs/{job_id}/results/`

---

## 🧪 Testing the API

### 1. Register & Login

```bash
# Register
curl -X POST http://localhost:8000/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "Test@12345",
    "first_name": "Test",
    "last_name": "User"
  }'

# Verify email (check console for OTP)

# Login
curl -X POST http://localhost:8000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test@12345"
  }'
```

### 2. Upload Document

```bash
curl -X POST http://localhost:8000/documents/ \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -F "file=@/path/to/invoice.pdf" \
  -F "document_type=invoice"
```

### 3. Trigger Extraction

```bash
curl -X POST http://localhost:8000/documents/{DOCUMENT_ID}/extract/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### 4. Check Job Status

```bash
curl -X GET http://localhost:8000/documents/jobs/{JOB_ID}/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### 5. Get Results

```bash
curl -X GET http://localhost:8000/documents/jobs/{JOB_ID}/results/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

---

## 🛠️ Tech Stack (100% Free)

- **Backend**: Django + DRF
- **OCR**: Tesseract (open-source)
- **AI**: Ollama + Llama 3.2 (runs locally, free)
- **Async**: Celery + Redis
- **PDF**: PyMuPDF
- **Database**: SQLite (dev) / PostgreSQL (prod)

---

## 📊 Monitoring

### View Celery Logs

```bash
docker-compose logs -f celery
```

### View API Logs

```bash
docker-compose logs -f api
```

### Access Django Admin

```
http://localhost:8000/admin/
```

---

## 🔧 Troubleshooting

### Ollama Connection Issues

If you get "Connection refused" errors:

1. Make sure Ollama is running: `ollama serve`
2. Check the URL in `.env`: `OLLAMA_BASE_URL=http://host.docker.internal:11434`
3. On Linux, use `http://172.17.0.1:11434` instead

### Tesseract Not Found

If OCR fails:

```bash
# Check Tesseract is installed in container
docker-compose exec api tesseract --version
```

### Celery Worker Not Processing

```bash
# Restart Celery worker
docker-compose restart celery

# Check Redis connection
docker-compose exec api python -c "import redis; r = redis.Redis(host='redis'); print(r.ping())"
```

---

## 🎉 Next Steps

1. ✅ Test with real invoices, receipts, contracts
2. ✅ Fine-tune AI prompts for better extraction
3. ✅ Add more document types
4. ✅ Implement webhooks for completion notifications
5. ✅ Add document classification (auto-detect type)
6. ✅ Build frontend dashboard

---

## 📝 API Documentation

Access interactive API docs:
- **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`
