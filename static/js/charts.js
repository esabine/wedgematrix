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

// Canonical club ordering: longest → shortest, wedge sub-swings grouped by swing type
var CANONICAL_CLUB_ORDER = [
    '1W', '3W', '2H', '3H', '4H', '3i', '4i', '5i', '6i', '7i', '8i', '9i',
    'PW', 'PW-Full', 'AW', 'AW-Full', 'SW', 'SW-Full', 'LW', 'LW-Full',
    'PW-3/3', 'AW-3/3', 'SW-3/3', 'LW-3/3',
    'PW-2/3', 'AW-2/3', 'SW-2/3', 'LW-2/3',
    'PW-1/3', 'AW-1/3', 'SW-1/3', 'LW-1/3',
    'PW-10:2', 'AW-10:2', 'SW-10:2', 'LW-10:2',
    'PW-10:3', 'AW-10:3', 'SW-10:3', 'LW-10:3',
    'PW-9:3', 'AW-9:3', 'SW-9:3', 'LW-9:3',
    'PW-8:4', 'AW-8:4', 'SW-8:4', 'LW-8:4',
];

// Build index once for O(1) lookup
var _CLUB_ORDER_MAP = {};
CANONICAL_CLUB_ORDER.forEach(function (c, i) { _CLUB_ORDER_MAP[c] = i; });

// Return a consistent color for a club name across ALL charts
function getClubColor(club) {
    var idx = _CLUB_ORDER_MAP[club];
    if (idx === undefined) idx = CANONICAL_CLUB_ORDER.length;
    return CLUB_PALETTE[idx % CLUB_PALETTE.length];
}

function sortByCanonicalOrder(clubs) {
    return clubs.slice().sort(function (a, b) {
        var posA = _CLUB_ORDER_MAP[a] !== undefined ? _CLUB_ORDER_MAP[a] : 9999;
        var posB = _CLUB_ORDER_MAP[b] !== undefined ? _CLUB_ORDER_MAP[b] : 9999;
        if (posA !== posB) return posA - posB;
        return a.localeCompare(b);
    });
}

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
    var labels = sortByCanonicalOrder(Object.keys(data));
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
                    backgroundColor: labels.map(function (c) {
                        return getClubColor(c);
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
                            var lines = [];
                            // Gap to shorter club (stored on this club)
                            if (gaps[idx] != null) {
                                var gNext = gaps[idx];
                                var warn = gNext > 20 ? ' \u26a0 too large' : (gNext < 5 ? ' \u26a0 too small' : '');
                                lines.push('Gap to next club: ' + gNext + 'yd' + warn);
                            }
                            // Gap from longer club (stored on previous club)
                            if (idx > 0 && gaps[idx - 1] != null) {
                                var gPrev = gaps[idx - 1];
                                var warn2 = gPrev > 20 ? ' \u26a0 too large' : (gPrev < 5 ? ' \u26a0 too small' : '');
                                lines.push('Gap from prev club: ' + gPrev + 'yd' + warn2);
                            }
                            return lines.join('\n');
                        },
                    },
                },
            },
            scales: {
                x: { title: { display: true, text: 'Club' } },
                y: { title: { display: true, text: 'Carry (yards)' }, beginAtZero: false,
                     grace: '15%' },
            },
            layout: { padding: { top: 10 } },
        },
        plugins: [{
            id: 'gapAnnotations',
            afterDraw: function (chart) {
                var ctx = chart.ctx;
                var meta = chart.getDatasetMeta(0);
                ctx.save();
                ctx.font = 'bold 10px "Segoe UI", Arial, sans-serif';
                ctx.textAlign = 'center';

                for (var i = 1; i < gaps.length; i++) {
                    var g = gaps[i - 1];
                    if (g === null || g === undefined) continue;

                    var bar = meta.data[i];
                    var prevBar = meta.data[i - 1];
                    if (!bar || !prevBar) continue;

                    // Position badge centered between the two bars it connects
                    var midX = (prevBar.x + bar.x) / 2;
                    var higherY = Math.min(prevBar.y, bar.y);
                    var badgeY = higherY - 22;
                    var text = g + 'yd';
                    var tw = ctx.measureText(text).width + 10;
                    var badgeH = 16;
                    var badgeR = 8;

                    // Badge pill background
                    ctx.fillStyle = gapColor(g);
                    ctx.beginPath();
                    ctx.roundRect(midX - tw / 2, badgeY - badgeH / 2, tw, badgeH, badgeR);
                    ctx.fill();

                    // Badge text
                    ctx.fillStyle = '#fff';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(text, midX, badgeY);

                    // Bracket: thin lines from badge down to each bar top
                    ctx.strokeStyle = gapBorderColor(g);
                    ctx.lineWidth = 1;
                    ctx.setLineDash([]);
                    ctx.beginPath();
                    ctx.moveTo(midX - tw / 2 + 4, badgeY + badgeH / 2);
                    ctx.lineTo(prevBar.x, prevBar.y - 2);
                    ctx.moveTo(midX + tw / 2 - 4, badgeY + badgeH / 2);
                    ctx.lineTo(bar.x, bar.y - 2);
                    ctx.stroke();
                }
                ctx.restore();
            },
        }],
    });
}

