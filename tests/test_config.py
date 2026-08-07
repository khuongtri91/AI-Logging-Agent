import pytest
from pydantic import ValidationError

from src.utils import Settings


def test_settings_accepts_valid_configuration():
    settings = Settings(
        gemini_api_model="gemini-test",
        gemini_api_key="test-key",
        temperature=0.2,
        log_directory="logs",
    )

    assert settings.gemini_api_model == "gemini-test"
    assert settings.max_iterations == 5
    assert "DevOps AI agent" in settings.get_system_prompt()
    assert "incident response" in settings.get_system_prompt()


def test_settings_rejects_empty_api_key():
    with pytest.raises(ValidationError):
        Settings(
            gemini_api_model="gemini-test",
            gemini_api_key="",
            temperature=0.2,
            log_directory="logs",
        )


def test_settings_rejects_system_prompt_outside_project_root():
    with pytest.raises(ValidationError):
        Settings(
            gemini_api_model="gemini-test",
            gemini_api_key="test-key",
            temperature=0.2,
            log_directory="logs",
            system_prompt_path="docs/system_prompt.txt",
        )
