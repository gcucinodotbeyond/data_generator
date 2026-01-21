import urllib.request
import json

url = "http://localhost:11434/api/generate"
data = {
    "model": "gemma3:latest",
    "prompt": "Say 'hello'",
    "stream": False
}

try:
    print(f"Sending request to {url}...")
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print("Response received:")
        print(result.get("response"))
except Exception as e:
    print(f"Error: {e}")
