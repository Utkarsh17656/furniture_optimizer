import os
import random
from src.models.models import Part, Sheet, ManufacturingConstraints
from src.engines.maxrects_engine import MaxRectsEngine
from src.utils.visualizer import Visualizer

def generate_visual_proof():
    # Generate 100 parts
    parts = []
    for i in range(100):
        w = random.choice([400, 600, 800, 300, 564])
        h = random.choice([300, 400, 600, 100, 200])
        parts.append(Part(id=f"P{i+1}", width=w, height=h, name=f"Part {i+1}"))
    
    sheet = Sheet(id="PROOF-S1", width=2440, height=1220, material="Plywood 18mm")
    constraints = ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True)
    
    engine = MaxRectsEngine()
    result = engine.optimize(sheet, parts, constraints)
    
    visualizer = Visualizer()
    artifact_dir = r"C:\Users\Utkarsh Yadav\.gemini\antigravity\brain\540781f6-e5ad-47f1-b1cd-b95e67aa3ca7"
    save_path = os.path.join(artifact_dir, "maxrects_100part_proof.png")
    
    # We only visualize the first sheet to keep the image clear
    # Modifying the visualizer call slightly or just sending the whole result
    # The visualizer plots all sheets, which might be long. 
    # Let's just plot the first sheet for the "proof".
    print(f"Generating visual proof for 100 parts (Sheet 1)...")
    visualizer.plot_result(result, constraints, save_path=save_path)

if __name__ == "__main__":
    generate_visual_proof()
