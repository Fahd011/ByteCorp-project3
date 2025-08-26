from app.db import SessionLocal
from app.models import User, Provider
from app.utils import hash_password
from config import config

# Provider data to seed
PROVIDERS_DATA = [
    {
        "name": "Duke Energy",
        "login_url": "https://duke-energy.com/my-account/sign-in",
        "billing_url": "https://businessportal2.duke-energy.com/billinghistory",
        "extras": {
            "wait_text": "Billing & Payment Activity"
        }
    }
    # Add more providers here in the future
    # {
    #     "name": "Another Provider",
    #     "login_url": "https://example.com/login",
    #     "billing_url": "https://example.com/billing",
    #     "extras": {
    #         "wait_text": "Some text to wait for"
    #     }
    # }
]

def seed():
    db = SessionLocal()
    
    # Seed users
    seed_users(db)
    
    # Seed providers
    seed_providers(db)
    
    db.close()

def seed_users(db):
    """Seed default users"""
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

def seed_providers(db):
    """Seed providers"""
    for provider_data in PROVIDERS_DATA:
        # Check if provider already exists
        existing_provider = db.query(Provider).filter(Provider.name == provider_data["name"]).first()
        if existing_provider:
            print(f"Provider '{provider_data['name']}' already exists.")
        else:
            new_provider = Provider(
                name=provider_data["name"],
                login_url=provider_data["login_url"],
                billing_url=provider_data["billing_url"],
                extras=provider_data.get("extras")
            )
            db.add(new_provider)
            db.commit()
            print(f"Provider '{provider_data['name']}' created successfully.")

if __name__ == "__main__":
    seed()
