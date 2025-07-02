print("Script started")
import requests
from datetime import datetime
import json

url_store = "http://localhost:8000/memory/store/1"
url_search = "http://localhost:8000/memory/search/1"

payload_store = {
    "content": "User felt tempted to buy a new iPhone, AI advised waiting 24 hours.",
    "timestamp": datetime.now().isoformat()
}

payload_search = {
    "query": "tempted to buy an iPhone"
}

def safe_post(url, payload, label):
    try:
        response = requests.post(url, json=payload)
        print(f"{label} Response: {response.status_code}, {response.json()}")
    except Exception as e:
        print(f"{label} Exception: {e}")

safe_post(url_store, payload_store, "Store")
safe_post(url_search, payload_search, "Search")

# Additional script to store a regretful iPhone purchase memory
payload_regret = {
    "content": "Felt bad after buying an iPhone last year. Should’ve waited or skipped it.",
    "timestamp": datetime.now().isoformat()
}
safe_post(url_store, payload_regret, "Regret Memory Store")

# Nudge test after storing the regret memory
url_nudge = "http://localhost:8000/memory/nudge/1"
payload_nudge = {
    "spending_intent": "I want to buy a new iPhone"
}
safe_post(url_nudge, payload_nudge, "Nudge")

# Script to store 3–4 unique, regretful spending memories for user_id=1
memories = [
    {
        "content": "I bought a $1200 smartwatch on impulse and regretted it the next day.",
        "timestamp": datetime.now().isoformat()
    },
    {
        "content": "Spent $500 on designer shoes during a sale, but I never wore them.",
        "timestamp": datetime.now().isoformat()
    },
    {
        "content": "Booked a last-minute flight to Paris for a weekend getaway, but it drained my savings.",
        "timestamp": datetime.now().isoformat()
    },
    {
        "content": "Bought a new gaming console even though my old one was working fine. Felt guilty afterwards.",
        "timestamp": datetime.now().isoformat()
    }
]

for idx, memory in enumerate(memories, 1):
    try:
        response = requests.post(url_store, json=memory)
        print(f"Memory {idx} status code:", response.status_code)
        try:
            print(json.dumps(response.json(), indent=2))
        except Exception:
            print(response.text)
    except Exception as e:
        print(f"❌ Failed to store memory {idx}:", str(e))
