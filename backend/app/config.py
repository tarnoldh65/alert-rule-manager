from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://alertmanager:alertmanager@localhost:5432/alertmanager"
    ingest_host: str = "0.0.0.0"
    ingest_port: int = 7754
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALERT_MANAGER_")


settings = Settings()
