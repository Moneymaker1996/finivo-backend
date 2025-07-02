import requests

url = "http://127.0.0.1:8000/chat"
data = {"message": "Hello, Finivo!"}
response = requests.post(url, json=data)
print("Status code:", response.status_code)
print("Raw text:", response.text)
try:
    print("JSON:", response.json())
except Exception as e:
    print("Error parsing JSON:", e)
