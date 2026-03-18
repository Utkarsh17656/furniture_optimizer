import os
import argparse
import json
import csv
import sys
from datetime import datetime
from src.main import load_data
from src.engines.shelf_engine import ShelfNestingEngine
from src.engines.maxrects_engine import MaxRectsEngine
from src.engines.intelligent_engine import IntelligentEngine
from src.utils.metrics import MetricsCalculator
from src.utils.visualizer import Visualizer
from src.models.models import ManufacturingConstraints

def run_production_job(input_path: str, engine_name: str, output_dir: str):
    """Runs a single production job and exports results."""
    # 1. Load Data
    sheet, parts, constraints = load_data(input_path)
    if not sheet or not parts:
        print(f"Error: Could not load valid job from {input_path}")
        return None

    # Default constraints if not in file
    if not constraints:
        constraints = ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True)

    # 2. Select Engine
    if engine_name.lower() == 'intelligent':
        engine = IntelligentEngine()
    elif engine_name.lower() == 'maxrects':
        engine = MaxRectsEngine()
    else:
        engine = ShelfNestingEngine()

    print(f"\n>>> Processing Job: {os.path.basename(input_path)} using {engine.name}")
    
    # 3. Run Optimization
    result = engine.optimize(sheet, parts, constraints)
    
    # 4. Export Results
    job_name = os.path.splitext(os.path.basename(input_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_output_dir = os.path.join(output_dir, f"{job_name}_{timestamp}")
    os.makedirs(job_output_dir, exist_ok=True)

    # A. JSON Export
    json_path = os.path.join(job_output_dir, "report.json")
    # Small helper to make result serializable
    report_data = {
        "job": job_name,
        "engine": engine.name,
        "timestamp": timestamp,
        "metrics": {
            "sheets_used": len(result.sheets),
            "efficiency": result.overall_efficiency,
            "wastage": result.wastage_percentage,
            "waste_area": result.total_waste_area,
            "runtime": result.runtime_seconds
        },
        "sheets": []
    }
    for i, s in enumerate(result.sheets):
        report_data["sheets"].append({
            "index": i + 1,
            "efficiency": s.efficiency,
            "wastage": s.wastage_percentage,
            "placed_parts_count": len(s.placed_parts)
        })
    
    with open(json_path, 'w') as f:
        json.dump(report_data, f, indent=4)

    # B. CSV Summary
    csv_path = os.path.join(output_dir, "production_summary.csv")
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Job", "Engine", "Sheets", "Efficiency %", "Wastage %", "Waste Area", "Runtime"])
        writer.writerow([timestamp, job_name, engine.name, len(result.sheets), f"{result.overall_efficiency:.2f}", f"{result.wastage_percentage:.2f}", result.total_waste_area, f"{result.runtime_seconds:.4f}"])

    # C. PNG Export
    viz_path = os.path.join(job_output_dir, "layout.png")
    visualizer = Visualizer()
    visualizer.plot_result(result, constraints, save_path=viz_path)

    print(f"Optimization Complete. Results saved to: {job_output_dir}")
    return result

def main():
    parser = argparse.ArgumentParser(description="Furniture Optimizer: Production Workflow Tool")
    parser.add_argument("--input", required=True, help="Path to input JSON job file or directory")
    parser.add_argument("--engine", default="intelligent", choices=["shelf", "maxrects", "intelligent"], help="Nesting engine to use")
    parser.add_argument("--output", default="output", help="Directory for exported results")

    args = parser.parse_args()

    # Ensure project root is in path for imports if run from CLI
    sys.path.append(os.getcwd())

    input_path = args.input
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    if os.path.isdir(input_path):
        # Batch Processing
        print(f"Batch Processing Folder: {input_path}")
        files = [f for f in os.listdir(input_path) if f.endswith('.json')]
        if not files:
            print("No .json job files found in directory.")
            return
        
        for file in files:
            full_path = os.path.join(input_path, file)
            run_production_job(full_path, args.engine, output_dir)
    else:
        # Single Job
        run_production_job(input_path, args.engine, output_dir)

if __name__ == "__main__":
    main()
