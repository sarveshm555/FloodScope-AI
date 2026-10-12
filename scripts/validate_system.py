import subprocess
import time
import sys
import urllib.request
import json

def validate_live_backend():
    print("Launching Uvicorn backend process...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    try:
        # Wait for server to bind
        time.sleep(2.5)
        url = "http://127.0.0.1:8000/api/health"
        print(f"Sending GET request to {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "System-Validator/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            status_code = resp.status
            body = json.loads(resp.read().decode())
            print(f"HTTP Status: {status_code}")
            print("Response Body:")
            print(json.dumps(body, indent=2))
            assert status_code == 200
            assert body["application_name"] == "FloodScope AI"
            assert body["status"] == "operational"
            print("LIVE VALIDATION PASSED!")
    finally:
        print("Terminating Uvicorn process...")
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == "__main__":
    validate_live_backend()
