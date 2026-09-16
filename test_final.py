import urllib.request
import json

req = urllib.request.Request("http://localhost:8015/health")
with urllib.request.urlopen(req) as response:
    print(json.loads(response.read().decode('utf-8')))