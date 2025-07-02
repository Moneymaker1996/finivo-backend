import requests

response = requests.post(
    "http://localhost:8000/memory/search/1",
    json={"query": "test"}
)

print("Status Code:", response.status_code)
print("Response:", response.json())
