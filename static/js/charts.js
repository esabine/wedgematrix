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
    var percentileEl = document.getElementById('analytics-percentile');
    var sessionId = sessionEl ? sessionEl.value : '';
    var clubFilter = clubEl ? clubEl.value : '';
    var dateRange = dateRangeEl ? dateRangeEl.value : '';
    var percentile = percentileEl ? percentileEl.value : '';

    var qs = buildQueryString({ session_id: sessionId, club: clubFilter, date_range: dateRange, percentile: percentile });

    // Show loading state
    Promise.all([
        fetch('/api/analytics/carry-distribution' + qs).then(handleResponse),
        fetch('/api/analytics/dispersion' + qs).then(handleResponse),
        fetch('/api/analytics/spin-carry' + qs).then(handleResponse),
        fetch('/api/analytics/shot-shape' + qs).then(handleResponse),
        fetch('/api/analytics/club-comparison' + qs).then(handleResponse),
        fetch('/api/analytics/launch-spin-stability' + qs).then(handleResponse),
        fetch('/api/analytics/radar-comparison' + qs).then(handleResponse),
    ]).then(function (results) {
        initCarryDistribution(results[0]);
        initDispersionChart(results[1]);
        initSpinChart(results[2]);
        initShotShape(results[3]);
        initClubComparison(results[4]);
        initLaunchSpinStability(results[5]);
        initRadarComparison(results[6]);
    }).catch(function (err) {
        console.error('Analytics load error:', err);
    });
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

/* ---------- Carry Distance Distribution (with Gapping) ---------- */
function initCarryDistribution(data) {
    var canvas = document.getElementById('chart-carry-distribution');
    if (!canvas || !data || typeof data !== 'object') return;
    destroyChart('carry-distribution');

    // Backend returns {club: {values, min, q1, median, q3, max, count, gap}}
    var labels = Object.keys(data);
    if (!labels.length) return;

    var medianData = labels.map(function (c) { return data[c].median || 0; });
    var pLabel = data[labels[0]] && data[labels[0]].percentile ?
                 'P' + data[labels[0]].percentile : 'P75';
    var pData = labels.map(function (c) { return data[c].q3 || data[c].median || 0; });

    // Compute gaps between adjacent clubs (longer club to shorter club)
    var gaps = labels.map(function (c) { return data[c].gap != null ? data[c].gap : null; });

    // Gap colors: red if >20yd, amber if <5yd, green otherwise
    function gapColor(g) {
        if (g === null || g === undefined) return 'transparent';
        if (g > 20) return 'rgba(220, 53, 69, 0.85)';
        if (g < 5) return 'rgba(255, 193, 7, 0.85)';
        return 'rgba(45, 106, 79, 0.7)';
    }

    function gapBorderColor(g) {
        if (g === null || g === undefined) return 'transparent';
        if (g > 20) return 'rgba(220, 53, 69, 1)';
        if (g < 5) return 'rgba(255, 193, 7, 1)';
        return 'rgba(45, 106, 79, 1)';
    }

    chartInstances['carry-distribution'] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Carry (' + pLabel + ')',
                    data: pData,
                    backgroundColor: labels.map(function (_, i) {
                        return CLUB_PALETTE[i % CLUB_PALETTE.length];
                    }),
                    borderColor: 'rgba(45, 106, 79, 1)',
                    borderWidth: 1,
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        afterLabel: function (ctx) {
                            var idx = ctx.dataIndex;
                            var g = gaps[idx];
                            if (g !== null && g !== undefined) {
                                var warning = g > 20 ? ' ⚠ too large' : (g < 5 ? ' ⚠ too small' : '');
                                return 'Gap from prev: ' + g + 'yd' + warning;
                            }
                            return '';
                        },
                    },
                },
            },
            scales: {
                x: { title: { display: true, text: 'Club' } },
                y: { title: { display: true, text: 'Carry (yards)' }, beginAtZero: false },
            },
        },
        plugins: [{
            id: 'gapAnnotations',
            afterDraw: function (chart) {
                var ctx = chart.ctx;
                var meta = chart.getDatasetMeta(0);
                ctx.save();
                ctx.font = 'bold 11px "Segoe UI", Arial, sans-serif';
                ctx.textAlign = 'center';

                for (var i = 0; i < gaps.length; i++) {
                    var g = gaps[i];
                    if (g === null || g === undefined) continue;

                    var bar = meta.data[i];
                    if (!bar) continue;

                    // Draw gap badge above the bar
                    var x = bar.x;
                    var y = bar.y - 8;
                    var text = g + 'yd';
                    var tw = ctx.measureText(text).width + 8;

                    // Badge background
                    ctx.fillStyle = gapColor(g);
                    ctx.beginPath();
                    ctx.roundRect(x - tw / 2, y - 14, tw, 17, 3);
                    ctx.fill();

                    // Badge text
                    ctx.fillStyle = '#fff';
                    ctx.fillText(text, x, y - 1);

                    // Connector line between adjacent bars
                    if (i > 0 && meta.data[i - 1]) {
                        var prevBar = meta.data[i - 1];
                        ctx.strokeStyle = gapBorderColor(g);
                        ctx.lineWidth = 1.5;
                        ctx.setLineDash([3, 3]);
                        ctx.beginPath();
                        ctx.moveTo(prevBar.x, prevBar.y);
                        ctx.lineTo(bar.x, bar.y);
                        ctx.stroke();
                        ctx.setLineDash([]);
                    }
                }
                ctx.restore();
            },
        }],
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
                    min: 0,
                },
            },
        },
    });
}

