# 🚀 Quick Start Guide - PostgreSQL + Testing

## 📋 TL;DR

```bash
# Local Development (SQLite)
DEBUG=True
python manage.py migrate
pytest

# Docker (PostgreSQL)
docker-compose up --build
docker-compose exec api pytest

# Production (PostgreSQL)
DEBUG=False
DATABASE_URL=postgresql://user:pass@host:port/db
python manage.py migrate
pytest
```

---

## 🎯 Quick Commands

### **Run Tests**
```bash
# All tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific tests
pytest tests/test_models.py
pytest -m unit
pytest -m api
```

### **Database**
```bash
# Migrate
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Shell
python manage.py shell
```

### **Docker**
```bash
# Start
docker-compose up --build

# Stop
docker-compose down

# Clean restart
docker-compose down -v
docker-compose up --build

# Run tests
docker-compose exec api pytest

# Logs
docker-compose logs -f api
docker-compose logs -f celery
docker-compose logs -f db
```

---

## ✅ Verification

```bash
# Check database connection
python manage.py check --database default

# Run migrations
python manage.py migrate

# Run tests
pytest

# Check coverage
pytest --cov=. --cov-report=term-missing
```

---

## 🔧 Environment Setup

### **.env for Local Development**
```env
DEBUG=True
USE_DOCKER=False
SECRET_KEY=your-secret-key
```

### **.env for Docker**
```env
DEBUG=True
USE_DOCKER=True
POSTGRES_DB=autodoc_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### **.env for Production**
```env
DEBUG=False
DATABASE_URL=postgresql://user:password@host:port/dbname
SECRET_KEY=strong-secret-key
```

---

## 📊 Test Results

Expected output:
```
============================= test session starts ==============================
collected 43 items

tests/test_models.py ..................                                  [ 41%]
tests/test_api.py ...............                                        [ 76%]
tests/test_integration.py ..........                                     [100%]

============================== 43 passed in 5.23s ===============================

---------- coverage: platform linux, python 3.12 -----------
Name                                     Stmts   Miss  Cover
------------------------------------------------------------
documents/models.py                         85      5    94%
documents/views.py                         120     12    90%
documents/tasks.py                         150     18    88%
documents/serializers.py                    65      3    95%
------------------------------------------------------------
TOTAL                                      420     38    91%
```

---

## 🐛 Common Issues

### **Issue**: Tests fail with database error
**Solution**:
```bash
python manage.py migrate
pytest --create-db
```

### **Issue**: Docker database not connecting
**Solution**:
```bash
docker-compose down -v
docker-compose up --build
```

### **Issue**: Import errors in tests
**Solution**:
```bash
pip install -r requirements.txt
```

---

## 🎉 Success!

If you see:
- ✅ 43+ tests passing
- ✅ 80%+ coverage
- ✅ All services healthy in Docker

**You're ready for production!** 🚀
