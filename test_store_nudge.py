print("Script started")
import requests
from datetime import datetime

# URLs
url_store = "http://localhost:8000/memory/store/1"
url_search = "http://localhost:8000/memory/search/1"

# Payload to store a new memory
payload_store = {
    "content": "I spent $500 on clothes last night after a stressful day.",
    "timestamp": datetime.now().isoformat()
}

# Payload to search memory
payload_search = {
    "query": "regret spending too much money"
}

# Store the memory
print("▶ Storing memory...")
response_store = requests.post(url_store, json=payload_store)
print("Store response status code:", response_store.status_code)
print("Store response body:", response_store.json())

# Search the memory
print("\n▶ Searching memory...")
response_search = requests.post(url_search, json=payload_search)
print("Search response status code:", response_search.status_code)
print("Search results:")
print(response_search.json())
