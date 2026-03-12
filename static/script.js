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

    let selectedEngine = 'maxrects';

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

    // 2. Engine selection toggle
    engineBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            engineBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedEngine = btn.dataset.engine;
        });
    });

    // 3. Run Optimization
    runBtn.addEventListener('click', async () => {
        const jobFile = jobSelect.value;
        if (!jobFile) return;

        runBtn.disabled = true;
        runBtn.innerText = "Optimizing...";
        statusChip.innerText = `Running ${selectedEngine.toUpperCase()} engine...`;

        try {
            const response = await fetch('/api/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_file: jobFile,
                    engine: selectedEngine
                })
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

    fetchJobs();
});
