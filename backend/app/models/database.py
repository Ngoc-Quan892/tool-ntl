"""
Database models and session management with PostgreSQL/SQLAlchemy.

Features:
- Connection pooling
- Session management
- Migration setup with Alembic
- Database manager class
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    create_engine,
    event,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Base = declarative_base()


class DatabaseManager:
    """Database manager with connection pooling and session management."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: Database connection string. If None, uses settings.DATABASE_URL
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._initialize_engine()

    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine with connection pooling."""
        # Configure connection args based on database type
        connect_args = {}
        if self.database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        elif self.database_url.startswith("postgresql"):
            # PostgreSQL connection pooling settings
            connect_args = {
                "connect_timeout": 10,
                "application_name": settings.APP_NAME,
            }

        # Create engine with connection pooling
        poolclass = None if self.database_url.startswith("sqlite") else QueuePool

        self.engine = create_engine(
            self.database_url,
            connect_args=connect_args,
            echo=settings.DB_ECHO,
            poolclass=poolclass,
            pool_size=settings.DB_POOL_SIZE if poolclass else None,
            max_overflow=settings.DB_MAX_OVERFLOW if poolclass else None,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
            future=True,
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

        # Log connection info
        logger.info(f"Database engine initialized: {self.database_url.split('@')[-1] if '@' in self.database_url else self.database_url}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session context manager.

        Usage:
            with db_manager.get_session() as session:
                # Use session
                pass
        """
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call _initialize_engine() first.")

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_db(self) -> Generator[Session, None, None]:
        """
        FastAPI dependency for database sessions.

        Usage:
            @app.get("/items")
            def get_items(db: Session = Depends(db_manager.get_db)):
                return db.query(Item).all()
        """
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call _initialize_engine() first.")

        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_tables(self) -> None:
        """Create all tables defined in Base metadata."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized.")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created.")

    def drop_tables(self) -> None:
        """Drop all tables. Use with caution!"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized.")
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All database tables dropped.")

    def health_check(self) -> bool:
        """
        Check database connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not self.engine:
                return False
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Initialize global database manager
db_manager = DatabaseManager()


# Database Models
class GameResult(Base):
    """Game result model storing each baccarat hand result."""

    __tablename__ = "game_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    result = Column(String(1), nullable=False, index=True)  # B, P, or T
    prediction = Column(JSON, nullable=True)  # Full prediction object
    shoe_number = Column(Integer, default=1, index=True)
    hand_number = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    true_count = Column(Float, nullable=True)
    edge = Column(Float, nullable=True)

    # Composite index for common queries
    __table_args__ = (
        Index("idx_game_results_shoe_hand", "shoe_number", "hand_number"),
        Index("idx_game_results_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<GameResult(id={self.id}, result={self.result}, shoe={self.shoe_number}, hand={self.hand_number})>"


class SimulationRun(Base):
    """Simulation run model for tracking batch simulations."""

    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String(50), unique=True, nullable=False, index=True)
    total_shoes = Column(Integer, nullable=False)
    completed_shoes = Column(Integer, default=0, nullable=False)
    results = Column(JSON, nullable=True)  # Simulation results summary
    status = Column(String(20), nullable=False, index=True, default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_simulation_runs_status", "status"),
        Index("idx_simulation_runs_task_id", "task_id"),
    )

    def __repr__(self) -> str:
        return f"<SimulationRun(id={self.id}, task_id={self.task_id}, status={self.status})>"


# Convenience function for FastAPI dependency injection
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    yield from db_manager.get_db()


# Event listeners for connection management
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance."""
    if db_manager.database_url.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
