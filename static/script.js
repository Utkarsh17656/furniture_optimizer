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

    // Theme Toggle Logic
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        const iconMoon = themeBtn.querySelector('.icon-moon');
        const iconSun = themeBtn.querySelector('.icon-sun');
        
        // Initialize from local storage
        if (localStorage.getItem('theme') === 'light') {
            document.documentElement.classList.add('light-mode');
            document.body.classList.add('light-mode');
            if(iconMoon) iconMoon.style.display = 'none';
            if(iconSun) iconSun.style.display = 'inline';
        }

        themeBtn.addEventListener('click', () => {
            document.documentElement.classList.toggle('light-mode');
            document.body.classList.toggle('light-mode');
            
            const isLight = document.body.classList.contains('light-mode');
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            
            if(iconMoon) iconMoon.style.display = isLight ? 'none' : 'inline';
            if(iconSun) iconSun.style.display = isLight ? 'inline' : 'none';
        });
    }

    // UI Input Mode
    const inputMethodBtns = document.querySelectorAll('.engine-btn[data-method]');
    const jsonInputGroup = document.getElementById('json-input-group');
    const manualInputGroup = document.getElementById('manual-input-group');
    const addPartBtn = document.getElementById('add-part-btn');
    const partsTbody = document.getElementById('parts-tbody');
    const csvUpload = document.getElementById('csv-upload');
    const excelUpload = document.getElementById('excel-upload');

    const shapeModeSelect = document.getElementById('shape-mode-select');
    let selectedEngine = 'intelligent';
    let inputMethod = 'json'; // default
    let shapeMode = 'rect-only';

    // Helper: Add a part row
    function addPartRow(name = '', w = '', h = '', qty = 1, type = 'RECT') {
        const tr = document.createElement('tr');
        const showShape = (shapeMode === 'shapes');
        
        tr.innerHTML = `
            <td class="shape-col" style="${showShape ? '' : 'display: none;'}">
                <select class="part-type">
                    <option value="RECT" ${type === 'RECT' ? 'selected' : ''}>Rect</option>
                    <option value="CIRCLE" ${type === 'CIRCLE' ? 'selected' : ''}>Circle</option>
                    <option value="RIGHT_TRIANGLE" ${type === 'RIGHT_TRIANGLE' ? 'selected' : ''}>Right Tri</option>
                    <option value="ISOSCELES_TRIANGLE" ${type === 'ISOSCELES_TRIANGLE' ? 'selected' : ''}>Iso Tri</option>
                    <option value="SCALENE_TRIANGLE" ${type === 'SCALENE_TRIANGLE' ? 'selected' : ''}>Scalene Tri</option>
                </select>
            </td>
            <td><input type="text" class="part-name" value="${name}" placeholder="Name" style="width: 80px;"></td>
            <td><input type="number" class="part-w" value="${w}" min="1" placeholder="W" style="width: 60px;"></td>
            <td><input type="number" class="part-h" value="${h}" min="1" placeholder="H" style="width: 60px;"></td>
            <td><input type="number" class="part-qty" value="${qty}" min="1" style="width: 50px;"></td>
            <td><button class="icon-btn remove-btn" title="Remove">X</button></td>
        `;
        
        const typeSelect = tr.querySelector('.part-type');
        const wInput = tr.querySelector('.part-w');
        const hInput = tr.querySelector('.part-h');
        
        const updatePlaceholders = () => {
            const t = typeSelect.value;
            if (t === 'RECT') {
                wInput.placeholder = 'W';
                hInput.placeholder = 'H';
                hInput.disabled = false;
                hInput.style.opacity = '1';
            } else if (t === 'CIRCLE') {
                wInput.placeholder = 'Radius';
                hInput.placeholder = '-';
                hInput.disabled = true;
                hInput.style.opacity = '0.3';
                hInput.value = '';
            } else if (t === 'RIGHT_TRIANGLE' || t === 'ISOSCELES_TRIANGLE' || t === 'SCALENE_TRIANGLE' || t === 'TRIANGLE') {
                wInput.placeholder = 'Breadth';
                hInput.placeholder = 'Height';
                hInput.disabled = false;
                hInput.style.opacity = '1';
            }
        };

        typeSelect.addEventListener('change', updatePlaceholders);
        updatePlaceholders();

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
    /* 
    engineBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            engineBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedEngine = btn.dataset.engine;
        });
    });
    */

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

    shapeModeSelect.addEventListener('change', () => {
        shapeMode = shapeModeSelect.value;
        const colHeader = document.querySelector('.shape-col');
        const rows = document.querySelectorAll('.shape-col');
        const dim1Header = document.getElementById('dim1-header');
        const dim2Header = document.getElementById('dim2-header');

        if (shapeMode === 'shapes') {
            rows.forEach(r => r.style.display = 'table-cell');
            dim1Header.innerText = 'Dim 1';
            dim2Header.innerText = 'Dim 2';
        } else {
            rows.forEach(r => r.style.display = 'none');
            dim1Header.innerText = 'W';
            dim2Header.innerText = 'H';
            // Reset all types to RECT if switching back to simple mode? 
            // Better to just hide and ignore metadata later.
        }
    });

    // 3. Manual Entry Handlers
    addPartBtn.addEventListener('click', () => addPartRow());

    // Data processing for uploaded files
    const processImportedData = (rows, uploaderInput, sourceType) => {
        const uploadError = document.getElementById('upload-error');
        if (rows.length === 0) {
            uploadError.innerText = `The uploaded ${sourceType} file is empty.`;
            uploadError.style.display = 'block';
            uploaderInput.value = '';
            return;
        }

        const headers = rows[0].map(h => String(h).trim().toLowerCase());
        const nameIdx = headers.indexOf('name');
        const wIdx = headers.indexOf('width');
        const hIdx = headers.indexOf('height');
        const qtyIdx = headers.indexOf('quantity');
        let typeIdx = headers.indexOf('type');
        if (typeIdx === -1) typeIdx = headers.indexOf('shape');

        if (nameIdx === -1 || wIdx === -1 || hIdx === -1 || qtyIdx === -1) {
            uploadError.innerText = `Please upload a valid ${sourceType} file with headers: Name, Width, Height, Quantity. Optional: Type.`;
            uploadError.style.display = 'block';
            uploaderInput.value = '';
            return;
        }

        let addedCount = 0;
        let errorRows = [];

        // Helper to parse shape type
        const parseShapeType = (rawType) => {
            if (!rawType) return 'RECT';
            const t = String(rawType).trim().toUpperCase();
            if (t.includes('RECT') || t.includes('SQUARE')) return 'RECT';
            if (t.includes('CIRC')) return 'CIRCLE';
            if (t.includes('RIGHT')) return 'RIGHT_TRIANGLE';
            if (t.includes('ISO')) return 'ISOSCELES_TRIANGLE';
            if (t.includes('SCA') || t.includes('TRI')) return 'SCALENE_TRIANGLE';
            return 'RECT';
        };

        for (let i = 1; i < rows.length; i++) {
            const cols = rows[i];
            if (!cols || cols.length === 0) continue; // skip empty rows

            const name = cols[nameIdx];
            const w = parseFloat(cols[wIdx]);
            // Circle doesn't strictly need Height but we should parse it safely
            let hText = String(cols[hIdx] || '').trim();
            const h = (hText === '' || hText === '-') ? '-' : parseFloat(cols[hIdx]);
            const qty = parseInt(cols[qtyIdx]);
            
            const rawType = typeIdx !== -1 ? cols[typeIdx] : 'RECT';
            const type = parseShapeType(rawType);

            // Validation logic
            let isValid = true;
            let finalH = 1; // Default dummy for circle
            if (isNaN(w) || isNaN(qty) || w <= 0 || qty <= 0) {
                isValid = false;
            }
            if (type !== 'CIRCLE') {
                if (h === '-' || isNaN(h) || h <= 0) isValid = false;
                else finalH = h;
            } else {
                finalH = h === '-' || isNaN(h) ? w : parseFloat(h); // just in case
            }

            if (!isValid) {
                errorRows.push(i + 1);
                continue;
            }

            addPartRow(name, w, finalH, qty, type);
            addedCount++;
        }

        if (errorRows.length > 0) {
            uploadError.innerText = `Imported ${addedCount} parts. Some rows (${errorRows.join(', ')}) were skipped due to invalid data.`;
            uploadError.style.display = 'block';
        } else {
            statusChip.innerText = `Successfully imported ${addedCount} parts from ${sourceType}.`;
        }

        uploaderInput.value = ''; // Reset
    };

    // CSV Parsing & Validation
    csvUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        const uploadError = document.getElementById('upload-error');
        if (!uploadError) return;

        uploadError.style.display = 'none';
        uploadError.innerText = '';

        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.csv')) {
            uploadError.innerText = "Please upload a valid CSV file.";
            uploadError.style.display = 'block';
            csvUpload.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = function(event) {
            const text = event.target.result;
            const lines = text.split('\n').map(r => r.trim()).filter(r => r);
            const rows = lines.map(line => line.split(',').map(c => c.trim()));
            processImportedData(rows, csvUpload, 'CSV');
        };
        reader.readAsText(file);
    });

    // Excel Parsing & Validation
    if (excelUpload) {
        excelUpload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            const uploadError = document.getElementById('upload-error');
            if (!uploadError) return;

            uploadError.style.display = 'none';
            uploadError.innerText = '';

            if (!file) return;

            if (!file.name.toLowerCase().match(/\.(xlsx|xls)$/)) {
                uploadError.innerText = "Please upload a valid Excel file.";
                uploadError.style.display = 'block';
                excelUpload.value = '';
                return;
            }

            const reader = new FileReader();
            reader.onload = function(event) {
                try {
                    const data = new Uint8Array(event.target.result);
                    const workbook = XLSX.read(data, {type: 'array'});
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const rows = XLSX.utils.sheet_to_json(worksheet, {header: 1});
                    processImportedData(rows, excelUpload, 'Excel');
                } catch (err) {
                    console.error("Error reading Excel:", err);
                    uploadError.innerText = "Failed to parse Excel file.";
                    uploadError.style.display = 'block';
                    excelUpload.value = '';
                }
            };
            reader.readAsArrayBuffer(file);
        });
    }

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
        
        const showScrapLabelsEl = document.getElementById('show-scrap-labels');
        payload.showScrapLabels = showScrapLabelsEl ? showScrapLabelsEl.checked : true;


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
                const type = shapeMode === 'shapes' ? row.querySelector('.part-type').value : 'RECT';
                const name = row.querySelector('.part-name').value || `Part-${partIdCounter}`;
                const w = parseFloat(row.querySelector('.part-w').value) || 0;
                const h = parseFloat(row.querySelector('.part-h').value) || 0;
                const qty = parseInt(row.querySelector('.part-qty').value) || 1;

                if (w > 0 && (h > 0 || type === 'CIRCLE') && qty > 0) {
                    for (let i = 0; i < qty; i++) {
                        let finalW = w;
                        let finalH = h;
                        let metadata = { shape: type };

                        if (type === 'CIRCLE') {
                            finalW = w * 2;
                            finalH = w * 2;
                            metadata.radius = w;
                        } else if (type === 'RIGHT_TRIANGLE' || type === 'ISOSCELES_TRIANGLE' || type === 'SCALENE_TRIANGLE' || type === 'TRIANGLE') {
                            finalW = w;
                            finalH = h;
                            metadata.breadth = w;
                            metadata.height = h;
                        }

                        parts.push({
                            id: `MANUAL-${partIdCounter++}`,
                            name: qty > 1 ? `${name} (${i+1}/${qty})` : name,
                            width: finalW,
                            height: finalH,
                            metadata: metadata
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
        
        const labelsBtn = document.getElementById('download-labels-btn');
        if (labelsBtn) labelsBtn.style.display = 'none';

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
                if (compTableBody) {
                    compTableBody.innerHTML = result.candidates_data.map((c, i) => `
                        <tr style="${i === 0 ? 'background: rgba(34, 197, 94, 0.1); font-weight: 600;' : ''}">
                            <td>${c.algorithm || 'Unknown'} ${i === 0 ? '<span class="alg-badge" style="background: var(--success); margin-left:8px;">BEST</span>' : ''}</td>
                            <td>${c.sheets || 0}</td>
                            <td>${(c.utilization || 0).toFixed(2)}%</td>
                            <td>${(c.wastage || 0).toFixed(2)}%</td>
                            <td>₹${(c.material_cost || 0).toFixed(2)}</td>
                        </tr>
                    `).join('');
                }
                if (compSection) compSection.style.display = 'block';
            } else if (compSection) {
                // Not intelligent mode, hide it or just show the single result
                compSection.style.display = 'block';
                if (compTableBody) {
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
            
            if (labelsBtn && result.engine !== 'Scrap Reuse') {
                labelsBtn.style.display = 'inline-block';
            }

        } catch (error) {
            console.error('Optimization error:', error);
            statusChip.innerText = "Error during optimization.";
        } finally {
            runBtn.disabled = false;
            runBtn.innerText = "Run Optimizer";
        }
    });

    // 5. CSV Preview & Download logic
    const previewModal = document.getElementById('csv-preview-modal');
    const previewTitle = document.getElementById('preview-title');
    const previewThead = document.getElementById('preview-thead');
    const previewTbody = document.getElementById('preview-tbody');
    const closePreviewBtn = document.getElementById('close-preview-btn');
    const cancelPreviewBtn = document.getElementById('cancel-preview-btn');
    const confirmDownloadBtn = document.getElementById('confirm-download-btn');

    let currentDownloadUrl = '';
    let currentFilename = '';

    const showCSVPreview = async (url, title, filename) => {
        try {
            const response = await fetch(url);
            const csvText = await response.text();
            const lines = csvText.split('\n').map(l => l.trim()).filter(l => l);
            
            if (lines.length === 0) {
                alert("The report is currently empty.");
                return;
            }

            previewTitle.innerText = title;
            currentDownloadUrl = url;
            currentFilename = filename;

            // Headers
            const headers = lines[0].split(',');
            previewThead.innerHTML = `<tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr>`;

            // Body (limited to first 50 rows for performance)
            const bodyLines = lines.slice(1, 51);
            previewTbody.innerHTML = bodyLines.map(line => {
                const cells = line.split(',');
                return `<tr>${cells.map(c => `<td>${c}</td>`).join('')}</tr>`;
            }).join('');

            if (lines.length > 51) {
                const footerTr = document.createElement('tr');
                footerTr.innerHTML = `<td colspan="${headers.length}" style="text-align: center; color: var(--text-secondary); font-style: italic;">... and ${lines.length - 51} more rows.</td>`;
                previewTbody.appendChild(footerTr);
            }

            previewModal.style.display = 'flex';
        } catch (error) {
            console.error('Error fetching CSV:', error);
            alert("Could not load preview.");
        }
    };

    const hidePreview = () => {
        previewModal.style.display = 'none';
        currentDownloadUrl = '';
    };

    closePreviewBtn.addEventListener('click', hidePreview);
    cancelPreviewBtn.addEventListener('click', hidePreview);
    
    confirmDownloadBtn.addEventListener('click', () => {
        if (currentDownloadUrl) {
            window.location.href = currentDownloadUrl;
            hidePreview();
        }
    });

    const downloadCsvBtn = document.getElementById('download-csv-btn');
    downloadCsvBtn.addEventListener('click', () => {
        showCSVPreview('/api/download_inventory', 'Inventory Report Preview', 'inventory.csv');
    });
    
    const downloadLabelsBtn = document.getElementById('download-labels-btn');
    if (downloadLabelsBtn) {
        downloadLabelsBtn.addEventListener('click', () => {
            showCSVPreview('/api/download_labels', 'Scrap Labels Preview', 'labels.csv');
        });
    }

    // Init
    fetchJobs();
    addPartRow('Side Panel', 600, 400, 2); // Add a default row so it's not empty
});
