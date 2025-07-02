import requests

url = "http://127.0.0.1:8000/users/"

data = {
    "name": "Test User",
    "email": "testuser@example.com",
    "plan": "free"  # Added plan field
}

response = requests.post(url, json=data)

if response.status_code == 200:
    print("✅ User added:")
    print(response.json())
else:
    print(f"❌ Failed to add user. Status {response.status_code}: {response.text}")
