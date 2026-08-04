from types import SimpleNamespace

from src.tools import log_reader


def configure_logs(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(
        log_reader,
        "get_settings",
        lambda: SimpleNamespace(log_directory=str(log_dir)),
    )
    return log_dir


def test_list_log_files(monkeypatch, tmp_path):
    log_dir = configure_logs(monkeypatch, tmp_path)
    (log_dir / "app.log").write_text("INFO ready\n", encoding="utf-8")
    (log_dir / "notes.txt").write_text("ignore me", encoding="utf-8")

    result = log_reader.list_log_files.invoke({})

    assert "Available log files" in result
    assert "app.log" in result
    assert "notes.txt" not in result


def test_list_log_files_handles_missing_directory(monkeypatch, tmp_path):
    missing_dir = tmp_path / "missing"
    monkeypatch.setattr(
        log_reader,
        "get_settings",
        lambda: SimpleNamespace(log_directory=str(missing_dir)),
    )

    result = log_reader.list_log_files.invoke({})

    assert "does not exist" in result


def test_list_log_files_handles_empty_directory(monkeypatch, tmp_path):
    configure_logs(monkeypatch, tmp_path)

    result = log_reader.list_log_files.invoke({})

    assert "No .log files found" in result


def test_read_log_file(monkeypatch, tmp_path):
    log_dir = configure_logs(monkeypatch, tmp_path)
    (log_dir / "app.log").write_text("INFO ready\nERROR failed\n", encoding="utf-8")

    result = log_reader.read_log_file.invoke({"filename": "app.log"})

    assert "File: app.log" in result
    assert "Lines: 3" in result
    assert "ERROR failed" in result


def test_read_log_file_handles_missing_file(monkeypatch, tmp_path):
    configure_logs(monkeypatch, tmp_path)

    result = log_reader.read_log_file.invoke({"filename": "missing.log"})

    assert "not found" in result


def test_read_log_file_rejects_path_traversal(monkeypatch, tmp_path):
    configure_logs(monkeypatch, tmp_path)

    result = log_reader.read_log_file.invoke({"filename": "../secret.log"})

    assert "must stay inside" in result


def test_search_logs_finds_case_insensitive_matches(monkeypatch, tmp_path):
    log_dir = configure_logs(monkeypatch, tmp_path)
    (log_dir / "app.log").write_text("INFO ready\nerror failed\n", encoding="utf-8")

    result = log_reader.search_logs.invoke({
        "filename": "app.log",
        "search_term": "ERROR",
    })

    assert "Found 1 matches" in result
    assert "Line 2: error failed" in result


def test_search_logs_handles_no_matches(monkeypatch, tmp_path):
    log_dir = configure_logs(monkeypatch, tmp_path)
    (log_dir / "app.log").write_text("INFO ready\n", encoding="utf-8")

    result = log_reader.search_logs.invoke({
        "filename": "app.log",
        "search_term": "ERROR",
    })

    assert "No matches found" in result


def test_search_logs_handles_missing_file(monkeypatch, tmp_path):
    configure_logs(monkeypatch, tmp_path)

    result = log_reader.search_logs.invoke({
        "filename": "missing.log",
        "search_term": "ERROR",
    })

    assert "not found" in result


def test_get_log_tools_returns_all_tools():
    tool_names = {tool.name for tool in log_reader.get_log_tools()}

    assert tool_names == {"read_log_file", "list_log_files", "search_logs"}
