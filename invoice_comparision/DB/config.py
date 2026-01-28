import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class BaseAppSettings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Use modern Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",  # No prefix for environment variables
        extra="ignore"  # Ignore extra environment variables
    )

    # Application Configuration
    app_name: str = "Invoice Comparision"
    APP_CREATED_BY: str = "system"
    app_version: str = "1.0.0"

    # Database Configuration
    db_host: str = "behelp.c7cg6ews0pdl.ap-south-1.rds.amazonaws.com"
    db_port: int = 5432
    db_name: str = "Invoice_Pipeline"
    db_user: str = "postgres"
    db_password: str = "Aust1n24$"

    # OpenAI Configuration
    openai_api_key: Optional[str] = None

    @property
    def database_url(self) -> str:
        """Construct database URL dynamically"""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = BaseAppSettings()
