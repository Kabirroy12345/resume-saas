import requests

data = {
    "resume": "Resume with Emojis 🚀 and • bullets and — em dashes.",
    "jd": "JD with weird chars: “quotes” and ‘single quotes’.",
    "skills": ["python", "aws", "c++", "c#"]
}

print("Sending request with Special Chars...")
try:
    res = requests.post("http://127.0.0.1:8000/score-report", json=data)
    print(f"Status Code: {res.status_code}")
    
    if res.status_code != 200:
        print("Failed!")
        print(res.text)
    else:
        print("Success! PDF generated.")
        
except Exception as e:
    print(f"Request failed: {e}")
