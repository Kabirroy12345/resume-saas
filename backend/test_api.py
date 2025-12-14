import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_auth_flow():
    # 1. Register
    reg_data = {
        "email": "integration_test@test.com",
        "username": "integration_test",
        "password": "password123"
    }
    print("--- Registering ---")
    res = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    if res.status_code == 400 and "already registered" in res.text:
        print("User already exists, proceeding to login...")
    elif res.status_code != 200:
        print(f"Register failed: {res.status_code} {res.text}")
        return
    else:
        print("Register success.")

    # 2. Login
    login_data = {
        "email": "integration_test@test.com",
        "password": "password123"
    }
    print("--- Logging in ---")
    res = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if res.status_code != 200:
        print(f"Login failed: {res.status_code} {res.text}")
        return
    
    token_data = res.json()
    token = token_data["access_token"]
    print(f"Got Token: {token[:10]}...")

    # 3. Access Protected Endpoint
    print("--- Accessing /auth/me ---")
    # Simulate what Frontend Sends: "Authorization": "Bearer <token>"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")

    if res.status_code == 200:
        print("SUCCESS: Auth flow is working!")
    else:
        print("FAILURE: Protected route failed.")

if __name__ == "__main__":
    try:
        test_auth_flow()
    except Exception as e:
        print(f"Test crashed: {e}")
