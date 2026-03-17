from flask import Flask, request, jsonify, send_from_directory
import os
import json
import csv
from flask import send_file
from datetime import datetime
import base64
from src.main import load_data
from src.engines.shelf_engine import ShelfNestingEngine
from src.engines.maxrects_engine import MaxRectsEngine
from src.models.models import ManufacturingConstraints, Sheet, Part

app = Flask(__name__, static_folder='../static', static_url_path='')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'static', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Lists available job files in the data directory."""
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    return jsonify(files)

@app.route('/api/optimize', methods=['POST'])
def optimize():
    """Runs optimization on a selected job."""
    data = request.json
    engine_name = data.get('engine', 'maxrects')
    
    sheet = None
    parts = []
    file_constraints = None
    job_filename = ""

    if 'job_data' in data:
        # Manual entry / CSV upload approach
        job_data = data['job_data']
        job_filename = "Manual Entry"
        
        sheet_data = job_data.get('sheet', {})
        sheet = Sheet(
            id=sheet_data.get('id', 'SHEET-1'),
            width=float(sheet_data.get('width', 2400)),
            height=float(sheet_data.get('height', 1200)),
            material=sheet_data.get('material', 'Standard')
        )
        
        for p in job_data.get('parts', []):
            parts.append(Part(
                id=p.get('id', 'P1'),
                width=float(p.get('width', 0)),
                height=float(p.get('height', 0)),
                name=p.get('name', '')
            ))
            
        constraints_data = job_data.get('constraints')
        if constraints_data:
            file_constraints = ManufacturingConstraints(
                kerf=float(constraints_data.get('kerf', 0.0)),
                margin=float(constraints_data.get('margin', 0.0)),
                allow_rotation=bool(constraints_data.get('allow_rotation', True))
            )

    elif 'job_file' in data:
        # Legacy JSON file approach
        job_filename = data.get('job_file')
        input_path = os.path.join(DATA_DIR, job_filename)
        sheet, parts, file_constraints = load_data(input_path)
    
    else:
        return jsonify({"error": "No job data or job file provided"}), 400

    if not sheet or not parts:
        return jsonify({"error": "Failed to load job"}), 400

    constraints = file_constraints if file_constraints else ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True)

    try:
        if engine_name.lower() == 'shelf':
            engine = ShelfNestingEngine()
        else:
            engine = MaxRectsEngine()

        print(f"Starting optimization with {engine.name} on {len(parts)} parts...")
        result = engine.optimize(sheet, parts, constraints)
        print("Optimization complete.")
        
        # Save waste area to CSV inventory
        inventory_path = os.path.join(DATA_DIR, 'inventory.csv')
        file_has_content = os.path.exists(inventory_path) and os.path.getsize(inventory_path) > 0
        
        timestamp_str = datetime.now().isoformat()
        waste_details = []
        
        with open(inventory_path, 'a', newline='') as csvfile:
            fieldnames = ['job_file', 'algorithm', 'sheet_index', 'sheet_id', 'material', 'waste_area', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_has_content:
                writer.writeheader()
                
            for i, res_sheet in enumerate(result.sheets):
                if res_sheet.waste_area > 0:
                    row = {
                        "job_file": job_filename,
                        "algorithm": engine.name,
                        "sheet_index": i,
                        "sheet_id": res_sheet.sheet.id,
                        "material": res_sheet.sheet.material,
                        "waste_area": round(res_sheet.waste_area, 2),
                        "timestamp": timestamp_str
                    }
                    writer.writerow(row)
                    waste_details.append(row)
        
        # Save visualization for frontend
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        viz_filename = f"viz_{timestamp}.png"
        viz_path = os.path.join(OUTPUT_DIR, viz_filename)
        
        # Use Visualizer
        print("Starting visualization generation...")
        from src.utils.visualizer import Visualizer
        viz = Visualizer()
        viz.plot_result(result, constraints, save_path=viz_path)
        print("Visualization generated.")
        
        return jsonify({
            "engine": engine.name,
            "metrics": {
                "sheets": len(result.sheets),
                "efficiency": round(result.overall_efficiency, 2),
                "wastage": round(result.wastage_percentage, 2),
                "waste": round(result.total_waste_area, 2),
                "runtime": round(result.runtime_seconds, 4)
            },
            "waste_details": waste_details,
            "viz_url": f"/output/{viz_filename}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    timestamp_str = datetime.now().isoformat()
    waste_details = []
    
    with open(inventory_path, 'a', newline='') as csvfile:
        fieldnames = ['job_file', 'algorithm', 'sheet_index', 'sheet_id', 'material', 'waste_area', 'timestamp']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_has_content:
            writer.writeheader()
            
        for i, res_sheet in enumerate(result.sheets):
            if res_sheet.waste_area > 0:
                row = {
                    "job_file": job_filename,
                    "algorithm": engine.name,
                    "sheet_index": i,
                    "sheet_id": res_sheet.sheet.id,
                    "material": res_sheet.sheet.material,
                    "waste_area": round(res_sheet.waste_area, 2),
                    "timestamp": timestamp_str
                }
                writer.writerow(row)
                waste_details.append(row)
    
    # Save visualization for frontend
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    viz_filename = f"viz_{timestamp}.png"
    viz_path = os.path.join(OUTPUT_DIR, viz_filename)
    
    # Use Visualizer - need to make sure it closes the plot correctly
    from src.utils.visualizer import Visualizer
    viz = Visualizer()
    viz.plot_result(result, constraints, save_path=viz_path)
    
    return jsonify({
        "engine": engine.name,
        "metrics": {
            "sheets": len(result.sheets),
            "efficiency": round(result.overall_efficiency, 2),
            "wastage": round(result.wastage_percentage, 2),
            "waste": round(result.total_waste_area, 2),
            "runtime": round(result.runtime_seconds, 4)
        },
        "waste_details": waste_details,
        "viz_url": f"/output/{viz_filename}"
    })

@app.route('/api/download_inventory', methods=['GET'])
def download_inventory():
    """Allows downloading the CSV inventory file."""
    inventory_path = os.path.join(DATA_DIR, 'inventory.csv')
    if os.path.exists(inventory_path):
        return send_file(inventory_path, as_attachment=True, download_name='inventory.csv')
    else:
        return jsonify({"error": "Inventory file not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)