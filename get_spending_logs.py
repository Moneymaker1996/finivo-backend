import requests

# Replace with the correct user_id
user_id = 1

# FastAPI base URL
url = f"http://127.0.0.1:8000/spending/{user_id}"

# Send GET request
response = requests.get(url)

# Display the response
if response.status_code == 200:
    print("✅ Spending Logs Retrieved:")
    print(response.json())
elif response.status_code == 404:
    print("❌ No logs found for this user.")
else:
    print(f"⚠️ Error {response.status_code}: {response.text}")
