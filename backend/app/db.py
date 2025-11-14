from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import contextmanager
from config import config

DATABASE_URL = config.DATABASE_URL

# ✅ Improved, production-safe engine configuration
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # ✅ Checks connection health before reusing it
    pool_recycle=1800,       # ✅ Reconnects every 30 minutes (avoid idle timeout)
    connect_args={"sslmode": "require"}  # ✅ Ensures SSL connection stays valid
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# ✅ Dependency for FastAPI routes
def get_db():
    """Generator for FastAPI Depends() dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Context manager for non-route code (background tasks, utilities)
@contextmanager
def get_db_context():
    """Context manager for database sessions in background tasks and utility functions"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
