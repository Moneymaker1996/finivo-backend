import requests
import json

url = "http://localhost:8000/memory/nudge/history/1"

try:
    response = requests.get(url)
    print("Status code:", response.status_code)
    print("Response body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)
    if response.status_code != 200:
        print("❌ Error: Server returned status", response.status_code)
except Exception as e:
    print("❌ Request failed:", str(e))
