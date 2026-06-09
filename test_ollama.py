import requests

url = "http://localhost:11434/api/generate"

data = {
    "model": "llama3.2:3b",
    "prompt": "Say hello in one short sentence.",
    "stream": False
}

response = requests.post(url, json=data)
result = response.json()

print(result["response"])

