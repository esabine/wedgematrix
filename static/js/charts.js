/* ==========================================================================
   WedgeMatrix — charts.js
   Chart.js visualizations for the Analytics dashboard
   ========================================================================== */

// Golf-appropriate color palette
var GOLF_COLORS = {
    green:      'rgba(45, 106, 79, 0.8)',
    greenLight: 'rgba(64, 145, 108, 0.7)',
    greenPale:  'rgba(82, 183, 136, 0.6)',
    blue:       'rgba(54, 162, 235, 0.7)',
    red:        'rgba(220, 53, 69, 0.7)',
    orange:     'rgba(255, 159, 64, 0.7)',
    purple:     'rgba(153, 102, 255, 0.7)',
    teal:       'rgba(32, 201, 151, 0.7)',
    gold:       'rgba(255, 193, 7, 0.7)',
    pink:       'rgba(214, 51, 132, 0.7)',
    gray:       'rgba(108, 117, 125, 0.5)',
    slate:      'rgba(69, 90, 100, 0.7)',
    lime:       'rgba(118, 190, 60, 0.7)',
    navy:       'rgba(27, 67, 50, 0.8)',
};

var CLUB_PALETTE = [
    GOLF_COLORS.green, GOLF_COLORS.blue, GOLF_COLORS.red,
    GOLF_COLORS.orange, GOLF_COLORS.purple, GOLF_COLORS.teal,
    GOLF_COLORS.gold, GOLF_COLORS.pink, GOLF_COLORS.slate,
    GOLF_COLORS.lime, GOLF_COLORS.navy, GOLF_COLORS.greenLight,
    GOLF_COLORS.greenPale, GOLF_COLORS.gray
];

// Store chart instances for cleanup on refresh
var chartInstances = {};

function destroyChart(id) {
    if (chartInstances[id]) {
        chartInstances[id].destroy();
        delete chartInstances[id];
    }
}

/* ---------- Load All Analytics ---------- */
function loadAnalytics() {
    var sessionEl = document.getElementById('analytics-session');
    var clubEl = document.getElementById('analytics-club');
    var dateRangeEl = document.getElementById('analytics-date-range');
    var sessionId = sessionEl ? sessionEl.value : '';
    var clubFilter = clubEl ? clubEl.value : '';
    var dateRange = dateRangeEl ? dateRangeEl.value : '';

    var qs = buildQueryString({ session_id: sessionId, club: clubFilter, date_range: dateRange });

    // Show loading state
    var chartIds = ['chart-carry-distribution','chart-dispersion','chart-spin',
                    'chart-loft-trend','chart-shot-shape','chart-club-comparison'];

    Promise.all([
        fetch('/api/analytics/carry-distribution' + qs).then(handleResponse),
        fetch('/api/analytics/dispersion' + qs).then(handleResponse),
        fetch('/api/analytics/spin-carry' + qs).then(handleResponse),
        fetch('/api/analytics/loft-trend' + qs).then(handleResponse),
        fetch('/api/analytics/shot-shape' + qs).then(handleResponse),
        fetch('/api/analytics/club-comparison' + qs).then(handleResponse),
    ]).then(function (results) {
        initCarryDistribution(results[0]);
        initDispersionChart(results[1]);
        initSpinChart(results[2]);
        initLoftTrend(results[3]);
        initShotShape(results[4]);
        initClubComparison(results[5]);
    }).catch(function (err) {
        console.error('Analytics load error:', err);
    });

    // Wire up the refresh button
    var refreshBtn = document.getElementById('analytics-refresh');
    if (refreshBtn) {
        refreshBtn.onclick = loadAnalytics;
    }
}

function handleResponse(response) {
    if (!response.ok) return {};
    return response.json();
}

function buildQueryString(params) {
    var parts = [];
    for (var key in params) {
        if (params[key]) {
            parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(params[key]));
        }
    }
    return parts.length ? '?' + parts.join('&') : '';
}

