from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os
from dotenv import load_dotenv

load_dotenv()

# Connection string to your PostgreSQL database
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:Deepa1234$@localhost/resume_saas_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
def init_db():
    print("   -> Calling Base.metadata.create_all...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   -> Base.metadata.create_all done.")
    except Exception as e:
        print(f"   -> ERROR in init_db: {e}")
        raise e

# Get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()