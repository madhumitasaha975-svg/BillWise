from app.database.connection import engine, Base
import app.models.core

print("Dropping old database tables...")
Base.metadata.drop_all(bind=engine)

print("Creating upgraded database tables...")
Base.metadata.create_all(bind=engine)

print("✅ Database successfully upgraded for Weeks 3-4!")