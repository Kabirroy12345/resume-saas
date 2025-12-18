from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import os

from .database import get_db
from .models import User
from dotenv import load_dotenv

load_dotenv()

# Argon2 for hashing
ph = PasswordHasher()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback_dev_secret_key_dont_use_in_prod_123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# ------------------------------
# HASH PASSWORD
# ------------------------------
def hash_password(password: str) -> str:
    return ph.hash(password)

# ------------------------------
# VERIFY PASSWORD
# ------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except Exception:
        return False

# ------------------------------
# JWT TOKEN CREATOR
# ------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ------------------------------
# GET CURRENT USER FROM TOKEN
# ------------------------------
def get_current_user(token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
    )

    try:
        print(f"DEBUG: Token received: {token[:20]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"DEBUG: Decoded email: {email}")
        if not email:
            print("DEBUG: No email in payload")
            raise credentials_exception
    except JWTError as e:
        print(f"DEBUG: JWT Decode Error: {str(e)}")
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise credentials_exception

    return user