/* ---------- Spin Rate vs Roll Distance ---------- */
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
        clubMap[club].push({ x: d.roll, y: d.spin_rate });
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
                                   ctx.parsed.x + 'yd roll, ' +
                                   ctx.parsed.y + ' rpm';
                        },
                    },
                },
            },
            scales: {
                x: { title: { display: true, text: 'Roll Distance (yards)' } },
                y: { title: { display: true, text: 'Spin Rate (rpm)' }, beginAtZero: false },
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
    var pLabel = 'P' + (document.getElementById('analytics-percentile') ?
                        document.getElementById('analytics-percentile').value : '75');

    chartInstances['club-comparison'] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Carry (' + pLabel + ')',
                    data: items.map(function (d) { return d.carry_p75; }),
                    backgroundColor: GOLF_COLORS.green,
                    borderColor: 'rgba(45, 106, 79, 1)',
                    borderWidth: 1,
                },
                {
                    label: 'Total (' + pLabel + ')',
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

/* ---------- Launch-Spin Stability Box Plot ---------- */
function initLaunchSpinStability(data) {
    var canvas = document.getElementById('chart-launch-spin-stability');
    var notesEl = document.getElementById('launch-spin-notes');
    if (!canvas) return;
    destroyChart('launch-spin-stability');

    // Expected: { clubs: { "7I": { spin: {min,q1,median,q3,max,mean,std}, launch: {...}, high_variance: bool, analysis: str }, ... }, correlation: str }
    if (!data || !data.clubs) {
        if (notesEl) notesEl.textContent = '';
        return;
    }

    var clubs = Object.keys(data.clubs);
    if (!clubs.length) return;

    // Build box plot items for spin and launch
    var spinItems = clubs.map(function (c) {
        var s = data.clubs[c].spin || {};
        return { min: s.min, q1: s.q1, median: s.median, q3: s.q3, max: s.max, mean: s.mean };
    });

    var launchItems = clubs.map(function (c) {
        var l = data.clubs[c].launch || {};
        return { min: l.min, q1: l.q1, median: l.median, q3: l.q3, max: l.max, mean: l.mean };
    });

    // High-variance club indicators
    var highVarClubs = clubs.filter(function (c) { return data.clubs[c].high_variance; });

    // Color labels for high-variance clubs
    var labelColors = clubs.map(function (c) {
        return data.clubs[c].high_variance ? 'rgba(220, 53, 69, 1)' : '#666';
    });

    // Use side-by-side box plot (Chart.js boxplot plugin)
    chartInstances['launch-spin-stability'] = new Chart(canvas, {
        type: 'boxplot',
        data: {
            labels: clubs,
            datasets: [
                {
                    label: 'Spin Rate (rpm)',
                    data: spinItems,
                    backgroundColor: 'rgba(45, 106, 79, 0.3)',
                    borderColor: GOLF_COLORS.green,
                    borderWidth: 2,
                    medianColor: 'rgba(45, 106, 79, 1)',
                    outlierBackgroundColor: GOLF_COLORS.red,
                },
                {
                    label: 'Launch Angle (\u00b0)',
                    data: launchItems,
                    backgroundColor: 'rgba(54, 162, 235, 0.3)',
                    borderColor: GOLF_COLORS.blue,
                    borderWidth: 2,
                    medianColor: 'rgba(54, 162, 235, 1)',
                    outlierBackgroundColor: GOLF_COLORS.orange,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            var d = ctx.raw;
                            if (!d) return '';
                            return ctx.dataset.label + ': med=' + (d.median || 0).toFixed(1) +
                                   ', IQR=[' + (d.q1 || 0).toFixed(1) + '-' + (d.q3 || 0).toFixed(1) + ']';
                        },
                    },
                },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Club' },
                    ticks: {
                        color: labelColors,
                        font: function (ctx) {
                            var idx = ctx.index;
                            if (idx !== undefined && clubs[idx] && data.clubs[clubs[idx]] && data.clubs[clubs[idx]].high_variance) {
                                return { weight: 'bold' };
                            }
                            return {};
                        },
                    },
                },
                y: { title: { display: true, text: 'Value' }, beginAtZero: false },
            },
        },
        plugins: [{
            id: 'highVarianceBadge',
            afterDraw: function (chart) {
                if (!highVarClubs.length) return;
                var ctx = chart.ctx;
                var xAxis = chart.scales.x;
                var yAxis = chart.scales.y;
                ctx.save();
                ctx.font = 'bold 9px "Segoe UI", Arial, sans-serif';
                ctx.textAlign = 'center';

                clubs.forEach(function (c, i) {
                    if (!data.clubs[c].high_variance) return;
                    var x = xAxis.getPixelForValue(i);
                    var y = yAxis.top - 4;
                    ctx.fillStyle = 'rgba(220, 53, 69, 0.85)';
                    var tw = ctx.measureText('\u26a0 HIGH VAR').width + 6;
                    ctx.beginPath();
                    ctx.roundRect(x - tw / 2, y - 12, tw, 14, 2);
                    ctx.fill();
                    ctx.fillStyle = '#fff';
                    ctx.fillText('\u26a0 HIGH VAR', x, y - 1);
                });
                ctx.restore();
            },
        }],
    });

    // Correlation analysis note
    if (notesEl) {
        var notes = [];
        if (data.correlation) notes.push(data.correlation);
        highVarClubs.forEach(function (c) {
            var analysis = data.clubs[c].analysis;
            if (analysis) notes.push(c + ': ' + analysis);
        });
        notesEl.textContent = notes.join(' | ') || '';
    }
}

