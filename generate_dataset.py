import json
import random
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.models.models import Part, Sheet, ManufacturingConstraints
from src.engines.intelligent_engine import IntelligentEngine

def generate_parts():
    large_options = [(1800, 400), (1600, 500), (2000, 300), (1400, 600)]
    medium_options = [(800, 400), (700, 300), (600, 350), (500, 450)]
    small_options = [(200, 150), (150, 150), (100, 200), (120, 80)]
    extreme_options = [(2000, 100), (1800, 120), (1000, 200), (50, 50), (80, 60)]

    parts_data = []
    
    # Large
    large_total = random.randint(5, 8)
    for i in range(large_total):
        w, h = random.choice(large_options)
        qty = random.randint(1, 2)
        parts_data.append({"id": f"L{i}", "width": w, "height": h, "quantity": qty})
        
    # Medium
    med_total = random.randint(15, 25)
    for i in range(med_total):
        w, h = random.choice(medium_options)
        qty = random.randint(1, 2)
        parts_data.append({"id": f"M{i}", "width": w, "height": h, "quantity": qty})
        
    # Small
    small_total = random.randint(30, 50)
    for i in range(small_total):
        w, h = random.choice(small_options)
        qty = random.randint(1, 3)
        parts_data.append({"id": f"S{i}", "width": w, "height": h, "quantity": qty})
        
    # Extreme
    ext_total = random.randint(10, 20)
    for i in range(ext_total):
        w, h = random.choice(extreme_options)
        qty = random.randint(1, 3)
        parts_data.append({"id": f"E{i}", "width": w, "height": h, "quantity": qty})
        
    return parts_data

def build_parts(parts_data):
    parts = []
    for p in parts_data:
        qty = p.get('quantity', 1)
        for i in range(qty):
            parts.append(Part(
                id=f"{p['id']}_{i+1}" if qty > 1 else p['id'],
                width=float(p['width']),
                height=float(p['height']),
                name=p.get('id', '')
            ))
    return parts

sheet = Sheet(id="S1", width=2440, height=1220, material="Standard")
constraints = ManufacturingConstraints(kerf=4, margin=10, allow_rotation=True, cost_per_sheet=3500)
engine = IntelligentEngine()

found = False
for attempt in range(50):
    random.seed(attempt)
    parts_data = generate_parts()
    parts = build_parts(parts_data)
    
    try:
        result = engine.optimize(sheet, parts, constraints)
        if hasattr(result, 'baseline_savings') and result.baseline_savings > 0:
            print(f"FOUND ONE AT SEED {attempt}!")
            print(f"Savings: {result.baseline_savings}")
            print("Candidates:")
            for r in result.candidates_data:
                print(r)
            
            output_data = {
                "sheet": {
                    "width": 2440,
                    "height": 1220,
                    "kerf": 4,
                    "margin": 10
                },
                "parts": parts_data
            }
            with open("c:\\Users\\Utkarsh Yadav\\Desktop\\Furniture_Optimizer\\data\\complex_savings_demo.json", "w") as f:
                json.dump(output_data, f, indent=2)
            found = True
            break
    except Exception as e:
        print(f"Error on attempt {attempt}: {e}")

if not found:
    print("Could not find a case.")
