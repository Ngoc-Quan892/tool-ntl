"""
Configuration management using Pydantic Settings

Loads from environment variables and .env file
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # App Info
    APP_NAME: str = "Baccarat Predictor Pro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Database
    # NOTE: Do not hardcode credentials. In production, set `DATABASE_URL` via environment.
    # Example: postgresql://<user>:<password>@<host>:5432/<db>
    # Leave empty by default to avoid accidental credential-like patterns in the repository.
    DATABASE_URL: str = ""
    DB_ECHO: bool = False  # Log SQL queries
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    REDIS_MAX_CONNECTIONS: int = 50
    
    # InfluxDB (Time series metrics)
    INFLUXDB_URL: Optional[str] = None
    INFLUXDB_TOKEN: Optional[str] = None
    INFLUXDB_ORG: Optional[str] = None
    INFLUXDB_BUCKET: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080"
    ]
    
    # Security
    # SECRET_KEY must be provided via environment in production. Keep this blank here
    # to avoid accidental use of a hardcoded secret. Set in `.env` or CI secrets.
    SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 20
    
    # Simulation
    MAX_SIMULATION_SHOES: int = 10000
    SIMULATION_BATCH_SIZE: int = 100
    SIMULATION_TIMEOUT_SECONDS: int = 300
    
    # Machine Learning
    ML_MODEL_PATH: str = "./ml-training/models/"
    ML_CACHE_PREDICTIONS: bool = True
    ML_FEATURE_COUNT: int = 20
    
    # Card Counting
    RESHUFFLE_POINT: int = 20  # Cards remaining when reshuffling
    DEFAULT_DECKS: int = 8
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 100
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # Alerting
    ALERT_ENABLED: bool = True
    ALERT_CHECK_INTERVAL: int = 60  # seconds
    SLACK_WEBHOOK_URL: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ALERT_EMAIL: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Use this function to access settings throughout the app
    """
    return Settings()


# Singleton instance
settings = get_settings()

