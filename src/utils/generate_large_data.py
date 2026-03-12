import json
import random

def generate_large_dataset(num_parts=60):
    sheet = {
        "id": "PROD-S1",
        "width": 2440,
        "height": 1220,
        "material": "Plywood 18mm"
    }
    
    parts = []
    # Mix of large, medium, and small parts
    
    # Large parts (e.g., side panels, tops)
    for i in range(1, 11):
        parts.append({
            "id": f"L-{i}",
            "width": random.randint(1200, 1800),
            "height": random.randint(400, 800),
            "name": f"Large Panel {i}"
        })
    
    # Medium parts (e.g., shelves, doors)
    for i in range(1, 26):
        parts.append({
            "id": f"M-{i}",
            "width": random.randint(400, 800),
            "height": random.randint(300, 600),
            "name": f"Medium Part {i}"
        })
        
    # Small parts (e.g., rails, stretchers, small shelves)
    for i in range(1, num_parts - 35 + 1):
        parts.append({
            "id": f"S-{i}",
            "width": random.randint(100, 600),
            "height": random.randint(50, 200),
            "name": f"Small Rail {i}"
        })
        
    dataset = {
        "sheet": sheet,
        "parts": parts
    }
    
    with open('data/large_production_dataset.json', 'w') as f:
        json.dump(dataset, f, indent=4)
    print(f"Generated large dataset with {len(parts)} parts.")

if __name__ == "__main__":
    generate_large_dataset()
