"""
Core configuration — reads from .env and exposes typed settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # AI Provider — supports "openai" or "groq" (free)
    ai_provider: str = "openai"

    # OpenAI (accepts OPENAI_API_KEY or OPENAI_KEY)
    openai_api_key: str = ""   # set via OPENAI_API_KEY
    openai_key: str = ""       # fallback alias set via OPENAI_KEY
    openai_model: str = "gpt-4o-mini"

    # Groq (free — https://console.groq.com)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Twilio / WhatsApp
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "raveya"

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