/* ---------- Radar: User vs PGA Tour Average ---------- */
function initRadarComparison(data) {
    var canvas = document.getElementById('chart-radar-comparison');
    if (!canvas) return;
    destroyChart('radar-comparison');

    // Expected: { axes: ['Carry','Dispersion','Smash Factor','Spin Rate','Launch Angle','Ball Speed'],
    //             user: { values: [70,55,80,60,75,65], raw: {Carry: 155, ...} },
    //             pga:  { values: [85,75,90,80,85,80], raw: {Carry: 275, ...} } }
    if (!data || !data.axes || !data.user || !data.pga) return;

    var axes = data.axes;
    var userVals = data.user.values || [];
    var pgaVals = data.pga.values || [];
    var userRaw = data.user.raw || {};
    var pgaRaw = data.pga.raw || {};

    chartInstances['radar-comparison'] = new Chart(canvas, {
        type: 'radar',
        data: {
            labels: axes,
            datasets: [
                {
                    label: 'My Shots',
                    data: userVals,
                    backgroundColor: 'rgba(45, 106, 79, 0.2)',
                    borderColor: 'rgba(45, 106, 79, 0.9)',
                    borderWidth: 2,
                    pointBackgroundColor: 'rgba(45, 106, 79, 1)',
                    pointRadius: 4,
                    fill: true,
                },
                {
                    label: 'PGA Tour Avg',
                    data: pgaVals,
                    backgroundColor: 'rgba(108, 117, 125, 0.05)',
                    borderColor: 'rgba(108, 117, 125, 0.6)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointBackgroundColor: 'rgba(108, 117, 125, 0.8)',
                    pointRadius: 3,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            var axis = axes[ctx.dataIndex];
                            var percentile = ctx.parsed.r;
                            var isUser = ctx.datasetIndex === 0;
                            var raw = isUser ? userRaw[axis] : pgaRaw[axis];
                            var label = ctx.dataset.label + ': ' + percentile + '/100';
                            if (raw !== undefined && raw !== null) {
                                label += ' (actual: ' + raw + ')';
                            }
                            return label;
                        },
                    },
                },
            },
            scales: {
                r: {
                    min: 0,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        backdropColor: 'transparent',
                        color: '#999',
                        font: { size: 10 },
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.08)' },
                    angleLines: { color: 'rgba(0, 0, 0, 0.08)' },
                    pointLabels: {
                        font: { size: 12, weight: 'bold' },
                        color: '#333',
                    },
                },
            },
        },
    });
}