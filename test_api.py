import requests
import json

URL = "http://127.0.0.1:5000/api/optimize"

# Test 1: JSON File + Intelligent Engine + Cost
payload1 = {
    "engine": "intelligent",
    "job_file": "complex_savings_demo.json",
    "cost_per_sheet": 3500
}

print("Running Test 1: JSON File...")
res1 = requests.post(URL, json=payload1)
if res1.status_code == 200:
    data = res1.json()
    print("Test 1 SUCCESS!")
    print(json.dumps(data.get('metrics', {}), indent=2))
    print(f"Candidates generated: {len(data.get('candidates_data', []))}")
else:
    print(f"Test 1 FAILED! Status: {res1.status_code}, Msg: {res1.text}")

# Test 2: Manual Payload + MaxRects + Cost
payload2 = {
    "engine": "maxrects",
    "cost_per_sheet": 3000,
    "job_data": {
        "sheet": {"id": "MANUAL-S", "width": 2400, "height": 1200, "material": "TestMat"},
        "parts": [
            {"id": "P1", "name": "Part A", "width": 600, "height": 400},
            {"id": "P2", "name": "Part A", "width": 600, "height": 400},
            {"id": "P3", "name": "Part B", "width": 1200, "height": 600}
        ],
        "constraints": {
            "kerf": 5, "margin": 10, "allow_rotation": True, "cost_per_sheet": 3000
        }
    }
}

print("\nRunning Test 2: Manual Payload...")
res2 = requests.post(URL, json=payload2)
if res2.status_code == 200:
    data = res2.json()
    print("Test 2 SUCCESS!")
    print(json.dumps(data.get('metrics', {}), indent=2))
else:
    print(f"Test 2 FAILED! Status: {res2.status_code}, Msg: {res2.text}")