/* ---------- Carry Distance Distribution ---------- */
function initCarryDistribution(data) {
    var canvas = document.getElementById('chart-carry-distribution');
    if (!canvas || !data || typeof data !== 'object') return;
    destroyChart('carry-distribution');

    // Backend returns {club: {values, min, q1, median, q3, max, count}}
    var labels = Object.keys(data);
    if (!labels.length) return;

    var medianData = labels.map(function (c) { return data[c].median || 0; });
    var q1Data = labels.map(function (c) { return data[c].q1 || 0; });
    var q3Data = labels.map(function (c) { return data[c].q3 || 0; });

    chartInstances['carry-distribution'] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'P25',
                    data: q1Data,
                    backgroundColor: 'rgba(45, 106, 79, 0.3)',
                    borderColor: 'rgba(45, 106, 79, 0.5)',
                    borderWidth: 1,
                },
                {
                    label: 'Median',
                    data: medianData,
                    backgroundColor: GOLF_COLORS.green,
                    borderColor: 'rgba(45, 106, 79, 1)',
                    borderWidth: 1,
                },
                {
                    label: 'P75',
                    data: q3Data,
                    backgroundColor: GOLF_COLORS.greenLight,
                    borderColor: 'rgba(64, 145, 108, 1)',
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: { mode: 'index' },
            },
            scales: {
                x: { title: { display: true, text: 'Club' } },
                y: { title: { display: true, text: 'Carry (yards)' }, beginAtZero: false },
            },
        },
    });
}

/* ---------- Dispersion Pattern ---------- */
function initDispersionChart(data) {
    var canvas = document.getElementById('chart-dispersion');
    if (!canvas) return;
    destroyChart('dispersion');

    // Handle both array and empty object
    var items = Array.isArray(data) ? data : [];
    if (!items.length) return;

    var clubMap = {};
    items.forEach(function (d) {
        var club = d.club || d.club_short;
        if (!clubMap[club]) clubMap[club] = [];
        clubMap[club].push({ x: d.offline, y: d.carry });
    });

    var datasets = Object.keys(clubMap).map(function (club, i) {
        return {
            label: club,
            data: clubMap[club],
            backgroundColor: CLUB_PALETTE[i % CLUB_PALETTE.length],
            pointRadius: 4,
            pointHoverRadius: 6,
        };
    });

    chartInstances['dispersion'] = new Chart(canvas, {
        type: 'scatter',
        data: { datasets: datasets },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return ctx.dataset.label + ': ' +
                                   ctx.parsed.y + 'yd carry, ' +
                                   ctx.parsed.x + 'yd offline';
                        },
                    },
                },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Offline (yards) \u2190 Left | Right \u2192' },
                    grid: { color: 'rgba(0,0,0,0.05)' },
                },
                y: {
                    title: { display: true, text: 'Carry (yards)' },
                    beginAtZero: false,
                },
            },
        },
    });
}

/* ---------- Spin Rate vs Carry ---------- */
function initSpinChart(data) {
    var canvas = document.getElementById('chart-spin');
    if (!canvas) return;
    destroyChart('spin');

    var items = Array.isArray(data) ? data : [];
    if (!items.length) return;

    var clubMap = {};
    items.forEach(function (d) {
        var club = d.club || d.club_short;
        if (!clubMap[club]) clubMap[club] = [];
        clubMap[club].push({ x: d.carry, y: d.spin_rate });
    });

    var datasets = Object.keys(clubMap).map(function (club, i) {
        return {
            label: club,
            data: clubMap[club],
            backgroundColor: CLUB_PALETTE[i % CLUB_PALETTE.length],
            pointRadius: 4,
            pointHoverRadius: 6,
        };
    });

    chartInstances['spin'] = new Chart(canvas, {
        type: 'scatter',
        data: { datasets: datasets },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return ctx.dataset.label + ': ' +
                                   ctx.parsed.x + 'yd, ' +
                                   ctx.parsed.y + ' rpm';
                        },
                    },
                },
            },
            scales: {
                x: { title: { display: true, text: 'Carry (yards)' } },
                y: { title: { display: true, text: 'Spin Rate (rpm)' }, beginAtZero: false },
            },
        },
    });
}

