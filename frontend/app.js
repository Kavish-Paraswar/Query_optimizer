const API = '';

const modeSelect = document.getElementById('modeSelect');
const applyModeBtn = document.getElementById('applyMode');
const reportStatus = document.getElementById('reportStatus');

const exactName = document.getElementById('exactName');
const exactBtn = document.getElementById('exactBtn');
const exactMeta = document.getElementById('exactMeta');
const exactCount = document.getElementById('exactCount');

const rangeLo = document.getElementById('rangeLo');
const rangeHi = document.getElementById('rangeHi');
const rangeBtn = document.getElementById('rangeBtn');
const rangeMeta = document.getElementById('rangeMeta');
const rangeCount = document.getElementById('rangeCount');

const prefixText = document.getElementById('prefixText');
const prefixBtn = document.getElementById('prefixBtn');
const prefixMeta = document.getElementById('prefixMeta');
const prefixCount = document.getElementById('prefixCount');

const runBenchBtn = document.getElementById('runBench');
const generatePdfBtn = document.getElementById('generatePdf');
const downloadPdfLink = document.getElementById('downloadPdf');
const benchTableBody = document.querySelector('#benchTable tbody');
const compareBtn = document.getElementById('compareBtn');
const compareTableBody = document.querySelector('#compareTable tbody');
let compareChart;

let chart;

async function api(path, options={}){
    const res = await fetch(API + path, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if(!res.ok){
        const t = await res.text();
        throw new Error(t || res.statusText);
    }
    const ct = res.headers.get('content-type') || '';
    if(ct.includes('application/json')) return res.json();
    return res.text();
}

function updateReportStatus(){
    api('/status').then(s => {
        const parts = [];
        parts.push('mode: ' + s.mode);
        if(s.reports.pdf) parts.push('pdf ✓');
        if(s.reports.summary_txt) parts.push('summary ✓');
        if(s.reports.timings_png) parts.push('chart ✓');
        reportStatus.textContent = parts.join(' • ');
    }).catch(() => { reportStatus.textContent = '—'; });
}

applyModeBtn.addEventListener('click', async () => {
    const mode = modeSelect.value;
    const memory_limit = 200000;
    await api('/mode', { method: 'POST', body: JSON.stringify({ mode, memory_limit }) });
    updateReportStatus();
});

exactBtn.addEventListener('click', async () => {
    const name = exactName.value.trim();
    if(!name) return;
    const res = await api('/search/exact', { method: 'POST', body: JSON.stringify({ name }) });
    exactMeta.textContent = `${res.count} results • ${res.time_s.toFixed(6)}s`;
    exactCount.textContent = res.count.toLocaleString();
});

rangeBtn.addEventListener('click', async () => {
    const lo = parseInt(rangeLo.value, 10);
    const hi = parseInt(rangeHi.value, 10);
    if(Number.isNaN(lo) || Number.isNaN(hi)) return;
    const res = await api('/search/range', { method: 'POST', body: JSON.stringify({ lo, hi }) });
    rangeMeta.textContent = `${res.count} results • ${res.time_s.toFixed(6)}s`;
    rangeCount.textContent = res.count.toLocaleString();
});

prefixBtn.addEventListener('click', async () => {
    const prefix = prefixText.value.trim();
    if(!prefix) return;
    const res = await api('/search/prefix', { method: 'POST', body: JSON.stringify({ prefix }) });
    prefixMeta.textContent = `${res.count} results • ${res.time_s.toFixed(6)}s`;
    prefixCount.textContent = res.count.toLocaleString();
});

runBenchBtn.addEventListener('click', async () => {
    const data = await api('/benchmarks/run', { method: 'POST' });
    renderBenchmark(data.benchmarks || []);
    updateReportStatus();
});
compareBtn?.addEventListener('click', async () => {
    const data = await api('/compare/dbs', { method: 'POST' });
    renderCompare(data);
});

function renderCompare(data){
    // Build times matrix
    const systems = ['mysql','postgres','in_memory'];
    const labels = ['Exact','Range','Prefix'];
    const rows = [];
    systems.forEach(sys => {
        const arr = Array.isArray(data[sys]) ? data[sys] : [];
        const times = labels.map((lbl, i) => (arr[i]?.[2]) || 0);
        const total = times.reduce((a,b)=>a+b,0);
        rows.push({ system: sys, times, total });
    });

    // Table
    compareTableBody.innerHTML = '';
    rows.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${r.system}</td><td>${r.times[0].toFixed(6)}</td><td>${r.times[1].toFixed(6)}</td><td>${r.times[2].toFixed(6)}</td><td>${r.total.toFixed(6)}</td>`;
        compareTableBody.appendChild(tr);
    });

    // Chart (stacked bars by system)
    const ctx = document.getElementById('compareChart');
    if(compareChart) compareChart.destroy();
    compareChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: rows.map(r => r.system.toUpperCase()),
            datasets: [
                { label: 'Exact', data: rows.map(r=>r.times[0]), backgroundColor: '#4f8cff' },
                { label: 'Range', data: rows.map(r=>r.times[1]), backgroundColor: '#22d3ee' },
                { label: 'Prefix', data: rows.map(r=>r.times[2]), backgroundColor: '#7aa8ff' },
            ]
        },
        options: { responsive: true, plugins: { }, scales: { x: { stacked: true }, y: { stacked: true } } }
    });
}

generatePdfBtn.addEventListener('click', async () => {
    await api('/reports/pdf', { method: 'POST', body: JSON.stringify({}) });
    updateReportStatus();
    window.location.href = '/reports/pdf/download';
});

function renderBenchmark(bench){
    benchTableBody.innerHTML = '';
    const labels = [], times = [];
    bench.forEach(item => {
        const tr = document.createElement('tr');
        const [method, count, time] = item;
        tr.innerHTML = `<td>${method}</td><td>${count}</td><td>${time.toFixed(6)}</td>`;
        benchTableBody.appendChild(tr);
        labels.push(method); times.push(time);
    });
    const ctx = document.getElementById('benchChart');
    if(chart) chart.destroy();
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{ label: 'Time (s)', data: times, backgroundColor: '#4f8cff' }]
        },
        options: { responsive: true, plugins: { legend: { display: false } } }
    });
}

updateReportStatus();

