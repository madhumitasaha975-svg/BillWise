from app.database.connection import engine
from app.models.core import Base
from sqlalchemy import text

def update_database_schema():
    print("=== UPDATING POSTGRESQL SCHEMA ===")
    
    # 1. This safely creates any completely NEW tables (like your 'plans' table)
    Base.metadata.create_all(bind=engine)
    print("✅ New tables checked/created (Plans table).")

    # 2. This forces PostgreSQL to add the missing column to the existing table
    with engine.connect() as conn:
        try:
            # We use raw SQL to alter the existing table
            conn.execute(text("ALTER TABLE customers ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("✅ Successfully added 'is_admin' column to existing customers table.")
        except Exception as e:
            # If the column already exists, it will throw a minor error we can ignore
            print(f"⚠️ Note on 'is_admin' column: {e}")

    print("==================================")

if __name__ == "__main__":
    update_database_schema()