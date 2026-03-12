import os
import random
import time
from typing import List, Dict, Any
from src.models.models import Part, Sheet, ManufacturingConstraints
from src.engines.shelf_engine import ShelfNestingEngine
from src.engines.maxrects_engine import MaxRectsEngine
from src.main import load_data

def generate_random_parts(count: int) -> List[Part]:
    parts = []
    for i in range(count):
        # Mix of standard furniture sizes
        w = random.choice([400, 600, 800, 1200, 300, 564])
        h = random.choice([300, 400, 600, 100, 200, 500])
        parts.append(Part(id=f"P{i+1}", width=w, height=h, name=f"Part {i+1}"))
    return parts

def run_experiment():
    print("=== Furniture Optimizer: Scalability & Performance Analysis ===")
    
    # Standard Plywood Sheet
    sheet_template = Sheet(id="STD-S1", width=2440, height=1220, material="Plywood 18mm")
    
    # Constraints
    constraints = ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True)
    
    dataset_sizes = [20, 50, 100, 200]
    engines = [ShelfNestingEngine(), MaxRectsEngine()]
    
    # Results storage
    # { size: { engine_name: { 'sheets': X, 'utilization': Y, 'runtime': Z } } }
    perf_results = {}

    for size in dataset_sizes:
        print(f"\n--- Testing Dataset Size: {size} parts ---")
        perf_results[size] = {}
        parts = generate_random_parts(size)
        
        for engine in engines:
            # We run it 3 times to get a stable average runtime if we wanted, 
            # but for this benchmark a single clean run is usually enough.
            result = engine.optimize(sheet_template, parts, constraints)
            
            perf_results[size][engine.name] = {
                'sheets': len(result.sheets),
                'utilization': result.overall_efficiency,
                'runtime': result.runtime_seconds
            }
            print(f"[{engine.name}] Sheets: {len(result.sheets)}, Efficiency: {result.overall_efficiency:.2f}%, Time: {result.runtime_seconds:.4f}s")

    # Output Final Summary Table
    print("\n" + "="*95)
    print(f"{'Size':<6} | {'Algorithm':<20} | {'Sheets':<8} | {'Utilization':<12} | {'Runtime (s)':<12}")
    print("-" * 95)
    
    for size in dataset_sizes:
        for engine_name, data in perf_results[size].items():
            print(f"{size:<6} | {engine_name:<20} | {data['sheets']:<8} | {data['utilization']:>10.2f}% | {data['runtime']:>11.4f}s")
        print("-" * 95)
    print("="*95)

if __name__ == "__main__":
    run_experiment()
