
import os
import sys
import json

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.main import load_data
from src.engines.maxrects_engine import MaxRectsEngine
from src.engines.shelf_engine import ShelfNestingEngine
from src.models.models import ManufacturingConstraints

def check_overlap(parts):
    overlaps = []
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            p1 = parts[i]
            p2 = parts[j]
            # Bounding box check
            if not (p1.x + p1.width <= p2.x or
                    p2.x + p2.width <= p1.x or
                    p1.y + p1.height <= p2.y or
                    p2.y + p2.height <= p1.y):
                overlaps.append((p1.part.id, p2.part.id, p1.x, p1.y, p2.x, p2.y))
    return overlaps

input_path = 'data/complex_shapes_test.json'
sheet, parts, constraints = load_data(input_path)
if not constraints:
    constraints = ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True)

for name, engine in [("MaxRects", MaxRectsEngine()), ("Shelf", ShelfNestingEngine())]:
    print(f"\n--- Testing {name} ---")
    result = engine.optimize(sheet, parts, constraints)
    for i, s in enumerate(result.sheets):
        overlaps = check_overlap(s.placed_parts)
        if overlaps:
            print(f"Sheet {i+1} has {len(overlaps)} overlaps!")
            for o in overlaps:
                print(f"  Overlap: {o[0]} and {o[1]} at ({o[2]}, {o[3]}) and ({o[4]}, {o[5]})")
        else:
            print(f"Sheet {i+1} is overlap-free.")
