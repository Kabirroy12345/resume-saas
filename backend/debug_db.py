import sqlalchemy
from sqlalchemy import create_engine
import sys
import time

DATABASE_URL = "postgresql://postgres:Deepa1234$@localhost/resume_saas_db"

print(f"Testing direct connection to {DATABASE_URL}...")
engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 5})

try:
    start_time = time.time()
    with engine.connect() as conn:
        print(f"Successfully connected to 'resume_saas_db' in {time.time() - start_time:.2f}s")
        print("Executing simple SELECT 1...")
        result = conn.execute(sqlalchemy.text("SELECT 1"))
        print(f"Result: {result.fetchone()}")
        print("✅ PostgreSQL is fully functional.")
            
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    sys.exit(1)
