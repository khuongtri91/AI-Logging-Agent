from functools import lru_cache
from pathlib import Path

from langchain_core.tools import tool

from src.utils import get_settings

@tool
def read_log_file(filename: str) -> str:
    """
    Read contents of a log file from the logs directory.
    
    Args:
        filename: Name of the log file (e.g., 'app.log', 'error.log')
    
    Returns:
        String containing the log file contents, or error message if file not found
    """
    settings = get_settings()

    try:
        log_path = _resolve_log_path(filename)
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add metadata
        file_size = log_path.stat().st_size
        line_count = content.count('\n') + 1
        
        return f"File: {filename}\nSize: {file_size} bytes\nLines: {line_count}\n\n{content}"
    
    except FileNotFoundError:
        return f"Error: Log file '{filename}' not found in {settings.log_directory}/ directory"
    except PermissionError:
        return f"Error: Permission denied reading '{filename}'"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error reading '{filename}': {str(e)}"

@tool
def list_log_files() -> str:
    """
    List all available log files in the logs directory.
    
    Returns:
        String containing list of available log files with their sizes
    """
    settings = get_settings()
    log_dir = Path(settings.log_directory)
    
    if not log_dir.exists():
        return f"Error: Log directory '{settings.log_directory}' does not exist"
    
    try:
        log_files = [f for f in log_dir.iterdir() if f.is_file() and f.suffix == '.log']
        
        if not log_files:
            return f"No .log files found in {settings.log_directory}/ directory"
        
        result = f"Available log files in {settings.log_directory}/:\n\n"
        for log_file in sorted(log_files):
            size = log_file.stat().st_size
            size_kb = size / 1024
            result += f"  - {log_file.name} ({size_kb:.2f} KB)\n"
        
        return result
    
    except Exception as e:
        return f"Error listing log files: {str(e)}"

@tool
def search_logs(filename: str, search_term: str) -> str:
    """
    Search for a specific term in a log file and return matching lines.
    
    Args:
        filename: Name of the log file to search
        search_term: Term to search for (case-insensitive)
    
    Returns:
        String containing matching log lines with line numbers
    """
    try:
        log_path = _resolve_log_path(filename)
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        matches = []
        for line_num, line in enumerate(lines, 1):
            if search_term.lower() in line.lower():
                matches.append(f"Line {line_num}: {line.rstrip()}")
        
        if not matches:
            return f"No matches found for '{search_term}' in {filename}"
        
        result = f"Found {len(matches)} matches for '{search_term}' in {filename}:\n\n"
        result += '\n'.join(matches)
        
        return result
    
    except FileNotFoundError:
        return f"Error: Log file '{filename}' not found"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error searching '{filename}': {str(e)}"

def _resolve_log_path(filename: str) -> Path:
    """Resolve a log filename inside the configured log directory."""
    settings = get_settings()
    log_dir = Path(settings.log_directory).resolve()
    log_path = (log_dir / filename).resolve()

    if log_dir not in log_path.parents and log_path != log_dir:
        raise ValueError("Log filename must stay inside the configured log directory")

    return log_path

@lru_cache
def get_log_tools() -> list:
    """
    Get all log-related tools for the agent.
    
    Returns:
        List of tool functions
    """
    return [read_log_file, list_log_files, search_logs]
