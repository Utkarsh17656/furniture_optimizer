import json
import random
import os

random.seed(42) # For reproducibility

data = {
    "sheet": {
        "id": "SHEET-STRESS",
        "width": 2440,
        "height": 1220,
        "material": "Plywood 18mm"
    },
    "constraints": {
        "kerf": 4.0,
        "margin": 10.0,
        "allow_rotation": True,
        "min_reusable_area": 46450.0,
        "min_reusable_dim": 100.0,
        "cost_per_sheet": 3000
    },
    "parts": []
}

part_id = 1

def add_part(name, shape, w, h, meta_params, qty=1):
    global part_id
    for _ in range(qty):
        metadata = {"shape": shape}
        metadata.update(meta_params)
        data["parts"].append({
            "id": f"P{part_id:03d}",
            "name": name,
            "width": w,
            "height": h,
            "metadata": metadata
        })
        part_id += 1

# 1. Large Rects (Conflicting with each other)
add_part("Large_Panel_1", "RECT", 1400, 800, {}, 2)
add_part("Large_Panel_2", "RECT", 1200, 1000, {}, 2)

# 2. Long Thin Strips (High aspect ratio)
add_part("Long_Strip_1", "RECT", 2200, 100, {}, 4)
add_part("Long_Strip_2", "RECT", 1800, 50, {}, 4)
add_part("Long_Strip_3", "RECT", 2400, 75, {}, 2)

# 3. Medium Rects
add_part("Medium_Panel", "RECT", 600, 400, {}, 5)
add_part("Square_Panel", "RECT", 500, 500, {}, 3)

# 4. Small Rects (Fillers)
add_part("Small_Filler", "RECT", 150, 100, {}, 8)
add_part("Tiny_Filler", "RECT", 80, 80, {}, 5)

# 5. Circles
for i in range(5):
    dia = random.choice([150, 250, 400, 600, 800])
    add_part(f"Circle_{dia}", "CIRCLE", dia, dia, {"diameter": dia}, 1)

# 6. Triangles
for i in range(5):
    b = random.choice([200, 400, 600])
    h = random.choice([150, 300, 500])
    add_part(f"Tri_{b}x{h}", "TRIANGLE", b, h, {"base": b, "height": h}, 1)

# 7. Semi-Circles
for i in range(4):
    dia = random.choice([300, 500, 700])
    add_part(f"Semi_Circ_{dia}", "SEMI_CIRCLE", dia, dia/2, {"diameter": dia}, 1)

# 8. Quarter-Circles
for i in range(4):
    r = random.choice([200, 400, 600])
    add_part(f"Qtr_Circ_{r}", "QUARTER_CIRCLE", r, r, {"radius": r}, 1)

out_path = os.path.join("data", "stress_test_shapes.json")
with open(out_path, "w") as f:
    json.dump(data, f, indent=2)

print(f"Generated {len(data['parts'])} parts in {out_path}")
