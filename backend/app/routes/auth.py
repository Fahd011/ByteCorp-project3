from config import config
from fastapi import status, APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime
from sqlalchemy.orm import Session
from datetime import datetime, timedelta


from app.db import get_db
from app.utils import hash_password, verify_password
from app.models import User,UserCreate, UserLogin, Token

import jwt

router = APIRouter()

# Security scheme
security = HTTPBearer(auto_error=False)

@router.post("/api/auth/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create new user with hashed password
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate access token
    access_token = create_access_token(data={"sub": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/api/auth/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    print(f"🔍 Login attempt for email: {user_credentials.email}")
    
    # First, check against root user credentials from environment variables
    if (config.ROOT_USER_EMAIL and config.ROOT_USER_PASSWORD and
        user_credentials.email == config.ROOT_USER_EMAIL and
        user_credentials.password == config.ROOT_USER_PASSWORD):
        print(f"✅ Root user authentication successful")
        # Create a token with root user identifier
        access_token = create_access_token(data={"sub": config.ROOT_USER_EMAIL, "is_root": True})
        return {"access_token": access_token, "token_type": "bearer"}
    
    # If not root user, check database
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user:
        print(f"❌ User not found for email: {user_credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"✅ User found: {user.email}")
    print(f"🔍 Verifying password...")
    
    if not verify_password(user_credentials.password, user.password_hash):
        print(f"❌ Password verification failed for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


# JWT functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        if not credentials.credentials:
            print("[verify_token] No token provided!")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
