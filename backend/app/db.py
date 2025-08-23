from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Import configuration first
from config import config


# # Database setup
DATABASE_URL = config.DATABASE_URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
