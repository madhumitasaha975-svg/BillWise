from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

# --- NEW GOOGLE AUTH IMPORTS ---
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Import your database dependency and schemas
from app.database.connection import get_db
from app.schemas.customer import CustomerCreate, CustomerResponse
from app.core.security import get_password_hash, verify_password, create_access_token

# IMPORTANT: Adjust this import based on exactly where your Customer model is!
from app.models.core import Customer 

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# --- NEW SCHEMA FOR GOOGLE TOKEN ---
class GoogleToken(BaseModel):
    token: str

@router.post("/register", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: CustomerCreate, db: Session = Depends(get_db)):
    # 1. Check if the email already exists in the database
    existing_user = db.query(Customer).filter(Customer.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email is already registered"
        )
    
    # 2. Hash the password
    hashed_pwd = get_password_hash(user_data.password)
    
    # 3. Create the new customer and save to database
    new_user = Customer(email=user_data.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 4. Return the newly created user (password is safely hidden by the schema)
    return new_user

@router.post("/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Find the user by email (OAuth2PasswordRequestForm uses 'username' for the email field)
    user = db.query(Customer).filter(Customer.email == form_data.username).first()
    
    # 2. Verify the user exists and the password matches
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Generate the JWT Access Token
    access_token = create_access_token(data={"sub": user.email})
    
    # 4. Return the token to the frontend
    return {"access_token": access_token, "token_type": "bearer"}

# --- NEW GOOGLE AUTH ROUTE ---
@router.post("/google")
def google_auth(token_data: GoogleToken, db: Session = Depends(get_db)):
    try:
        # 1. Verify the token directly with Google's servers
        CLIENT_ID = "947976051057-ncvdo5vr5ov3uqm49vvbg3kk9oq16t4v.apps.googleusercontent.com"
        
        idinfo = id_token.verify_oauth2_token(
            token_data.token, 
            google_requests.Request(), 
            CLIENT_ID
        )
        
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="No email found in Google token")
        
        # 2. Check if this customer already exists in your PostgreSQL database
        user = db.query(Customer).filter(Customer.email == email).first()
        
        if not user:
            # 3. Create a new user if they don't exist
            # Generate a random dummy password for Google users
            dummy_password = str(uuid.uuid4())
            hashed_dummy = get_password_hash(dummy_password)
            
            user = Customer(
                email=email,
                hashed_password=hashed_dummy
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # 4. Generate YOUR app's JWT token
        access_token = create_access_token(data={"sub": user.email}) 
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except ValueError:
        # If the token is expired or fake, Google throws a ValueError
        raise HTTPException(status_code=401, detail="Invalid Google token")