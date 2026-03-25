document.addEventListener('DOMContentLoaded', () => {
    const jobSelect = document.getElementById('job-select');
    const engineBtns = document.querySelectorAll('.engine-btn[data-engine]');
    const runBtn = document.getElementById('run-btn');
    const vizImg = document.getElementById('viz-img');
    const placeholder = document.querySelector('.placeholder');
    const statusChip = document.getElementById('status-chip');

    const metricEfficiency = document.getElementById('metric-efficiency');
    const metricWaste = document.getElementById('metric-waste');
    const metricReusable = document.getElementById('metric-reusable');
    const metricScrap = document.getElementById('metric-scrap');
    const metricSheets = document.getElementById('metric-sheets');
    const runtimeDisplay = document.getElementById('runtime-display');

    // UI Input Mode
    const inputMethodBtns = document.querySelectorAll('.engine-btn[data-method]');
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

    // CSV Parsing & Validation
    csvUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        const csvError = document.getElementById('csv-error');
        if (!csvError) return;

        csvError.style.display = 'none';
        csvError.innerText = '';

        if (!file) return;

        // 1. File type validation
        if (!file.name.toLowerCase().endsWith('.csv')) {
            csvError.innerText = "Please upload a valid CSV file.";
            csvError.style.display = 'block';
            csvUpload.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = function(event) {
            const text = event.target.result;
            const rows = text.split('\n').map(r => r.trim()).filter(r => r);
            
            if (rows.length === 0) {
                csvError.innerText = "The uploaded CSV file is empty.";
                csvError.style.display = 'block';
                return;
            }

            // 2. Header validation
            const expectedHeaders = ["Name", "Width", "Height", "Quantity"];
            const actualHeaders = rows[0].split(',').map(h => h.trim());
            
            const headersMatch = expectedHeaders.every((h, i) => 
                actualHeaders[i] && actualHeaders[i].toLowerCase() === h.toLowerCase());

            if (!headersMatch) {
                csvError.innerText = "Please upload a valid CSV file with headers: Name, Width, Height, Quantity";
                csvError.style.display = 'block';
                csvUpload.value = '';
                return;
            }

            // Clear existing manual parts if user wants a clean slate? 
            // The prompt says "Populate parts list table", implying adding to it.
            // But usually validation should be for the whole file.

            let addedCount = 0;
            let errorRows = [];

            for (let i = 1; i < rows.length; i++) {
                const cols = rows[i].split(',').map(c => c.trim());
                
                // 3. Row data validation
                if (cols.length < 4) {
                    errorRows.push(i + 1);
                    continue;
                }

                const name = cols[0];
                const w = parseFloat(cols[1]);
                const h = parseFloat(cols[2]);
                const qty = parseInt(cols[3]);

                if (isNaN(w) || isNaN(h) || isNaN(qty) || w <= 0 || h <= 0 || qty <= 0) {
                    errorRows.push(i + 1);
                    continue;
                }

                addPartRow(name, w, h, qty);
                addedCount++;
            }

            if (errorRows.length > 0) {
                csvError.innerText = `Imported ${addedCount} parts. Some rows (${errorRows.join(', ')}) were skipped due to invalid data.`;
                csvError.style.display = 'block';
            } else {
                statusChip.innerText = `Successfully imported ${addedCount} parts from CSV.`;
            }

            csvUpload.value = ''; // Reset
        };
        reader.readAsText(file);
    });

    // 4. Run Optimization
    runBtn.addEventListener('click', async () => {
        let payload = { engine: selectedEngine };
        payload.cost_per_sheet = parseFloat(document.getElementById('cost-per-sheet').value) || 0;
        
        let min_area = document.getElementById('min-reusable-area');
        let min_dim = document.getElementById('min-reusable-dim');
        let kerf_input = document.getElementById('kerf');
        let margin_input = document.getElementById('margin');

        let parsed_area = min_area ? parseFloat(min_area.value) : NaN;
        payload.min_reusable_area = !isNaN(parsed_area) ? parsed_area * 92903 : 46450;
        payload.min_reusable_dim = min_dim ? (parseFloat(min_dim.value) || 100) : 100;
        payload.kerf = kerf_input ? (parseFloat(kerf_input.value) || 0) : 4.0;
        payload.margin = margin_input ? (parseFloat(margin_input.value) || 0) : 10.0;


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
                constraints: { 
                    kerf: payload.kerf, 
                    margin: payload.margin, 
                    allow_rotation: true,
                    min_reusable_area: payload.min_reusable_area,
                    min_reusable_dim: payload.min_reusable_dim
                }
            };
        }

        runBtn.disabled = true;
        runBtn.innerText = "Optimizing...";
        statusChip.innerText = `Running ${selectedEngine.toUpperCase()} engine...`;
        
        const fulfillmentChip = document.getElementById('fulfillment-chip');
        if (fulfillmentChip) fulfillmentChip.style.display = 'none';

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
            metricEfficiency.innerText = `${(result.metrics.efficiency || 0).toFixed(2)}%`;
            if (metricWaste) metricWaste.innerText = `${(result.metrics.waste || 0).toFixed(2)} sq mm`;
            if (metricReusable) metricReusable.innerText = `${(result.metrics.reusable_waste || 0).toFixed(2)} sq mm`;
            if (metricScrap) metricScrap.innerText = `${(result.metrics.scrap_waste || 0).toFixed(2)} sq mm`;
            metricSheets.innerText = result.metrics.sheets || 0;
            runtimeDisplay.innerText = `Runtime: ${(result.metrics.runtime || 0).toFixed(4)}s`;
            
            if (fulfillmentChip && result.parts_fulfilled_count > 0) {
                fulfillmentChip.innerText = `${result.parts_fulfilled_count} part(s) fulfilled using reusable material`;
                fulfillmentChip.style.display = 'block';
            }
            
            const metricMatCost = document.getElementById('metric-material-cost');
            const metricReusableCost = document.getElementById('metric-reusable-cost');
            const metricScrapCost = document.getElementById('metric-scrap-cost');
            
            if (metricMatCost) {
                const val = (result.metrics && result.metrics.material_cost !== undefined) ? result.metrics.material_cost : 0;
                metricMatCost.innerText = `₹${Number(val).toFixed(2)}`;
            }
            if (metricReusableCost) {
                const val = (result.metrics && result.metrics.reusable_waste_cost !== undefined) ? result.metrics.reusable_waste_cost : 0;
                metricReusableCost.innerText = `+ ₹${Number(val).toFixed(2)}`;
            }
            if (metricScrapCost) {
                const val = (result.metrics && result.metrics.scrap_waste_cost !== undefined) ? result.metrics.scrap_waste_cost : 0;
                metricScrapCost.innerText = `- ₹${Number(val).toFixed(2)}`;
            }

            // Comparative Analysis Table
            const compSection = document.getElementById('comparative-analysis-section');
            const compTableBody = document.getElementById('comparative-table-body');
            
            if (result.candidates_data && result.candidates_data.length > 0) {
                compTableBody.innerHTML = result.candidates_data.map((c, i) => `
                    <tr style="${i === 0 ? 'background: rgba(34, 197, 94, 0.1); font-weight: 600;' : ''}">
                        <td>${c.algorithm || 'Unknown'} ${i === 0 ? '<span class="alg-badge" style="background: var(--success); margin-left:8px;">BEST</span>' : ''}</td>
                        <td>${c.sheets || 0}</td>
                        <td>${(c.utilization || 0).toFixed(2)}%</td>
                        <td>${(c.wastage || 0).toFixed(2)}%</td>
                        <td>₹${(c.material_cost || 0).toFixed(2)}</td>
                    </tr>
                `).join('');
                compSection.style.display = 'block';
            } else if (compSection) {
                // Not intelligent mode, hide it or just show the single result
                compSection.style.display = 'block';
                compTableBody.innerHTML = `
                    <tr style="background: rgba(34, 197, 94, 0.1); font-weight: 600;">
                        <td>${result.engine || 'Unknown'} <span class="alg-badge" style="background: var(--success); margin-left:8px;">SINGLE</span></td>
                        <td>${result.metrics.sheets || 0}</td>
                        <td>${(result.metrics.efficiency || 0).toFixed(2)}%</td>
                        <td>${(result.metrics.wastage || 0).toFixed(2)}%</td>
                        <td>₹${result.metrics.material_cost !== undefined ? result.metrics.material_cost.toFixed(2) : '0.00'}</td>
                    </tr>
                `;
            }

            // Handle Waste Data Table
            const wasteSection = document.getElementById('waste-data-section');
            const wasteTableBody = document.getElementById('waste-table-body');
            const wasteTableFoot = document.getElementById('waste-table-foot');
            
            if (result.waste_details && result.waste_details.length > 0) {
                let totalReusabe = 0;
                let totalScrap = 0;
                wasteTableBody.innerHTML = result.waste_details.map(row => {
                    totalReusabe += (row.reusable_waste_area || 0);
                    totalScrap += (row.scrap_waste_area || 0);
                    return `
                    <tr>
                        <td>${row.sheet_number}</td>
                        <td style="font-weight: 600;">${row.sheet_id}</td>
                        <td style="color: var(--accent); font-weight: 600;">${(row.waste_area || 0).toFixed(2)} </td>
                        <td style="color: var(--success);">${(row.reusable_waste_area || 0).toFixed(2)}</td>
                        <td style="color: #fb7185;">${(row.scrap_waste_area || 0).toFixed(2)}</td>
                        <td>${(row.waste_percentage || 0).toFixed(2)}%</td>
                        <td>₹${(row.material_cost || 0).toFixed(2)}</td>
                        <td style="color: #fb7185; font-weight: 600;">₹${(row.scrap_waste_cost || 0).toFixed(2)}</td>
                    </tr>
                `}).join('');
                
                if (wasteTableFoot) {
                    wasteTableFoot.innerHTML = `
                        <tr style="background: rgba(15, 23, 42, 0.5);">
                            <td colspan="3" style="text-align: right; font-weight: 700; text-transform: uppercase;">Totals:</td>
                            <td style="color: var(--success); font-weight: 700; font-size: 1.1em;">${totalReusabe.toFixed(2)}</td>
                            <td style="color: #fb7185; font-weight: 700; font-size: 1.1em;">${totalScrap.toFixed(2)}</td>
                            <td colspan="3"></td>
                        </tr>
                    `;
                }

                wasteSection.style.display = 'block';
            } else {
                wasteSection.style.display = 'none';
            }

            // Update Visualization
            if (result.viz_url) {
                vizImg.src = result.viz_url + '?t=' + new Date().getTime(); // Prevent caching
                vizImg.style.display = 'block';
                placeholder.style.display = 'none';
            } else {
                vizImg.style.display = 'none';
                placeholder.style.display = 'block';
                placeholder.innerText = 'All parts fulfilled by reusable scrap. No visualization generated.';
            }

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