/* ---------- Dispersion Pattern ---------- */
// Plugin: draw a dotted vertical "Target" line at x=0
var dispersionTargetLine = {
    id: 'dispersionTargetLine',
    afterDraw: function (chart) {
        var xScale = chart.scales.x;
        if (!xScale) return;
        var xPixel = xScale.getPixelForValue(0);
        if (xPixel < xScale.left || xPixel > xScale.right) return;

        var ctx = chart.ctx;
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = 'rgba(108, 117, 125, 0.6)';
        ctx.lineWidth = 1.5;
        ctx.moveTo(xPixel, chart.scales.y.top);
        ctx.lineTo(xPixel, chart.scales.y.bottom);
        ctx.stroke();

        // Label near top
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(108, 117, 125, 0.7)';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('Target', xPixel + 4, chart.scales.y.top + 12);
        ctx.restore();
    },
};

// Plugin: concentric distance arcs (driving-range rings) behind scatter dots
var dispersionConcentricArcs = {
    id: 'dispersionConcentricArcs',
    beforeDatasetsDraw: function (chart) {
        var xScale = chart.scales.x;
        var yScale = chart.scales.y;
        if (!xScale || !yScale) return;

        var ctx = chart.ctx;
        var area = chart.chartArea;
        ctx.save();
        ctx.beginPath();
        ctx.rect(area.left, area.top, area.right - area.left, area.bottom - area.top);
        ctx.clip();

        // Choose arc interval based on y-axis range
        var yMax = yScale.max;
        var step = 50;
        if (yMax > 500) step = 100;
        else if (yMax < 80) step = 25;

        // Golfer origin in pixel space: offline=0, carry=0
        var originPx = xScale.getPixelForValue(0);
        var originPy = yScale.getPixelForValue(0);

        var xMin = xScale.min;
        var xMax = xScale.max;
        var arcSteps = 120;

        ctx.setLineDash([3, 4]);
        ctx.lineWidth = 0.8;

        for (var carry = step; carry <= yMax + step; carry += step) {
            // Arc: all points at distance `carry` from golfer (0,0)
            // carry_at_x = sqrt(carry² - x²)
            ctx.strokeStyle = 'rgba(45, 106, 79, 0.18)';
            ctx.beginPath();
            var started = false;

            for (var s = 0; s <= arcSteps; s++) {
                var x = xMin + (xMax - xMin) * (s / arcSteps);
                var rSq = carry * carry - x * x;
                if (rSq < 0) continue;
                var y = Math.sqrt(rSq);
                if (y < yScale.min || y > yScale.max * 1.05) continue;

                var px = xScale.getPixelForValue(x);
                var py = yScale.getPixelForValue(y);

                if (!started) { ctx.moveTo(px, py); started = true; }
                else { ctx.lineTo(px, py); }
            }
            if (started) ctx.stroke();

            // Distance label at center of arc
            var labelY = Math.min(carry, yScale.max);
            if (labelY > yScale.min + 5) {
                var labelPx = xScale.getPixelForValue(0);
                var labelPy = yScale.getPixelForValue(labelY);
                if (labelPy > area.top + 10 && labelPy < area.bottom - 10) {
                    ctx.setLineDash([]);
                    ctx.font = '9px "Segoe UI", sans-serif';
                    ctx.fillStyle = 'rgba(45, 106, 79, 0.4)';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(carry + ' yd', labelPx, labelPy - 3);
                    ctx.setLineDash([3, 4]);
                }
            }
        }

        ctx.restore();
    },
};

