import requests

url = "http://127.0.0.1:8000/auth/login"
headers = {
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "POST",
}

try:
    print(f"Sending OPTIONS to {url} with Origin: {headers['Origin']}")
    response = requests.options(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for k, v in response.headers.items():
        if "access-control" in k.lower():
            print(f"{k}: {v}")
            
    if response.status_code == 200 and "Access-Control-Allow-Origin" in response.headers:
        print("\n✅ POSITIVE: CORS preflight looks good.")
    else:
        print("\n❌ NEGATIVE: CORS preflight failed.")

except Exception as e:
    print(f"❌ Error: {e}")
