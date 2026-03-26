import requests
import time

engines = ['shelf', 'maxrects', 'intelligent']
payload = {
    'cost_per_sheet': 3000, 
    'job_file': 'stress_test_shapes.json', 
    'showScrapLabels': False
}

for e in engines:
    payload['engine'] = e
    print(f"--- Running {e.upper()} ---")
    resp = requests.post('http://localhost:5000/api/optimize', json=payload)
    data = resp.json()
    if 'metrics' in data:
        metrics = data['metrics']
        print(f"Parts Fulfilled: {data.get('parts_fulfilled_count')} / {data.get('total_parts', '53')}")
        print(f"Sheets Used: {metrics.get('sheets_used', 0)}")
        print(f"Efficiency: {metrics.get('efficiency', 0)}%")
        print(f"Total Cost: {metrics.get('total_cost', 0)}")
        print(f"Waste % : {metrics.get('waste_percentage', 0)}%")
    else:
        print(f"Error or unexpected output for {e}: {data.keys()}")
    time.sleep(1)
