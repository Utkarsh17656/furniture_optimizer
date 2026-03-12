import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import load_data
from src.engines.shelf_engine import ShelfNestingEngine
from src.engines.maxrects_engine import MaxRectsEngine
from src.utils.metrics import MetricsCalculator
from src.utils.visualizer import Visualizer

from src.models.models import ManufacturingConstraints

import argparse

def compare_engines(job_filename: str = None):
    print("=== Furniture Optimizer: Benchmarking Framework ===")
    
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    
    if job_filename:
        input_path = os.path.join(data_dir, job_filename)
    else:
        input_path = os.path.join(data_dir, 'demo_job.json')
        if not os.path.exists(input_path):
            input_path = os.path.join(data_dir, 'example_input.json')
    
    sheet, parts, _ = load_data(input_path)
    if not sheet:
        print(f"Error: Could not load dataset at {input_path}")
        return

    # Define common constraints
    constraints = ManufacturingConstraints(
        kerf=4.0,       # 4mm saw blade
        margin=10.0,    # 10mm safety margin
        allow_rotation=True
    )

    print(f"Constraints: Kerf={constraints.kerf}mm, Margin={constraints.margin}mm, Rotation={'Allowed' if constraints.allow_rotation else 'Off'}")

    engines = [
        ShelfNestingEngine(),
        MaxRectsEngine()
    ]
    
    results = []

    for engine in engines:
        print(f"\nEvaluating: {engine.name}...")
        result = engine.optimize(sheet, parts, constraints)
        results.append((engine.name, result))
        MetricsCalculator.print_summary(result)

    print("\n" + "="*105)
    print(f"{'Algorithm':<20} | {'Sheets':<8} | {'Utilization':<12} | {'Wastage':<12} | {'Runtime (s)':<12}")
    print("-" * 105)
    
    for name, res in results:
        print(f"{name:<20} | {len(res.sheets):<8} | {res.overall_efficiency:>10.2f}% | {res.wastage_percentage:>10.2f}% | {res.runtime_seconds:>11.4f}s")
    print("="*105 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Filename of the job in data/ directory")
    args = parser.parse_args()
    compare_engines(args.input)
