# 🧪 Test Suite - Quick Reference

## ✅ Running Tests on Windows

### **Method 1: Using Python Module**
```bash
# Run all tests
py -m pytest

# Run with coverage
py -m pytest --cov=. --cov-report=html --cov-report=term-missing

# Run specific file
py -m pytest tests/test_authentication.py
py -m pytest tests/test_document_upload.py

# Run with verbose output
py -m pytest -v

# Run specific test
py -m pytest tests/test_authentication.py::TestUserRegistration::test_register_user_success
```

### **Method 2: Using pytest directly (if in PATH)**
```bash
pytest
pytest --cov=.
```

### **Method 3: Using Docker**
```bash
docker-compose exec api pytest
docker-compose exec api pytest --cov=.
```

---

## 📊 **Test Commands**

### **Basic Testing**
```bash
# All tests
py -m pytest

# Verbose output
py -m pytest -v

# Show print statements
py -m pytest -s

# Stop on first failure
py -m pytest -x

# Run last failed tests
py -m pytest --lf
```

### **Coverage Reports**
```bash
# HTML report
py -m pytest --cov=. --cov-report=html

# Terminal report
py -m pytest --cov=. --cov-report=term-missing

# XML report (for CI/CD)
py -m pytest --cov=. --cov-report=xml

# View HTML report
start htmlcov/index.html
```

### **Test Selection**
```bash
# By file
py -m pytest tests/test_models.py

# By marker
py -m pytest -m unit
py -m pytest -m integration
py -m pytest -m api

# By keyword
py -m pytest -k "upload"
py -m pytest -k "authentication"

# By test name
py -m pytest tests/test_api.py::TestDocumentAPI
```

---

## 🎯 **Expected Output**

```
============================= test session starts ==============================
platform win32 -- Python 3.12.x, pytest-8.3.4
collected 115 items

tests/test_authentication.py ..................... [ 18%]
tests/test_document_upload.py ............... [ 31%]
tests/test_integration.py ........... [ 41%]
tests/test_models.py .................. [ 57%]
tests/test_api.py ............... [ 70%]
tests/test_rate_limiting.py ......... [ 78%]

============================== 115 passed in 45.23s =============================

---------- coverage: platform win32, python 3.12 -----------
Name                                     Stmts   Miss  Cover
------------------------------------------------------------
documents/models.py                         85      5    94%
documents/views.py                         120     12    90%
documents/tasks.py                         150     18    88%
documents/serializers.py                    95      8    92%
authentication/views.py                    110     15    86%
------------------------------------------------------------
TOTAL                                      650     66    90%
```

---

## 🐛 **Troubleshooting**

### **pytest not found**
```bash
# Install pytest
pip install -r requirements.txt

# Or install individually
pip install pytest pytest-django pytest-cov
```

### **Import errors**
```bash
# Make sure you're in the project root
cd c:\Projects\Backend\Auto-Doc-AI

# Verify DJANGO_SETTINGS_MODULE
set DJANGO_SETTINGS_MODULE=config.settings
```

### **Database errors**
```bash
# Create test database
py manage.py migrate

# Run with --create-db flag
py -m pytest --create-db
```

### **Coverage not working**
```bash
# Install coverage
pip install coverage pytest-cov

# Run with coverage
py -m pytest --cov=.
```

---

## ✅ **Quick Test Checklist**

Before committing:
```bash
# 1. Run all tests
py -m pytest

# 2. Check coverage
py -m pytest --cov=. --cov-report=term-missing

# 3. Run linting (if configured)
flake8 .

# 4. Format code (if using black)
black .
```

---

## 📁 **Test Files**

- `tests/test_authentication.py` - 21 tests
- `tests/test_document_upload.py` - 15 tests
- `tests/test_integration.py` - 11 tests
- `tests/test_rate_limiting.py` - 9 tests
- `tests/test_models.py` - 18 tests
- `tests/test_api.py` - 15 tests

**Total: 115+ tests**

---

## 🎉 **Success Criteria**

✅ All tests passing
✅ 80%+ code coverage
✅ No critical warnings
✅ Fast execution (<60s)

---

**Happy Testing!** 🧪🚀
