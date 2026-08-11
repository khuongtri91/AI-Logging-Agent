PYTHON ?= python

.PHONY: help install run run-ui test clean

help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies"
	@echo "  make run      - Run the AI logging agent"
	@echo "  make run-ui   - Run the Streamlit web interface"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Clean up generated files"

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m streamlit run streamlit_app.py

run-ui:
	$(PYTHON) -m streamlit run streamlit_app.py

test:
	$(PYTHON) -m pytest tests/test_config.py tests/test_response.py tests/test_log_reader.py tests/test_tools_call.py tests/test_source_tools.py tests/test_model.py tests/test_log_analyzer.py tests/test_main.py tests/test_ui.py tests/test_memory.py tests/test_sources.py -v --cov=src --cov-report=term-missing --cov-fail-under=80

clean:
	$(PYTHON) -c "import pathlib, shutil; skipped = {'.venv', '.git', '.agents'}; [shutil.rmtree(path) for path in pathlib.Path('.').rglob('__pycache__') if path.is_dir() and not skipped.intersection(path.parts)]; [path.unlink() for path in pathlib.Path('.').rglob('*.pyc') if path.is_file() and not skipped.intersection(path.parts)]"
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(path) for path in [pathlib.Path('.pytest_cache'), pathlib.Path('htmlcov')] if path.exists()]; [path.unlink() for path in [pathlib.Path('.coverage'), pathlib.Path('coverage.xml')] if path.exists()]"
