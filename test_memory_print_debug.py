import requests
import json

url = "http://localhost:8000/memory/search/1"

payload = {
    "query": "regret spending too much money"
}

try:
    response = requests.post(url, json=payload)
    print("\n--- RESPONSE STATUS ---")
    print(f"Status code: {response.status_code}")

    print("\n--- RAW TEXT ---")
    print(response.text)

    print("\n--- JSON (if parsable) ---")
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError:
        print("❌ Response is not valid JSON.")

except Exception as e:
    print("\n❌ Request failed:", str(e))
