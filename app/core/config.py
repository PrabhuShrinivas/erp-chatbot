from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    LLM_PROVIDER: str = "openrouter"
    LLM_MODEL: str = "gpt-oss-120b"
    LLM_API_KEY: str
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
