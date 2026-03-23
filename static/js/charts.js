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
    // Clean up custom event handlers (concentric arc chart)
    if (id === 'carry-distribution') {
        var c = document.getElementById('chart-carry-distribution');
        if (c && c._carryArcHandler) {
            c.removeEventListener('mousemove', c._carryArcHandler);
            c._carryArcHandler = null;
            c.title = '';
        }
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

/* ---------- Carry Distance — Concentric Arc Chart ---------- */
function initCarryDistribution(data) {
    var canvas = document.getElementById('chart-carry-distribution');
    if (!canvas || !data || typeof data !== 'object') return;
    destroyChart('carry-distribution');

    // Backend returns {club: {values, min, q1, median, q3, max, count, gap, percentile}}
    var allClubs = Object.keys(data);
    if (!allClubs.length) return;
    var clubs = sortByCanonicalOrder(allClubs);

    var pLabel = data[clubs[0]] && data[clubs[0]].percentile
        ? 'P' + data[clubs[0]].percentile : 'P75';

    // Build ordered data
    var clubData = clubs.map(function (c) {
        return {
            club: c,
            dist: Math.round(data[c].q3 || data[c].median || 0),
            gap: data[c].gap,
            count: data[c].count || 0,
        };
    });

    // Scale: round max distance up to nearest 50 + buffer
    var maxDist = Math.max.apply(null, clubData.map(function (d) { return d.dist; }));
    var scaleDist = Math.ceil(maxDist / 50) * 50 + 25;

    // Canvas sizing — HiDPI aware
    var container = canvas.parentElement;
    var dpr = window.devicePixelRatio || 1;
    var totalWidth = container.clientWidth || 500;
    var legendW = Math.min(130, Math.max(100, totalWidth * 0.25));
    var arcW = totalWidth - legendW;
    var height = Math.max(300, Math.min(480, totalWidth * 0.6));

    canvas.width = totalWidth * dpr;
    canvas.height = height * dpr;
    canvas.style.width = totalWidth + 'px';
    canvas.style.height = height + 'px';

    var ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    // Geometry: golfer at bottom-center of arc area, arcs open upward
    var cx = arcW / 2;
    var cy = height - 18;
    var maxRadius = Math.min(cy - 22, (arcW / 2) - 6);

    function yardToR(yards) { return (yards / scaleDist) * maxRadius; }

    // 170° arc span centered at 12-o'clock
    var ARC_SPAN = 170 * Math.PI / 180;
    var ARC_START = Math.PI + (Math.PI - ARC_SPAN) / 2;
    var ARC_END = 2 * Math.PI - (Math.PI - ARC_SPAN) / 2;

    // Color by club type
    function clubColor(club) {
        var base = club.split('-')[0];
        if (/W$/.test(base)) return '#66bb6a';
        if (/H$/.test(base)) return '#26c6da';
        if (/i$/.test(base)) return '#42a5f5';
        if (/^PW/.test(club)) return '#ffb74d';
        if (/^AW/.test(club)) return '#ffa726';
        if (/^SW/.test(club)) return '#ef5350';
        if (/^LW/.test(club)) return '#ab47bc';
        return '#9e9e9e';
    }

    // === BACKGROUND ===
    ctx.fillStyle = '#162b22';
    ctx.fillRect(0, 0, totalWidth, height);

    var bgGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxRadius * 1.3);
    bgGrad.addColorStop(0, '#1e3d2f');
    bgGrad.addColorStop(0.7, '#1a3328');
    bgGrad.addColorStop(1, '#162b22');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, arcW, height);

    // === DISTANCE REFERENCE RINGS ===
    ctx.setLineDash([3, 5]);
    for (var d = 25; d <= scaleDist; d += 25) {
        var r = yardToR(d);
        var major = d % 50 === 0;
        ctx.strokeStyle = major ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.08)';
        ctx.lineWidth = major ? 0.8 : 0.5;
        ctx.beginPath();
        ctx.arc(cx, cy, r, ARC_START, ARC_END);
        ctx.stroke();
        if (major) {
            ctx.font = '9px "Segoe UI", sans-serif';
            ctx.fillStyle = 'rgba(255,255,255,0.35)';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';
            ctx.fillText(d + ' yd', cx, cy - r - 3);
        }
    }
    ctx.setLineDash([]);

    // Center / target line
    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx, cy - maxRadius - 10);
    ctx.stroke();

    // === GAP FILLS for problem gaps ===
    for (var gi = 0; gi < clubData.length - 1; gi++) {
        var g = clubData[gi].gap;
        if (g === null || g === undefined) continue;
        var r1 = yardToR(clubData[gi].dist);
        var r2 = yardToR(clubData[gi + 1].dist);
        var fillColor = null;
        if (g > 20) fillColor = 'rgba(220, 53, 69, 0.12)';
        else if (g < 5) fillColor = 'rgba(255, 193, 7, 0.10)';
        if (fillColor) {
            ctx.fillStyle = fillColor;
            ctx.beginPath();
            ctx.arc(cx, cy, r1, ARC_START, ARC_END, false);
            ctx.arc(cx, cy, r2, ARC_END, ARC_START, true);
            ctx.closePath();
            ctx.fill();
        }
    }

    // === CLUB ARCS (draw longest first so shorter arcs layer on top) ===
    var sortedByDist = clubData.slice().sort(function (a, b) { return b.dist - a.dist; });
    sortedByDist.forEach(function (cd) {
        var r = yardToR(cd.dist);
        ctx.beginPath();
        ctx.arc(cx, cy, r, ARC_START, ARC_END);
        ctx.strokeStyle = clubColor(cd.club);
        ctx.lineWidth = 2.5;
        ctx.stroke();
    });

    // Golfer origin marker
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.beginPath();
    ctx.arc(cx, cy, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // === LEGEND (right sidebar) ===
    var legX = arcW + 8;
    var legTopY = 8;

    // Title
    ctx.font = 'bold 11px "Segoe UI", Arial, sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('Carry (' + pLabel + ')', legX, legTopY);

    // Divider
    ctx.strokeStyle = 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(legX, legTopY + 16);
    ctx.lineTo(legX + legendW - 16, legTopY + 16);
    ctx.stroke();

    // Entries — compute spacing to fit all clubs
    var availH = height - legTopY - 30;
    var entryH = Math.min(20, Math.max(13, availH / clubData.length));
    var startY = legTopY + 22;

    clubData.forEach(function (cd, i) {
        var y = startY + i * entryH;
        var col = clubColor(cd.club);

        // Color swatch (thick line)
        ctx.strokeStyle = col;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(legX, y + entryH / 2);
        ctx.lineTo(legX + 12, y + entryH / 2);
        ctx.stroke();

        // Club name
        ctx.font = 'bold 10px "Segoe UI", Arial, sans-serif';
        ctx.fillStyle = 'rgba(255,255,255,0.9)';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(cd.club, legX + 16, y + entryH / 2);

        // Distance (right-aligned)
        ctx.font = '10px "Segoe UI", Arial, sans-serif';
        ctx.fillStyle = 'rgba(255,255,255,0.6)';
        ctx.textAlign = 'right';
        ctx.fillText(cd.dist + ' yd', legX + legendW - 16, y + entryH / 2);

        // Gap badge for problem gaps (only show ⚠ if gap is concerning)
        if (cd.gap !== null && cd.gap !== undefined && i < clubData.length - 1 && entryH >= 15) {
            var badgeColor = null;
            var warn = '';
            if (cd.gap > 20) { badgeColor = 'rgba(220, 53, 69, 0.75)'; warn = '↕' + cd.gap; }
            else if (cd.gap < 5) { badgeColor = 'rgba(255, 193, 7, 0.75)'; warn = '↕' + cd.gap; }
            if (badgeColor) {
                var midY = y + entryH;
                ctx.font = '8px "Segoe UI", sans-serif';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'middle';
                var tw = ctx.measureText(warn).width + 6;
                ctx.fillStyle = badgeColor;
                ctx.beginPath();
                ctx.roundRect(legX + 16, midY - 5, tw, 10, 3);
                ctx.fill();
                ctx.fillStyle = '#fff';
                ctx.fillText(warn, legX + 19, midY);
            }
        }
    });

    // Store cleanup reference (custom canvas, not Chart.js)
    chartInstances['carry-distribution'] = {
        destroy: function () {
            var c = canvas.getContext('2d');
            c.setTransform(1, 0, 0, 1, 0, 0);
            c.clearRect(0, 0, canvas.width, canvas.height);
            canvas.style.width = '';
            canvas.style.height = '';
        },
    };

    // Tooltip on hover — show club details near mouse
    canvas._carryArcHandler = function (e) {
        var rect = canvas.getBoundingClientRect();
        var mx = e.clientX - rect.left;
        var my = e.clientY - rect.top;
        // Check if within arc area
        if (mx > arcW) return;
        var dx = mx - cx;
        var dy = my - cy;
        var mouseR = Math.sqrt(dx * dx + dy * dy);
        var mouseYards = (mouseR / maxRadius) * scaleDist;
        // Find closest club
        var closest = null;
        var closestDelta = Infinity;
        clubData.forEach(function (cd) {
            var delta = Math.abs(mouseYards - cd.dist);
            if (delta < closestDelta) {
                closestDelta = delta;
                closest = cd;
            }
        });
        if (closest && closestDelta < scaleDist * 0.04) {
            canvas.title = closest.club + ': ' + closest.dist + ' yd (' + closest.count + ' shots)' +
                (closest.gap != null ? ' | Gap: ' + closest.gap + 'yd' : '');
        } else {
            canvas.title = '';
        }
    };
    canvas.addEventListener('mousemove', canvas._carryArcHandler);
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
    var datasets = clubNames.map(function (club, i) {
        var color = CLUB_PALETTE[i % CLUB_PALETTE.length];
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
                    title: { display: true, text: 'Offline (yards) \u2190 Left | Right \u2192' },
                    grid: { color: 'rgba(0,0,0,0.05)' },
                },
                y: {
                    title: { display: true, text: 'Carry (yards)' },
                    min: 0,
                },
            },
        },
        plugins: [dispersionTargetLine],
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