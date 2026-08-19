from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Adjust these two imports based on your exact file structure!
from app.database.connection import get_db 
from app.models.core import Customer

# ==========================================
# 1. SECURITY CONFIGURATION
# ==========================================
# In a true production environment, SECRET_KEY should be moved to your .env file!
# For now, we will define it here to get the system running.
SECRET_KEY = "super_secret_billing_platform_key_change_me_later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Tell passlib to use the bcrypt algorithm for hashing passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# This tells FastAPI to extract the token from the "Authorization" header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login") 


# ==========================================
# 2. PASSWORD HASHING & VERIFICATION
# ==========================================
def get_password_hash(password: str) -> str:
    """Takes a plain text password and returns a securely hashed version."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compares a typed password against the hashed version in the database."""
    return pwd_context.verify(plain_password, hashed_password)


# ==========================================
# 3. JWT TOKEN GENERATION
# ==========================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a secure JSON Web Token for user sessions."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
        
    to_encode.update({"exp": expire})
    
    # Sign the token using our secret key and the HS256 algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ==========================================
# 4. FASTAPI DEPENDENCIES (GATEKEEPERS)
# ==========================================
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependency that intercepts the request, reads the JWT token, 
    and fetches the matching user from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the token using your secret key
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # We assume the user's email was stored in the "sub" (subject) field of the token
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception

    # Find the user in the database
    user = db.query(Customer).filter(Customer.email == email).first()
    if user is None:
        raise credentials_exception
        
    return user

def get_admin_user(current_user: Customer = Depends(get_current_user)):
    """
    Dependency to check if the currently authenticated user is an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    return current_user