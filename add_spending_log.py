import requests

url = "http://127.0.0.1:8000/spending/"

data = {
    "user_id": 1,
    "item_name": "Gucci Wallet",
    "amount": 450.00,
    "decision": "approved",
    "category": "Accessories",  # Added category field
    "comment": "Luxury purchase, justified"
}

response = requests.post(url, json=data)

if response.status_code == 200:
    print("✅ Spending log added:")
    print(response.json())
else:
    print(f"❌ Failed to add spending log. Status {response.status_code}: {response.text}")
