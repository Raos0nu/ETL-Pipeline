"""
Configuration management for the ETL Pipeline
Uses environment variables with sensible defaults
"""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = "sqlite:///sales.db"
    pool_size: int = 5
    max_overflow: int = 10
    pool_pre_ping: bool = True
    echo: bool = False


@dataclass
class ETLConfig:
    """ETL Pipeline configuration"""
    data_file: str = "data/sample_sales.csv"
    batch_size: int = 1000
    enable_incremental: bool = True
    enable_data_quality_checks: bool = True
    max_retries: int = 3
    retry_delay: int = 1


@dataclass
class AppConfig:
    """Application configuration"""
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "5000"))
    api_version: str = "v1"
    cors_origins: list = None
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    def __post_init__(self):
        if self.cors_origins is None:
            cors_env = os.getenv("CORS_ORIGINS", "*")
            self.cors_origins = [origin.strip() for origin in cors_env.split(",")]


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "True").lower() == "true"
    metrics_port: int = int(os.getenv("METRICS_PORT", "9090"))
    enable_tracing: bool = os.getenv("ENABLE_TRACING", "False").lower() == "true"
    log_file: Optional[str] = os.getenv("LOG_FILE", None)
    log_format: str = os.getenv("LOG_FORMAT", "json")  # json or text


class Config:
    """Main configuration class"""
    
    def __init__(self):
        # Ensure data directory exists
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Load configurations
        self.app = AppConfig()
        self.database = DatabaseConfig(
            url=os.getenv("DATABASE_URL", "sqlite:///sales.db")
        )
        self.etl = ETLConfig(
            data_file=os.getenv("DATA_FILE", "data/sample_sales.csv")
        )
        self.monitoring = MonitoringConfig()
        
        # Set log file path if not absolute
        if self.monitoring.log_file and not Path(self.monitoring.log_file).is_absolute():
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            self.monitoring.log_file = str(log_dir / self.monitoring.log_file)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return not self.is_production


# Global configuration instance
config = Config()
