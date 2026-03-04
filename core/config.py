"""
Core configuration — reads from .env and exposes typed settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Twilio / WhatsApp
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"

    # Database
    database_url: str = "sqlite+aiosqlite:///./raveya.db"

    # App
    app_env: str = "development"
    app_port: int = 8000
    log_level: str = "INFO"

    # Escalation target
    escalation_phone: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
