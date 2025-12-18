import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001"

def test_home():
    try:
        print("Testing home endpoint...")
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"Home Status: {response.status_code}")
        print(f"Home Response: {response.json()}")
        return True
    except Exception as e:
        print(f"Home test failed: {e}")
        return False

def test_score():
    try:
        print("\nTesting score endpoint (triggering model load)...")
        data = {
            "resume": "Python developer with experience in FastAPI and machine learning.",
            "jd": "Looking for a Python engineer with ML skills.",
            "skills": ["python", "machine learning"]
        }
        start = time.time()
        response = requests.post(f"{BASE_URL}/score", json=data, timeout=30)
        duration = time.time() - start
        
        print(f"Score Status: {response.status_code}")
        print(f"Score Response keys: {list(response.json().keys())}")
        print(f"Duration: {duration:.2f}s")
        return True
    except Exception as e:
        print(f"Score test failed: {e}")
        return False

if __name__ == "__main__":
    if test_home():
        test_score()