/* ---------- Dynamic Loft Trend ---------- */
function initLoftTrend(data) {
    var canvas = document.getElementById('chart-loft-trend');
    if (!canvas) return;
    destroyChart('loft-trend');

    // Backend returns [{id, club_short, dynamic_loft, standard_loft, loft_diff, status}]
    var items = Array.isArray(data) ? data : [];
    if (!items.length) return;

    var clubMap = {};
    items.forEach(function (d) {
        var club = d.club || d.club_short;
        if (d.dynamic_loft != null) {
            if (!clubMap[club]) clubMap[club] = [];
            clubMap[club].push(d.dynamic_loft);
        }
    });

    var maxLen = Math.max.apply(null, Object.values(clubMap).map(function (a) { return a.length; }));
    var labels = Array.from({ length: maxLen }, function (_, i) { return 'Shot ' + (i + 1); });

    var datasets = Object.keys(clubMap).map(function (club, i) {
        return {
            label: club,
            data: clubMap[club],
            borderColor: CLUB_PALETTE[i % CLUB_PALETTE.length],
            backgroundColor: 'transparent',
            borderWidth: 2,
            tension: 0.3,
            pointRadius: 3,
        };
    });

    chartInstances['loft-trend'] = new Chart(canvas, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: {
            responsive: true,
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { title: { display: true, text: 'Shot Number' } },
                y: { title: { display: true, text: 'Dynamic Loft (\u00b0)' } },
            },
        },
    });
}

/* ---------- Shot Shape Analysis ---------- */
function initShotShape(data) {
    var canvas = document.getElementById('chart-shot-shape');
    if (!canvas) return;
    destroyChart('shot-shape');

    var items = Array.isArray(data) ? data : [];
    if (!items.length) return;

    var points = items.map(function (d) {
        return { x: d.club_path, y: d.face_angle };
    });

    chartInstances['shot-shape'] = new Chart(canvas, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Shots',
                data: points,
                backgroundColor: GOLF_COLORS.green,
                pointRadius: 5,
                pointHoverRadius: 7,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            var diff = ctx.parsed.y - ctx.parsed.x;
                            var shape = diff > 1 ? 'Fade/Slice' :
                                        diff < -1 ? 'Draw/Hook' : 'Straight';
                            return 'Path: ' + ctx.parsed.x + '\u00b0, Face: ' +
                                   ctx.parsed.y + '\u00b0 \u2192 ' + shape;
                        },
                    },
                },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Club Path (\u00b0) \u2190 In-to-out | Out-to-in \u2192' },
                    grid: { color: 'rgba(0,0,0,0.05)' },
                },
                y: {
                    title: { display: true, text: 'Face Angle (\u00b0) \u2190 Closed | Open \u2192' },
                    grid: { color: 'rgba(0,0,0,0.05)' },
                },
            },
        },
        plugins: [{
            id: 'crosshairs',
            afterDraw: function (chart) {
                var ctx = chart.ctx;
                var xAxis = chart.scales.x;
                var yAxis = chart.scales.y;
                var xZero = xAxis.getPixelForValue(0);
                var yZero = yAxis.getPixelForValue(0);

                ctx.save();
                ctx.strokeStyle = 'rgba(0, 0, 0, 0.15)';
                ctx.lineWidth = 1;
                ctx.setLineDash([5, 5]);

                ctx.beginPath();
                ctx.moveTo(xZero, yAxis.top);
                ctx.lineTo(xZero, yAxis.bottom);
                ctx.stroke();

                ctx.beginPath();
                ctx.moveTo(xAxis.left, yZero);
                ctx.lineTo(xAxis.right, yZero);
                ctx.stroke();

                ctx.restore();
            },
        }],
    });
}

/* ---------- Club Comparison ---------- */
function initClubComparison(data) {
    var canvas = document.getElementById('chart-club-comparison');
    if (!canvas) return;
    destroyChart('club-comparison');

    var items = Array.isArray(data) ? data : [];
    if (!items.length) return;

    var labels = items.map(function (d) { return d.club; });

    chartInstances['club-comparison'] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Carry (P75)',
                    data: items.map(function (d) { return d.carry_p75; }),
                    backgroundColor: GOLF_COLORS.green,
                    borderColor: 'rgba(45, 106, 79, 1)',
                    borderWidth: 1,
                },
                {
                    label: 'Total (P75)',
                    data: items.map(function (d) { return d.total_p75; }),
                    backgroundColor: GOLF_COLORS.blue,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1,
                },
                {
                    label: 'Max Total',
                    data: items.map(function (d) { return d.max_total; }),
                    backgroundColor: GOLF_COLORS.orange,
                    borderColor: 'rgba(255, 159, 64, 1)',
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { title: { display: true, text: 'Club' } },
                y: { title: { display: true, text: 'Distance (yards)' }, beginAtZero: false },
            },
        },
    });
}