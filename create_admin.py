from app.database.connection import SessionLocal
from app.models.core import Customer
from app.core.security import get_password_hash

def create_master_admin():
    db = SessionLocal()
    
    # The dedicated Admin Credentials
    ADMIN_EMAIL = "harshdeep@admin.com"
    ADMIN_PASSWORD = "MasterAdmin2026!"
    
    # Check if admin already exists so we don't duplicate it
    existing_admin = db.query(Customer).filter(Customer.email == ADMIN_EMAIL).first()
    
    if existing_admin:
        print("Admin account already exists!")
        db.close()
        return

    # Create the admin user and explicitly set is_admin to True
    hashed_pwd = get_password_hash(ADMIN_PASSWORD)
    admin_user = Customer(
        email=ADMIN_EMAIL, 
        hashed_password=hashed_pwd, 
        is_admin=True  # <--- This is the magic key
    )
    
    db.add(admin_user)
    db.commit()
    print(f"Success! Master admin created.")
    print(f"Email: {ADMIN_EMAIL}")
    print(f"Password: {ADMIN_PASSWORD}")
    
    db.close()

if __name__ == "__main__":
    create_master_admin()