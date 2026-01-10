"""
SQLAlchemy ORM models for the ETL Pipeline
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from datetime import datetime
from typing import Optional, Generator
from contextlib import contextmanager
import os

import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from config import config
except ImportError:
    # Fallback configuration
    class Config:
        class DatabaseConfig:
            url = "sqlite:///sales.db"
            echo = False
            pool_size = 5
            max_overflow = 10
            pool_pre_ping = True
        database = DatabaseConfig()
    config = Config()

try:
    from backend.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

Base = declarative_base()


class SalesRecord(Base):
    """Sales record model"""
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, nullable=False, index=True)
    product = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Add indexes for common queries
    __table_args__ = (
        Index('idx_order_product', 'order_id', 'product'),
        Index('idx_created_at', 'created_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert model instance to dictionary"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product": self.product,
            "quantity": self.quantity,
            "price": self.price,
            "total_price": self.total_price,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f"<SalesRecord(order_id={self.order_id}, product='{self.product}', total_price={self.total_price})>"


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database connection"""
        try:
            db_url = config.database.url
            
            # Special handling for SQLite
            if db_url.startswith("sqlite"):
                # Use StaticPool for SQLite to allow multiple connections
                connect_args = {"check_same_thread": False}
                poolclass = StaticPool
            else:
                connect_args = {}
                poolclass = None
            
            # Create engine
            engine_kwargs = {
                "echo": config.database.echo,
                "connect_args": connect_args,
            }
            
            if poolclass:
                engine_kwargs["poolclass"] = poolclass
            elif not db_url.startswith("sqlite"):
                engine_kwargs.update({
                    "pool_size": config.database.pool_size,
                    "max_overflow": config.database.max_overflow,
                    "pool_pre_ping": config.database.pool_pre_ping,
                })
            
            self.engine = create_engine(db_url, **engine_kwargs)
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("Database initialized successfully", extra={
                "extra_fields": {"database_url": db_url.split("@")[-1] if "@" in db_url else db_url}
            })
            
        except Exception as e:
            logger.error("Failed to initialize database", exc_info=True, extra={
                "extra_fields": {"error": str(e)}
            })
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Database session error", exc_info=True, extra={
                "extra_fields": {"error": str(e)}
            })
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """Get database session (manual cleanup required)"""
        return self.SessionLocal()
    
    def health_check(self) -> bool:
        """Check database health"""
        try:
            with self.get_session() as session:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database health check failed", extra={
                "extra_fields": {"error": str(e)}
            })
            return False


# Global database manager instance
db_manager = DatabaseManager()
