import json
import os
import sys
from typing import List, Optional

# Ensure project root is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.models import Part, Sheet, ManufacturingConstraints
from src.engines.shelf_engine import ShelfNestingEngine
from src.utils.metrics import MetricsCalculator
from src.utils.visualizer import Visualizer

def load_data(json_path: str) -> tuple[Optional[Sheet], List[Part], Optional[ManufacturingConstraints]]:
    """Loads sheet, parts, and optional constraints from a JSON file."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        sheet_data = data.get('sheet')
        if not sheet_data:
            return None, [], None
            
        sheet = Sheet(
            id=sheet_data.get('id', 'Sheet-1'),
            width=float(sheet_data['width']),
            height=float(sheet_data['height']),
            material=sheet_data.get('material', 'Standard')
        )
        parts = []
        for p in data.get('parts', []):
            qty = p.get('quantity', 1)
            for i in range(qty):
                parts.append(Part(
                    id=f"{p['id']}_{i+1}" if qty > 1 else p['id'],
                    width=float(p['width']),
                    height=float(p['height']),
                    name=p.get('name', '')
                ))
            
        constraints_data = data.get('constraints')
        constraints = None
        if constraints_data:
            constraints = ManufacturingConstraints(
                kerf=float(constraints_data.get('kerf', 0.0)),
                margin=float(constraints_data.get('margin', 0.0)),
                allow_rotation=bool(constraints_data.get('allow_rotation', True))
            )
            
        return sheet, parts, constraints
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, [], None

def main():
    print("=== Furniture Optimizer: Architecture Refinement & Visualization ===")
    
    # Configuration
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    input_path = os.path.join(data_dir, 'example_input.json')
    
    print(f"Loading data from {input_path}...")    # Load Data
    sheet, parts, file_constraints = load_data(input_path)
    if not sheet:
        print("Failed to load sheet data.")
        return
        
    print(f"Job loaded: {input_path}")
    # The original instruction had a typo 'int("Failed to load sheet data.")' here.
    # Assuming the intent was to remove the redundant print and return,
    # or that the previous `if not sheet:` block was sufficient.
    # Keeping the `print(f"Job loaded: {input_path}")` as it was explicitly added.

    print(f"Target Sheet: {sheet.id} ({sheet.width}x{sheet.height})")
    print(f"Parts requested: {len(parts)}")

    # Initialize Engine with Constraints
    # Prefer constraints from file, otherwise use defaults
    constraints = file_constraints if file_constraints else ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True)
    engine = ShelfNestingEngine()
    print(f"Executing: {engine.name} with Kerf={constraints.kerf}mm, Margin={constraints.margin}mm")
    
    # Run Optimization
    result = engine.optimize(sheet, parts, constraints)
    
    # Print Metrics Summary
    MetricsCalculator.print_summary(result)
    
    # Visualize Results
    visualizer = Visualizer()
    print("Generating visualization...")
    
    # Save a copy to artifacts for easier review
    artifact_dir = r"C:\Users\Utkarsh Yadav\.gemini\antigravity\brain\540781f6-e5ad-47f1-b1cd-b95e67aa3ca7"
    save_path = os.path.join(artifact_dir, "nesting_visualization.png")
    
    visualizer.plot_result(result, constraints, save_path=save_path)

if __name__ == "__main__":
    main()
