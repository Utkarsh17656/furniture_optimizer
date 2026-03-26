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
            meta = p.get('metadata', {})
            shape = meta.get('shape', 'RECT').upper()
            w = p.get('width', 0)
            h = p.get('height', 0)
            
            # Auto-infer width and height from metadata if omitted
            if shape == 'CIRCLE':
                if 'radius' in meta and not w:
                    w = h = float(meta['radius']) * 2
                elif 'diameter' in meta and not w:
                    w = h = float(meta['diameter'])
            elif shape in ['TRIANGLE', 'RIGHT_TRIANGLE', 'ISOSCELES_TRIANGLE', 'SCALENE_TRIANGLE']:
                b = meta.get('breadth', meta.get('base'))
                if b is not None and not w:
                    w = float(b)
                if 'height' in meta and not h:
                    h = float(meta['height'])
            elif shape == 'SEMI_CIRCLE':
                if 'diameter' in meta and not w:
                    w = float(meta['diameter'])
                    h = w / 2
                elif 'radius' in meta and not w:
                    w = float(meta['radius']) * 2
                    h = float(meta['radius'])
            elif shape == 'QUARTER_CIRCLE':
                if 'radius' in meta and not w:
                    w = h = float(meta['radius'])
                    
            parts.append(Part(
                id=p.get('id', 'P1'),
                width=float(w),
                height=float(h),
                name=p.get('name', ''),
                metadata=meta
            ))
            
        constraints_data = job_data.get('constraints')
        if constraints_data:
            file_constraints = ManufacturingConstraints(
                kerf=float(constraints_data.get('kerf', 4.0)),
                margin=float(constraints_data.get('margin', 10.0)),
                allow_rotation=bool(constraints_data.get('allow_rotation', True)),
                cost_per_sheet=cost_per_sheet,
                min_reusable_area=float(constraints_data.get('min_reusable_area', 46450.0)),
                min_reusable_dim=float(constraints_data.get('min_reusable_dim', 100.0))
            )

    elif 'job_file' in data:
        # Legacy JSON file approach
        job_filename = data.get('job_file')
        input_path = os.path.join(DATA_DIR, job_filename)
        sheet, parts, file_constraints = load_data(input_path)
        
        # Merge global constraints if provided in the root payload
        if file_constraints:
            # Smart Merge: If request sends UI defaults, preserve file-specific constraints
            req_kerf = float(data.get('kerf', 4.0))
            req_margin = float(data.get('margin', 10.0))
            req_area = float(data.get('min_reusable_area', 46450.0))
            req_dim = float(data.get('min_reusable_dim', 100.0))

            # UI defaults (approx)
            UI_DEF_AREA = 46451.5  # 0.5 * 92903
            UI_DEF_AREA_ALT = 46450.0
            UI_DEF_MARGIN = 10.0
            UI_DEF_KERF = 4.0
            UI_DEF_DIM = 100.0

            final_kerf = req_kerf if req_kerf != UI_DEF_KERF else file_constraints.kerf
            final_margin = req_margin if req_margin != UI_DEF_MARGIN else file_constraints.margin
            
            # Allow approx match for area
            is_default_area = abs(req_area - UI_DEF_AREA) < 1.0 or abs(req_area - UI_DEF_AREA_ALT) < 1.0
            final_area = req_area if not is_default_area else file_constraints.min_reusable_area
            
            final_dim = req_dim if req_dim != UI_DEF_DIM else file_constraints.min_reusable_dim

            file_constraints = ManufacturingConstraints(
                kerf=final_kerf,
                margin=final_margin,
                allow_rotation=file_constraints.allow_rotation,
                cost_per_sheet=cost_per_sheet,
                min_reusable_area=final_area,
                min_reusable_dim=final_dim
            )
        else:
            file_constraints = ManufacturingConstraints(
                kerf=float(data.get('kerf', 4.0)), 
                margin=float(data.get('margin', 10.0)), 
                allow_rotation=True, 
                cost_per_sheet=cost_per_sheet,
                min_reusable_area=float(data.get('min_reusable_area', 46450.0)),
                min_reusable_dim=float(data.get('min_reusable_dim', 100.0))
            )
    
    else:
        return jsonify({"error": "No job data or job file provided"}), 400

    if not sheet or not parts:
        return jsonify({"error": "Failed to load job"}), 400

    constraints = file_constraints if file_constraints else ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True)

    import uuid
    # --- Reusable Scrap Processing ---
    inventory_csv_path = os.path.join(DATA_DIR, 'reusable_inventory.csv')
    reusable_scraps = []
    
    # 1. Load existing reusable inventory
    if os.path.exists(inventory_csv_path):
        with open(inventory_csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    reusable_scraps.append({
                        "id": row.get("id"),
                        "type": row.get("type", "SCRAP"),
                        "width": float(row.get("width", 0)),
                        "height": float(row.get("height", 0)),
                        "area": float(row.get("area", 0)),
                        "sheet_id": row.get("sheet_id", ""),
                        "source_job": row.get("job_name") or row.get("source_job"),
                        "timestamp": row.get("timestamp"),
                        "used": False
                    })
                except Exception:
                    pass

    # 2. Try to fulfill parts from scrap (greedy, no rotation)
    parts_fulfilled_from_scrap = 0
    remaining_parts = []
    for p in parts:
        matched = False
        for s in reusable_scraps:
            if not s["used"] and s["width"] >= p.width and s["height"] >= p.height:
                s["used"] = True
                matched = True
                parts_fulfilled_from_scrap += 1
                break
        if not matched:
            remaining_parts.append(p)
            
    # 3. Write back unused scraps
    with open(inventory_csv_path, 'w', newline='') as f:
        fieldnames = ['id', 'type', 'width', 'height', 'area', 'sheet_id', 'job_name', 'timestamp']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in reusable_scraps:
            if not s["used"]:
                writer.writerow({
                    "id": s["id"],
                    "type": s["type"],
                    "width": s["width"],
                    "height": s["height"],
                    "area": s["area"],
                    "sheet_id": s["sheet_id"],
                    "job_name": s["source_job"],
                    "timestamp": s["timestamp"]
                })
                
    # Update parts list for engine
    parts = remaining_parts
    
    # If all parts were fulfilled by scrap, we can skip engine execution
    if not parts:
        return jsonify({
            "engine": "Scrap Reuse",
            "metrics": {
                "sheets": 0, "efficiency": 100.0, "wastage": 0.0,
                "waste": 0.0, "reusable_waste": 0.0, "scrap_waste": 0.0,
                "runtime": 0.0, "material_cost": 0.0, "waste_cost": 0.0,
                "reusable_waste_cost": 0.0, "scrap_waste_cost": 0.0,
                "baseline_savings": 0.0
            },
            "parts_fulfilled_count": parts_fulfilled_from_scrap,
            "candidates_data": [],
            "waste_details": [],
            "viz_url": ""
        })

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
            fieldnames = ['job_file', 'sheet_number', 'sheet_id', 'waste_area', 'reusable_waste_area', 'scrap_waste_area', 'waste_percentage', 'material_cost', 'waste_cost', 'reusable_waste_cost', 'scrap_waste_cost', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_has_content:
                writer.writeheader()
                
            for i, res_sheet in enumerate(result.sheets):
                sheet_area = res_sheet.sheet.width * res_sheet.sheet.height
                waste_percent = (res_sheet.waste_area / sheet_area * 100) if sheet_area > 0 else 0
                mat_cost = constraints.cost_per_sheet
                waste_cost_val = (res_sheet.waste_area / sheet_area * mat_cost) if sheet_area > 0 else 0
                reusable_waste_cost_val = (res_sheet.reusable_waste_area / sheet_area * mat_cost) if sheet_area > 0 else 0
                scrap_waste_cost_val = (res_sheet.scrap_waste_area / sheet_area * mat_cost) if sheet_area > 0 else 0

                row = {
                    "job_file": job_filename,
                    "sheet_number": i + 1,
                    "sheet_id": res_sheet.sheet.id,
                    "waste_area": round(res_sheet.waste_area, 2),
                    "reusable_waste_area": round(res_sheet.reusable_waste_area, 2),
                    "scrap_waste_area": round(res_sheet.scrap_waste_area, 2),
                    "waste_percentage": round(waste_percent, 2),
                    "material_cost": round(mat_cost, 2),
                    "waste_cost": round(waste_cost_val, 2),
                    "reusable_waste_cost": round(reusable_waste_cost_val, 2),
                    "scrap_waste_cost": round(scrap_waste_cost_val, 2),
                    "timestamp": timestamp_str
                }
                writer.writerow(row)
                waste_details.append(row)
        
        base_job_name = job_filename.replace('.json', '') if job_filename != 'Manual Entry' else 'ManualEntry'
        base_job_name = base_job_name.replace(' ', '')
        
        # Save newly generated reusable scraps & inject IDs BEFORE visualization
        with open(inventory_csv_path, 'a', newline='') as f:
            fieldnames = ['id', 'type', 'width', 'height', 'area', 'sheet_id', 'job_name', 'timestamp']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            scrap_index = 1
            for s in result.sheets:
                for scrap in s.reusable_scraps:
                    scrap_id = f"{base_job_name}_SCRAP_{scrap_index}"
                    scrap["label_id"] = scrap_id
                    writer.writerow({
                        "id": scrap_id,
                        "type": scrap.get('type', 'SCRAP'),
                        "width": round(scrap['width'], 2),
                        "height": round(scrap['height'], 2),
                        "area": round(scrap['area'], 2),
                        "sheet_id": s.sheet.id,
                        "job_name": base_job_name,
                        "timestamp": timestamp_str
                    })
                    scrap_index += 1

        show_scrap_labels = data.get('showScrapLabels', True)
        
        # Save visualization for frontend
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        viz_filename = f"viz_{timestamp}.png"
        viz_path = os.path.join(OUTPUT_DIR, viz_filename)
        
        # Use Visualizer
        print("Starting visualization generation...")
        from src.utils.visualizer import Visualizer
        viz = Visualizer()
        viz.plot_result(result, constraints, save_path=viz_path, show_scrap_labels=show_scrap_labels)
        print("Visualization generated.")
        
        # Generate Label CSV
        labels_csv_path = os.path.join(DATA_DIR, 'labels.csv')
        
        with open(labels_csv_path, 'w', newline='') as f:
            fieldnames = ['id', 'part_name', 'width', 'height', 'sheet_id', 'job_name']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            part_index = 1
            for res_sheet in result.sheets:
                for placed_part in res_sheet.placed_parts:
                    orig_part = placed_part.part
                    metadata = getattr(orig_part, 'metadata', {})
                    shape_type = metadata.get('shape', 'RECT')
                    
                    label_id = f"{shape_type}_{base_job_name}_{part_index}"
                    part_name = orig_part.name if orig_part.name else f"Part_{part_index}"
                    
                    if shape_type == 'CIRCLE':
                        r = metadata.get('radius', metadata.get('diameter', orig_part.width) / 2)
                        dim_text = f"R{int(r)}"
                    elif shape_type == 'TRIANGLE':
                        b = metadata.get('breadth', metadata.get('base', orig_part.width))
                        dim_text = f"{int(b)}x{int(orig_part.height)}"
                    elif shape_type == 'SEMI_CIRCLE':
                        d = metadata.get('diameter', metadata.get('radius', orig_part.width / 2) * 2)
                        dim_text = f"Ø{int(d)}"
                    elif shape_type == 'QUARTER_CIRCLE':
                        dim_text = f"R{int(metadata.get('radius', orig_part.width))}"
                    else:
                        dim_text = f"{int(orig_part.width)}x{int(orig_part.height)}"

                    writer.writerow({
                        "id": label_id,
                        "part_name": f"{part_name} ({dim_text})",
                        "width": orig_part.width,
                        "height": orig_part.height,
                        "sheet_id": res_sheet.sheet.id,
                        "job_name": job_filename
                    })
                    part_index += 1
        
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
                "reusable_waste": round(result.total_reusable_waste_area, 2),
                "scrap_waste": round(result.total_scrap_waste_area, 2),
                "runtime": round(result.runtime_seconds, 4),
                "material_cost": round(total_material_cost, 2),
                "waste_cost": round(waste_cost, 2),
                "reusable_waste_cost": sum(round((s.reusable_waste_area / (s.sheet.width * s.sheet.height) * constraints.cost_per_sheet) if (s.sheet.width * s.sheet.height)>0 else 0, 2) for s in result.sheets),
                "scrap_waste_cost": sum(round((s.scrap_waste_area / (s.sheet.width * s.sheet.height) * constraints.cost_per_sheet) if (s.sheet.width * s.sheet.height)>0 else 0, 2) for s in result.sheets),
                "baseline_savings": round(getattr(result, 'baseline_savings', 0.0), 2)
            },
            "candidates_data": getattr(result, 'candidates_data', []),
            "waste_details": waste_details,
            "viz_url": f"/output/{viz_filename}",
            "parts_fulfilled_count": parts_fulfilled_from_scrap
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
    def sfloat(val):
        try:
            return float(val) if val else 0.0
        except (ValueError, TypeError):
            return 0.0

    total_sheets = len(rows)
    total_waste_area = sum(sfloat(r.get('waste_area')) for r in rows)
    total_reusable_area = sum(sfloat(r.get('reusable_waste_area')) for r in rows)
    total_scrap_area = sum(sfloat(r.get('scrap_waste_area')) for r in rows)
    total_material_cost = sum(sfloat(r.get('material_cost')) for r in rows)
    total_waste_cost = sum(sfloat(r.get('waste_cost')) for r in rows)
    total_reusable_cost = sum(sfloat(r.get('reusable_waste_cost')) for r in rows)
    total_scrap_cost = sum(sfloat(r.get('scrap_waste_cost')) for r in rows)
    
    # Simple average of the percentages for "average waste %"
    avg_waste_percent = sum(sfloat(r.get('waste_percentage')) for r in rows) / total_sheets if total_sheets > 0 else 0

    summary_row = {
        "job_file": "TOTAL",
        "sheet_number": "-",
        "sheet_id": str(total_sheets),
        "waste_area": round(total_waste_area, 2),
        "reusable_waste_area": round(total_reusable_area, 2),
        "scrap_waste_area": round(total_scrap_area, 2),
        "waste_percentage": round(avg_waste_percent, 2),
        "material_cost": round(total_material_cost, 2),
        "waste_cost": round(total_waste_cost, 2),
        "reusable_waste_cost": round(total_reusable_cost, 2),
        "scrap_waste_cost": round(total_scrap_cost, 2),
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

@app.route('/api/download_labels', methods=['GET'])
def download_labels():
    """Allows downloading the labels CSV file."""
    labels_path = os.path.join(DATA_DIR, 'labels.csv')
    if not os.path.exists(labels_path):
        return jsonify({"error": "Labels file not found"}), 404
        
    return send_file(labels_path, as_attachment=True, download_name='labels.csv')

if __name__ == '__main__':
    app.run(debug=True, port=5000)