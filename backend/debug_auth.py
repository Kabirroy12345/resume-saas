import os
from dotenv import load_dotenv
from jose import jwt
from datetime import datetime, timedelta

# Load env
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

print(f"SECRET_KEY present: {bool(SECRET_KEY)}")
print(f"ALGORITHM: {ALGORITHM}")

if not SECRET_KEY:
    print("CRITICAL: SECRET_KEY is missing!")
    # Generate a key for testing
    SECRET_KEY = "test_secret"

# Test Token Generation
data = {"sub": "test@test.com"}
expire = datetime.utcnow() + timedelta(minutes=30)
data.update({"exp": expire})

try:
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    print(f"Generated Token: {token[:20]}...")
except Exception as e:
    print(f"Generation Failed: {e}")
    exit(1)

# Test Verification
try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print(f"Decoded Payload: {payload}")
    print("Verification SUCCESS")
except Exception as e:
    print(f"Verification FAILED: {e}")
