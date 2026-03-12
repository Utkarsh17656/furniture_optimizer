from flask import Flask, request, jsonify, send_from_directory
import os
import json
from datetime import datetime
import base64
from src.main import load_data
from src.engines.shelf_engine import ShelfNestingEngine
from src.engines.maxrects_engine import MaxRectsEngine
from src.models.models import ManufacturingConstraints

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
    job_filename = data.get('job_file')
    engine_name = data.get('engine', 'maxrects')
    
    input_path = os.path.join(DATA_DIR, job_filename)
    sheet, parts, file_constraints = load_data(input_path)
    
    if not sheet or not parts:
        return jsonify({"error": "Failed to load job"}), 400

    constraints = file_constraints if file_constraints else ManufacturingConstraints(kerf=4.0, margin=10.0, allow_rotation=True)

    if engine_name.lower() == 'shelf':
        engine = ShelfNestingEngine()
    else:
        engine = MaxRectsEngine()

    result = engine.optimize(sheet, parts, constraints)
    
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
        "viz_url": f"/output/{viz_filename}"
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
