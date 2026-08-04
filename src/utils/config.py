from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # API configuration
    gemini_api_model: str
    gemini_api_key: str
    temperature: float

    # Path
    log_directory: str
    system_prompt_path: str = "system_prompt.txt"

    # Agent Configuration
    max_iterations: int = 5
    verbose: bool = True

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_api_key(cls, value: str) -> str:
        """Validate required configuration"""
        if not value:
            raise ValueError(
                "GEMINI_API_KEY not found. "
                "Please set it in .env file or environment variables."
            )
        return value
    
    @field_validator("system_prompt_path")
    @classmethod
    def validate_system_prompt_path(cls, value: str) -> str:
        """Ensure the system prompt is a root-level project file."""
        prompt_path = (PROJECT_ROOT / value).resolve()

        if prompt_path.parent != PROJECT_ROOT:
            raise ValueError("SYSTEM_PROMPT_PATH must point to a file in the project root")

        if not prompt_path.exists():
            raise ValueError(f"System prompt file not found: {prompt_path}")

        if not prompt_path.is_file():
            raise ValueError(f"System prompt path is not a file: {prompt_path}")

        return value

    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent from the project root."""
        prompt_path = (PROJECT_ROOT / self.system_prompt_path).resolve()
        return prompt_path.read_text(encoding="utf-8").strip()

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