function initDispersionChart(data) {
    var canvas = document.getElementById('chart-dispersion');
    if (!canvas) return;
    destroyChart('dispersion');

    // Handle new envelope format {shots: [...], dispersion_boundary: {...}}
    // or legacy flat array format [...]
    var items, boundaries;
    if (data && !Array.isArray(data) && data.shots) {
        items = data.shots;
        boundaries = data.dispersion_boundary || null;
    } else {
        items = Array.isArray(data) ? data : [];
        boundaries = null;
    }
    if (!items.length) return;

    var clubMap = {};
    var clubColorMap = {};
    items.forEach(function (d) {
        var club = d.club || d.club_short;
        if (!clubMap[club]) clubMap[club] = [];
        clubMap[club].push({ x: d.offline, y: d.carry, spin_rate: d.spin_rate, launch_angle: d.launch_angle, ball_speed: d.ball_speed, face_angle: d.face_angle });
    });

    var clubNames = Object.keys(clubMap);
    // Symmetric x-axis: find max absolute offline value
    var maxAbsOffline = 0;
    items.forEach(function (d) {
        var abs = Math.abs(d.offline || 0);
        if (abs > maxAbsOffline) maxAbsOffline = abs;
    });
    var offlineLimit = Math.ceil(maxAbsOffline * 1.1) || 10;

    var datasets = clubNames.map(function (club, i) {
        var color = getClubColor(club);
        clubColorMap[club] = color;
        return {
            label: club,
            data: clubMap[club],
            backgroundColor: color,
            pointRadius: 4,
            pointHoverRadius: 6,
        };
    });

    // P90 dispersion boundary datasets
    var MAX_BOUNDARY_CLUBS = 4;
    if (boundaries && typeof boundaries === 'object') {
        var boundaryClubs = Object.keys(boundaries);
        var showBoundaries = clubNames.length <= MAX_BOUNDARY_CLUBS || clubNames.length === 1;

        if (showBoundaries) {
            var singleClub = clubNames.length === 1;
            boundaryClubs.forEach(function (club) {
                var pts = boundaries[club];
                if (!Array.isArray(pts) || pts.length < 3) return;

                // Close the loop by repeating the first point
                var loopData = pts.map(function (p) {
                    return { x: p.offline, y: p.carry };
                });
                loopData.push({ x: pts[0].offline, y: pts[0].carry });

                // Red for single club, otherwise match club scatter color
                var lineColor = singleClub
                    ? 'rgba(220, 53, 69, 0.7)'
                    : (clubColorMap[club] || 'rgba(108, 117, 125, 0.5)');
                var fillColor = singleClub
                    ? 'rgba(220, 53, 69, 0.12)'
                    : lineColor.replace(/[\d.]+\)$/, '0.12)');

                datasets.push({
                    label: club + ' P90',
                    data: loopData,
                    showLine: true,
                    borderColor: lineColor,
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    backgroundColor: fillColor,
                    fill: true,
                    pointRadius: 0,
                    pointHitRadius: 0,
                    tension: 0.3,
                });
            });
        }
    }

    chartInstances['dispersion'] = new Chart(canvas, {
        type: 'scatter',
        data: { datasets: datasets },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        filter: function (item) {
                            // Hide boundary datasets from legend to reduce clutter
                            return !item.text.endsWith(' P90');
                        },
                    },
                },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            if (ctx.dataset.label.endsWith(' P90')) return null;
                            var r = ctx.raw;
                            var lines = [ctx.dataset.label + ': ' +
                                   ctx.parsed.y + 'yd carry, ' +
                                   ctx.parsed.x + 'yd offline'];
                            if (r.ball_speed != null) lines.push('Ball Speed: ' + r.ball_speed + ' mph');
                            if (r.launch_angle != null) lines.push('Launch: ' + r.launch_angle + '°');
                            if (r.spin_rate != null) lines.push('Spin: ' + r.spin_rate + ' rpm');
                            if (r.face_angle != null) lines.push('Face Angle: ' + r.face_angle + '°');
                            return lines;
                        },
                    },
                    filter: function (item) {
                        return !item.dataset.label.endsWith(' P90');
                    },
                },
            },
            scales: {
                x: {
                    title: { display: true, text: ['\u2190 Left | Right \u2192', 'Offline (Yards)'] },
                    min: -offlineLimit,
                    max: offlineLimit,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                },
                y: {
                    title: { display: true, text: 'Carry (yards)' },
                    min: 0,
                    grid: { display: false },
                },
            },
        },
        plugins: [dispersionConcentricArcs, dispersionTargetLine],
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

    var datasets = Object.keys(clubMap).map(function (club) {
        return {
            label: club,
            data: clubMap[club],
            backgroundColor: getClubColor(club),
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

    // Group shots by club for per-club datasets and colored tooltips
    var clubMap = {};
    items.forEach(function (d) {
        var club = d.club || d.club_short || 'Unknown';
        if (!clubMap[club]) clubMap[club] = [];
        clubMap[club].push({ x: d.club_path, y: d.face_angle });
    });

    var datasets = Object.keys(clubMap).map(function (club) {
        return {
            label: club,
            data: clubMap[club],
            backgroundColor: getClubColor(club),
            pointRadius: 5,
            pointHoverRadius: 7,
        };
    });

    chartInstances['shot-shape'] = new Chart(canvas, {
        type: 'scatter',
        data: { datasets: datasets },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            var diff = ctx.parsed.y - ctx.parsed.x;
                            var shape = diff > 1 ? 'Fade/Slice' :
                                        diff < -1 ? 'Draw/Hook' : 'Straight';
                            return ctx.dataset.label + ': Path ' + ctx.parsed.x + '\u00b0, Face ' +
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

    // Sort by canonical club order
    var orderedClubs = sortByCanonicalOrder(items.map(function (d) { return d.club; }));
    var itemMap = {};
    items.forEach(function (d) { itemMap[d.club] = d; });
    items = orderedClubs.map(function (c) { return itemMap[c]; }).filter(Boolean);

    var labels = items.map(function (d) { return d.club; });
    var boxData = items.map(function (d) {
        return {
            min: d.min,
            q1: d.q1,
            median: d.median,
            q3: d.q3,
            max: d.max,
            mean: d.mean,
            outliers: d.outliers || [],
        };
    });

    chartInstances['club-comparison'] = new Chart(canvas, {
        type: 'boxplot',
        data: {
            labels: labels,
            datasets: [{
                label: 'Carry Distance',
                data: boxData,
                backgroundColor: 'rgba(45, 106, 79, 0.3)',
                borderColor: GOLF_COLORS.green,
                borderWidth: 1,
                outlierBackgroundColor: GOLF_COLORS.orange,
                meanBackgroundColor: GOLF_COLORS.blue,
                meanBorderColor: GOLF_COLORS.blue,
                meanRadius: 3,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            var d = items[ctx.dataIndex];
                            return [
                                'Median: ' + d.median + ' yd',
                                'Mean: ' + d.mean + ' yd',
                                'Q1–Q3: ' + d.q1 + '–' + d.q3 + ' yd',
                                'Range: ' + d.min + '–' + d.max + ' yd',
                                'Shots: ' + (d.count || d.shot_count || ''),
                            ];
                        },
                    },
                },
            },
            scales: {
                x: { title: { display: true, text: 'Club' } },
                y: { title: { display: true, text: 'Carry (yards)' }, beginAtZero: false },
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

    // Sort clubs by canonical order
    var clubs = sortByCanonicalOrder(Object.keys(data.clubs));
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

    if (!data || !data.axes || !data.user || !data.pga) return;

    // Populate club dropdown
    var select = document.getElementById('radar-club-select');
    if (select && data.per_club) {
        // Keep "All Clubs" option, remove old club options
        while (select.options.length > 1) select.remove(1);
        var clubs = data.clubs_used || Object.keys(data.per_club);
        clubs.forEach(function (club) {
            var opt = document.createElement('option');
            opt.value = club;
            opt.textContent = club;
            select.appendChild(opt);
        });
        select.onchange = function () { renderRadar(select.value); };
    }

    function renderRadar(clubKey) {
        destroyChart('radar-comparison');
        var axes, userVals, pgaVals, userRaw, pgaRaw;

        if (clubKey === 'all' || !data.per_club || !data.per_club[clubKey]) {
            axes = data.axes;
            userVals = data.user.values || [];
            pgaVals = data.pga.values || [];
            userRaw = data.user.raw || {};
            pgaRaw = data.pga.raw || {};
        } else {
            var pc = data.per_club[clubKey];
            axes = data.axes;
            userVals = pc.user || [];
            pgaVals = pc.pga || [];
            userRaw = {};
            pgaRaw = {};
        }

        chartInstances['radar-comparison'] = new Chart(canvas, {
            type: 'radar',
            data: {
                labels: axes,
                datasets: [
                    {
                        label: clubKey === 'all' ? 'My Shots' : clubKey,
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

    renderRadar('all');
}

/* ---------- PGA Tour Average Reference Table ---------- */
function loadPGAAverages() {
    var tbody = document.getElementById('pga-averages-body');
    if (!tbody) return;

    fetch('/api/analytics/pga-averages')
        .then(handleResponse)
        .then(function (data) {
            if (!data || !data.clubs || !data.clubs.length) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No PGA Tour data available</td></tr>';
                return;
            }
            tbody.innerHTML = data.clubs.map(function (c) {
                return '<tr>' +
                    '<td class="fw-semibold">' + (c.club || '') + '</td>' +
                    '<td>' + (c.carry != null ? c.carry : '–') + '</td>' +
                    '<td>' + (c.spin_rate != null ? c.spin_rate.toLocaleString() : '–') + '</td>' +
                    '<td>' + (c.launch_angle != null ? c.launch_angle : '–') + '</td>' +
                    '<td>' + (c.ball_speed != null ? c.ball_speed : '–') + '</td>' +
                    '<td>' + (c.dispersion != null ? c.dispersion : '–') + '</td>' +
                    '</tr>';
            }).join('');
        })
        .catch(function () {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Failed to load PGA Tour data</td></tr>';
        });
}