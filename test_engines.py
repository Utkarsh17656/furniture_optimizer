import sys
import os
sys.path.append(os.getcwd())

from src.models.models import Part, Sheet, ManufacturingConstraints
from src.engines.intelligent_engine import IntelligentEngine

def test():
    sheet = Sheet(id="SHEET", width=2400, height=1200)
    
    parts = []
    
    # Side Panel 600x400x2
    for i in range(2):
        parts.append(Part(id=f"sp_{i}", width=600, height=400, metadata={"shape": "RECT"}))
    
    # SquarePart 500x500x5
    for i in range(5):
        parts.append(Part(id=f"sq_{i}", width=500, height=500, metadata={"shape": "RECT"}))
        
    # RectPart 800x400x10
    for i in range(10):
        parts.append(Part(id=f"rect_{i}", width=800, height=400, metadata={"shape": "RECT"}))
        
    # CirclePart 300x3 (using diameter as width/height)
    for i in range(3):
        # UI multiplies w * 2 for circle if input was radius. The user input 300 in UI.
        # Wait, if user typed 300, is it radius or diameter?
        # In script.js: `if (type === 'CIRCLE') { finalW = w * 2; finalH = w * 2; metadata.radius = w; }`
        # So width = 600, height = 600
        parts.append(Part(id=f"circ_{i}", width=600, height=600, metadata={"shape": "CIRCLE", "radius": 300}))
        
    # TriPart 400x600x2
    for i in range(2):
        # Type is probably RIGHT_TRIANGLE
        parts.append(Part(id=f"tri_{i}", width=400, height=600, metadata={"shape": "RIGHT_TRIANGLE"}))
        
    constraints = ManufacturingConstraints(kerf=4, margin=10, allow_rotation=True)
    
    engine = IntelligentEngine()
    result = engine.optimize(sheet, parts, constraints)
    
    print("Selected Engine:", engine.name)
    print("Candidates:")
    for c in result.candidates_data:
        print(f"  {c['algorithm']}: Sheets={c['sheets']}, eff={c['utilization']}% score={c['score']}")

if __name__ == "__main__":
    test()
