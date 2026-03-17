document.addEventListener('DOMContentLoaded', () => {
    const jobSelect = document.getElementById('job-select');
    const engineBtns = document.querySelectorAll('.engine-btn');
    const runBtn = document.getElementById('run-btn');
    const vizImg = document.getElementById('viz-img');
    const placeholder = document.querySelector('.placeholder');
    const statusChip = document.getElementById('status-chip');

    const metricEfficiency = document.getElementById('metric-efficiency');
    const metricWastage = document.getElementById('metric-wastage');
    const metricSheets = document.getElementById('metric-sheets');
    const runtimeDisplay = document.getElementById('runtime-display');

    // UI Input Mode
    const inputMethodBtns = document.querySelectorAll('#input-method-toggle .engine-btn');
    const jsonInputGroup = document.getElementById('json-input-group');
    const manualInputGroup = document.getElementById('manual-input-group');
    const addPartBtn = document.getElementById('add-part-btn');
    const partsTbody = document.getElementById('parts-tbody');
    const csvUpload = document.getElementById('csv-upload');

    let selectedEngine = 'maxrects';
    let inputMethod = 'json'; // default

    // Helper: Add a part row
    function addPartRow(name = '', w = '', h = '', qty = 1) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="part-name" value="${name}" placeholder="Part Name"></td>
            <td><input type="number" class="part-w" value="${w}" min="1" placeholder="W" style="width: 60px;"></td>
            <td><input type="number" class="part-h" value="${h}" min="1" placeholder="H" style="width: 60px;"></td>
            <td><input type="number" class="part-qty" value="${qty}" min="1" style="width: 50px;"></td>
            <td><button class="icon-btn remove-btn" title="Remove">X</button></td>
        `;
        // Setup remove button
        tr.querySelector('.remove-btn').addEventListener('click', () => {
            tr.remove();
        });
        partsTbody.appendChild(tr);
    }

    // 1. Fetch available jobs
    async function fetchJobs() {
        try {
            const response = await fetch('/api/jobs');
            const jobs = await response.json();

            jobSelect.innerHTML = jobs.map(job => `<option value="${job}">${job}</option>`).join('');
            statusChip.innerText = "System Ready: Choose a job and run.";
        } catch (error) {
            console.error('Error fetching jobs:', error);
            statusChip.innerText = "Error loading jobs.";
        }
    }

    // 2. Toggles
    engineBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            engineBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedEngine = btn.dataset.engine;
        });
    });

    inputMethodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            inputMethodBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            inputMethod = btn.dataset.method;
            
            if (inputMethod === 'json') {
                jsonInputGroup.style.display = 'block';
                manualInputGroup.style.display = 'none';
            } else {
                jsonInputGroup.style.display = 'none';
                manualInputGroup.style.display = 'block';
            }
        });
    });

    // 3. Manual Entry Handlers
    addPartBtn.addEventListener('click', () => addPartRow());

    // CSV Parsing
    csvUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function(event) {
            const text = event.target.result;
            const rows = text.split('\n').map(r => r.trim()).filter(r => r);
            
            // Assuming first row is header, skip it if it looks like one
            let startIdx = 0;
            if (rows[0].toLowerCase().includes('name') || rows[0].toLowerCase().includes('width')) {
                startIdx = 1;
            }

            for (let i = startIdx; i < rows.length; i++) {
                const cols = rows[i].split(',').map(c => c.trim());
                if (cols.length >= 3) {
                    const name = cols[0];
                    const w = parseInt(cols[1]) || 0;
                    const h = parseInt(cols[2]) || 0;
                    const qty = cols.length >= 4 ? (parseInt(cols[3]) || 1) : 1;
                    if (w > 0 && h > 0) {
                        addPartRow(name, w, h, qty);
                    }
                }
            }
            csvUpload.value = ''; // Reset
        };
        reader.readAsText(file);
    });

    // 4. Run Optimization
    runBtn.addEventListener('click', async () => {
        let payload = { engine: selectedEngine };

        if (inputMethod === 'json') {
            const jobFile = jobSelect.value;
            if (!jobFile) {
                alert("Please select a job file.");
                return;
            }
            payload.job_file = jobFile;
        } else {
            // Build manual payload
            const sw = parseFloat(document.getElementById('sheet-width').value) || 0;
            const sh = parseFloat(document.getElementById('sheet-height').value) || 0;
            const mat = document.getElementById('sheet-material').value;
            const kerf = parseFloat(document.getElementById('kerf').value) || 0;
            const margin = parseFloat(document.getElementById('margin').value) || 0;

            if (sw <= 0 || sh <= 0) {
                alert("Invalid sheet dimensions.");
                return;
            }

            const parts = [];
            let partIdCounter = 1;
            const rows = partsTbody.querySelectorAll('tr');
            
            if (rows.length === 0) {
                alert("Please add at least one part.");
                return;
            }

            rows.forEach(row => {
                const name = row.querySelector('.part-name').value || `Part-${partIdCounter}`;
                const w = parseFloat(row.querySelector('.part-w').value) || 0;
                const h = parseFloat(row.querySelector('.part-h').value) || 0;
                const qty = parseInt(row.querySelector('.part-qty').value) || 1;

                if (w > 0 && h > 0 && qty > 0) {
                    for (let i = 0; i < qty; i++) {
                        parts.push({
                            id: `MANUAL-${partIdCounter++}`,
                            name: qty > 1 ? `${name} (${i+1}/${qty})` : name,
                            width: w,
                            height: h
                        });
                    }
                }
            });

            if (parts.length === 0) {
                alert("No valid parts found. Check dimensions.");
                return;
            }

            payload.job_data = {
                sheet: { id: "SHEET-MANUAL", width: sw, height: sh, material: mat },
                parts: parts,
                constraints: { kerf: kerf, margin: margin, allow_rotation: true }
            };
        }

        runBtn.disabled = true;
        runBtn.innerText = "Optimizing...";
        statusChip.innerText = `Running ${selectedEngine.toUpperCase()} engine...`;

        try {
            const response = await fetch('/api/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.error) {
                alert(result.error);
                return;
            }

            // Update Metrics
            metricEfficiency.innerText = `${result.metrics.efficiency}%`;
            metricWastage.innerText = `${result.metrics.wastage}%`;
            metricSheets.innerText = result.metrics.sheets;
            runtimeDisplay.innerText = `Runtime: ${result.metrics.runtime}s`;

            // Color coding for wastage
            if (result.metrics.wastage > 25) {
                metricWastage.classList.add('wastage-high');
                metricWastage.classList.remove('wastage-low');
            } else {
                metricWastage.classList.add('wastage-low');
                metricWastage.classList.remove('wastage-high');
            }

            // Handle Waste Data Table
            const wasteSection = document.getElementById('waste-data-section');
            const wasteTableBody = document.getElementById('waste-table-body');
            const wasteTableFoot = document.getElementById('waste-table-foot');
            
            if (result.waste_details && result.waste_details.length > 0) {
                let totalWaste = 0;
                wasteTableBody.innerHTML = result.waste_details.map(row => {
                    totalWaste += row.waste_area;
                    return `
                    <tr>
                        <td>${row.sheet_id} - [${row.sheet_index}]</td>
                        <td><span class="alg-badge">${row.algorithm}</span></td>
                        <td>${row.material}</td>
                        <td style="color: var(--accent); font-weight: 600;">${row.waste_area.toFixed(2)} sq units</td>
                        <td>${new Date(row.timestamp).toLocaleTimeString()}</td>
                    </tr>
                `}).join('');
                
                if (wasteTableFoot) {
                    wasteTableFoot.innerHTML = `
                        <tr style="background: rgba(15, 23, 42, 0.5);">
                            <td colspan="3" style="text-align: right; font-weight: 700; text-transform: uppercase;">Total Waste Area:</td>
                            <td style="color: #fb7185; font-weight: 700; font-size: 1.1em;">${totalWaste.toFixed(2)} sq units</td>
                            <td></td>
                        </tr>
                    `;
                }

                wasteSection.style.display = 'block';
            } else {
                wasteSection.style.display = 'none';
            }

            // Update Visualization
            vizImg.src = result.viz_url + '?t=' + new Date().getTime(); // Prevent caching
            vizImg.style.display = 'block';
            placeholder.style.display = 'none';

            statusChip.innerText = `Optimization Complete: ${result.engine} engine used.`;

        } catch (error) {
            console.error('Optimization error:', error);
            statusChip.innerText = "Error during optimization.";
        } finally {
            runBtn.disabled = false;
            runBtn.innerText = "Run Optimizer";
        }
    });

    // 5. Download CSV Action
    const downloadCsvBtn = document.getElementById('download-csv-btn');
    downloadCsvBtn.addEventListener('click', () => {
        window.location.href = '/api/download_inventory';
    });

    // Init
    fetchJobs();
    addPartRow('Side Panel', 600, 400, 2); // Add a default row so it's not empty
});
