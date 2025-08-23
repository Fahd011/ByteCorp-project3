from app.db import SessionLocal
from app.models import User
from app.utils import hash_password
from config import config

def seed():
    db = SessionLocal()
    test_email = config.ROOT_USER_EMAIL
    test_password = config.ROOT_USER_PASSWORD

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == test_email).first()
    if existing_user:
        print(f"User '{test_email}' already exists.")
    else:
        hashed_password = hash_password(test_password)
        new_user = User(email=test_email, password_hash=hashed_password)
        db.add(new_user)
        db.commit()
        print(f"User '{test_email}' created with password '{test_password}'.")
    db.close()

if __name__ == "__main__":
    seed()
