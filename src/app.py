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
from src.engines.intelligent_engine import IntelligentEngine
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
    cost_per_sheet = float(data.get('cost_per_sheet', 0.0))
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
                kerf=float(constraints_data.get('kerf', 4.0)),
                margin=float(constraints_data.get('margin', 10.0)),
                allow_rotation=bool(constraints_data.get('allow_rotation', True)),
                cost_per_sheet=cost_per_sheet
            )

    elif 'job_file' in data:
        # Legacy JSON file approach
        job_filename = data.get('job_file')
        input_path = os.path.join(DATA_DIR, job_filename)
        sheet, parts, file_constraints = load_data(input_path)
        
        # Merge global cost if provided
        global_cost = float(data.get('cost_per_sheet', 0.0))
        if file_constraints:
            file_constraints = ManufacturingConstraints(
                kerf=file_constraints.kerf,
                margin=file_constraints.margin,
                allow_rotation=file_constraints.allow_rotation,
                cost_per_sheet=cost_per_sheet
            )
        else:
            file_constraints = ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True, cost_per_sheet=cost_per_sheet)
    
    else:
        return jsonify({"error": "No job data or job file provided"}), 400

    if not sheet or not parts:
        return jsonify({"error": "Failed to load job"}), 400

    constraints = file_constraints if file_constraints else ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True)

    try:
        if engine_name.lower() == 'intelligent':
            engine = IntelligentEngine()
        elif engine_name.lower() == 'shelf':
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
            fieldnames = ['job_file', 'sheet_number', 'sheet_id', 'waste_area', 'waste_percentage', 'material_cost', 'waste_cost', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_has_content:
                writer.writeheader()
                
            for i, res_sheet in enumerate(result.sheets):
                sheet_area = res_sheet.sheet.width * res_sheet.sheet.height
                waste_percent = (res_sheet.waste_area / sheet_area * 100) if sheet_area > 0 else 0
                mat_cost = constraints.cost_per_sheet
                waste_cost_val = (res_sheet.waste_area / sheet_area * mat_cost) if sheet_area > 0 else 0

                row = {
                    "job_file": job_filename,
                    "sheet_number": i + 1,
                    "sheet_id": res_sheet.sheet.id,
                    "waste_area": round(res_sheet.waste_area, 2),
                    "waste_percentage": round(waste_percent, 2),
                    "material_cost": round(mat_cost, 2),
                    "waste_cost": round(waste_cost_val, 2),
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
        
        # Calculate total cost if missing for base results
        total_material_cost, waste_cost = 0.0, 0.0
        if isinstance(engine, IntelligentEngine):
            from src.engines.intelligent_engine import Evaluator
            total_material_cost, waste_cost = Evaluator.calculate_cost(result, constraints.cost_per_sheet)
        else:
            total_material_cost = len(result.sheets) * constraints.cost_per_sheet
            for s in result.sheets:
                sheet_area = s.sheet.width * s.sheet.height
                if sheet_area > 0:
                    fraction_wasted = s.waste_area / sheet_area
                    waste_cost += fraction_wasted * constraints.cost_per_sheet

        return jsonify({
            "engine": engine.name,
            "metrics": {
                "sheets": len(result.sheets),
                "efficiency": round(result.overall_efficiency, 2),
                "wastage": round(result.wastage_percentage, 2),
                "waste": round(result.total_waste_area, 2),
                "runtime": round(result.runtime_seconds, 4),
                "material_cost": round(total_material_cost, 2),
                "waste_cost": round(waste_cost, 2),
                "baseline_savings": round(getattr(result, 'baseline_savings', 0.0), 2)
            },
            "candidates_data": getattr(result, 'candidates_data', []),
            "waste_details": waste_details,
            "viz_url": f"/output/{viz_filename}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/download_inventory', methods=['GET'])
def download_inventory():
    """Allows downloading the CSV inventory file with a summary row."""
    inventory_path = os.path.join(DATA_DIR, 'inventory.csv')
    if not os.path.exists(inventory_path):
        return jsonify({"error": "Inventory file not found"}), 404

    # Read existing data to calculate totals
    rows = []
    try:
        with open(inventory_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames
            for row in reader:
                rows.append(row)
    except Exception as e:
        return jsonify({"error": f"Failed to read inventory: {str(e)}"}), 500

    if not rows:
        return send_file(inventory_path, as_attachment=True, download_name='inventory.csv')

    # Calculate Totals
    total_sheets = len(rows)
    total_waste_area = sum(float(r['waste_area']) for r in rows)
    total_material_cost = sum(float(r['material_cost']) for r in rows)
    total_waste_cost = sum(float(r['waste_cost']) for r in rows)
    avg_waste_percent = (total_waste_area / (sum(float(r['waste_area']) / (float(r['waste_percentage']) / 100) if float(r['waste_percentage']) > 0 else 0 for r in rows) or 1)) * 100 
    
    # Wait, avg_waste_% calculation above is complex because we don't store total_sheet_area.
    # Actually, we can just average the waste_percentage column if we want "average waste per sheet".
    # Or we can sum total_waste_area and divide by sum of total_sheet_areas.
    # Since we don't have total_sheet_area in the CSV, I'll use the average of percentages or calculate it from waste_area / (waste_percent/100).
    
    # A cleaner way to get avg_waste_%:
    # total_sheet_area_sum = sum(float(r['waste_area']) / (float(r['waste_percentage']) / 100) for r in rows if float(r['waste_percentage']) > 0)
    # But some rows might have 0% waste.
    
    # Let's just use simple average of the percentages for "average waste %" as it's a common business metric.
    avg_waste_percent = sum(float(r['waste_percentage']) for r in rows) / total_sheets

    summary_row = {
        "job_file": "TOTAL",
        "sheet_number": "-",
        "sheet_id": str(total_sheets),
        "waste_area": round(total_waste_area, 2),
        "waste_percentage": round(avg_waste_percent, 2),
        "material_cost": round(total_material_cost, 2),
        "waste_cost": round(total_waste_cost, 2),
        "timestamp": "-"
    }

    # Create a temporary file or in-memory stream for the response
    import io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    writer.writerow(summary_row)
    
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    output.close()

    return send_file(
        mem,
        as_attachment=True,
        download_name='inventory_report.csv',
        mimetype='text/csv'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)