# Runbook

Run commands from the project root: `E:\projects\ai-logging-agents`.

## Install Dependencies

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If the virtual environment is already active:

```powershell
python -m pip install -r requirements.txt
```

## Run Streamlit App

```powershell
.venv\Scripts\python.exe -m streamlit run src/main.py
```

Or, if `make` is available:

```powershell
make run
```

Streamlit usually opens:

```text
http://localhost:8501
```

## Run Tests

```powershell
.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_response.py tests/test_log_reader.py tests/test_tools_call.py tests/test_model.py tests/test_log_analyzer.py tests/test_main.py tests/test_ui.py -v --cov=src --cov-report=term-missing --cov-fail-under=80
```

Or:

```powershell
make test
```

## Clean Generated Files

```powershell
make clean
```

If `make` is unavailable, remove generated caches manually:

- `__pycache__/`
- `.pytest_cache/`
- `.coverage`
- `htmlcov/`

## Useful Smoke Checks

Compile Python files:

```powershell
.venv\Scripts\python.exe -m compileall src tests
```

Check Streamlit import:

```powershell
.venv\Scripts\python.exe -c "import streamlit; print(streamlit.__version__)"
```
