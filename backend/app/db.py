from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
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

# ✅ Dependency for FastAPI / background jobs
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
