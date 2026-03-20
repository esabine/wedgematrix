/* ==========================================================================
   WedgeMatrix — app.js
   Main client-side logic: matrix controls, shot exclusions, batch ops
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    initFlashAutoDismiss();
    initMatrixControls();
    initShotExclusionToggles();
    initBatchSelectExclude();
    initDeleteConfirmation();
    initClubToggleButtons();
});

/* ---------- Flash Message Auto-Dismiss ---------- */
function initFlashAutoDismiss() {
    document.querySelectorAll('#flash-container .alert').forEach(function (alert) {
        setTimeout(function () {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
}

/* ---------- Matrix Controls (Percentile + Session Scope) ---------- */
function initMatrixControls() {
    var percentileSelect = document.getElementById('percentile-select');
    var sessionScope = document.getElementById('session-scope');

    if (percentileSelect) {
        percentileSelect.addEventListener('change', reloadMatrixView);
    }
    if (sessionScope) {
        sessionScope.addEventListener('change', reloadMatrixView);
    }
}

function reloadMatrixView() {
    var percentileSelect = document.getElementById('percentile-select');
    var sessionScope = document.getElementById('session-scope');
    var matrixType = percentileSelect
        ? percentileSelect.getAttribute('data-matrix')
        : 'club';

    var params = new URLSearchParams();
    if (percentileSelect && percentileSelect.value) {
        params.set('percentile', percentileSelect.value);
    }
    if (sessionScope && sessionScope.value) {
        params.set('session_id', sessionScope.value);
    }

    var baseUrl = matrixType === 'wedge' ? '/wedge-matrix' : '/club-matrix';
    window.location.href = baseUrl + '?' + params.toString();
}

/* ---------- Shot Exclude Toggle (AJAX) ---------- */
function initShotExclusionToggles() {
    document.querySelectorAll('.toggle-exclude-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var shotId = this.getAttribute('data-shot-id');
            toggleShotExclude(shotId, this);
        });
    });
}

function toggleShotExclude(shotId, btn) {
    fetch('/shots/' + shotId + '/toggle-exclude', {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
        .then(function (response) { return response.json(); })
        .then(function (data) {
            if (data.success) {
                var row = btn.closest('tr');
                var icon = btn.querySelector('i');

                if (data.excluded) {
                    row.classList.add('excluded-row');
                    btn.classList.remove('btn-outline-warning');
                    btn.classList.add('btn-outline-success');
                    btn.title = 'Include this shot';
                    icon.classList.remove('bi-eye-slash');
                    icon.classList.add('bi-eye');
                    var badge = row.querySelector('.badge');
                    if (badge) {
                        badge.className = 'badge bg-secondary';
                        badge.textContent = 'Excluded';
                    }
                } else {
                    row.classList.remove('excluded-row');
                    btn.classList.remove('btn-outline-success');
                    btn.classList.add('btn-outline-warning');
                    btn.title = 'Exclude this shot';
                    icon.classList.remove('bi-eye');
                    icon.classList.add('bi-eye-slash');
                    var badge = row.querySelector('.badge');
                    if (badge) {
                        badge.className = 'badge bg-light text-dark';
                        badge.textContent = 'Active';
                    }
                }
            }
        })
        .catch(function (err) {
            console.error('Toggle failed:', err);
        });
}

/* ---------- Batch Select & Exclude/Include ---------- */
function initBatchSelectExclude() {
    // Skip on shots page — handled by inline script with better integration
    if (document.getElementById('shots-date-range-group')) return;

    var selectAll = document.getElementById('select-all');
    var excludeBtn = document.getElementById('batch-exclude-btn');
    var includeBtn = document.getElementById('batch-include-btn');

    if (!selectAll || !excludeBtn) return;

    selectAll.addEventListener('change', function () {
        var checked = this.checked;
        // Only toggle visible rows
        document.querySelectorAll('.shot-data-row').forEach(function (row) {
            if (row.style.display !== 'none') {
                var cb = row.querySelector('.shot-checkbox');
                if (cb) cb.checked = checked;
            }
        });
        updateBatchButtons();
    });

    document.getElementById('shots-table').addEventListener('change', function (e) {
        if (e.target.classList.contains('shot-checkbox')) {
            updateBatchButtons();
        }
    });

    excludeBtn.addEventListener('click', function () {
        batchToggleExclude(true);
    });

    includeBtn.addEventListener('click', function () {
        batchToggleExclude(false);
    });

    function updateBatchButtons() {
        var anyChecked = document.querySelectorAll('.shot-checkbox:checked').length > 0;
        excludeBtn.disabled = !anyChecked;
        includeBtn.disabled = !anyChecked;
    }

    function batchToggleExclude(exclude) {
        var selected = document.querySelectorAll('.shot-checkbox:checked');
        var ids = Array.from(selected).map(function (cb) { return parseInt(cb.value, 10); });

        if (!ids.length) return;

        fetch('/shots/batch-exclude', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ shot_ids: ids, exclude: exclude })
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    window.location.reload();
                } else {
                    console.error('Batch operation error:', data.error);
                }
            })
            .catch(function (err) {
                console.error('Batch operation failed:', err);
            });
    }
}

/* ---------- Delete Session Confirmation ---------- */
function initDeleteConfirmation() {
    document.querySelectorAll('.delete-session-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var sessionId = this.getAttribute('data-session-id');
            var sessionName = this.getAttribute('data-session-name');

            document.getElementById('delete-session-name').textContent = sessionName;
            document.getElementById('delete-session-form').action =
                '/sessions/' + sessionId + '/delete';

            var modal = new bootstrap.Modal(
                document.getElementById('deleteSessionModal')
            );
            modal.show();
        });
    });
}

/* ---------- Club Toggle Buttons (Shots page — client-side only) ---------- */
function initClubToggleButtons() {
    var toggleGroup = document.getElementById('club-toggle-group');
    if (!toggleGroup) return;

    // Skip if the page uses server-side pagination (shots page now handles its own toggles)
    if (document.querySelector('.pagination[aria-label="Shot pagination"]')) return;
    // Also skip if the shots page inline script is present (detected by shots-date-range-group)
    if (document.getElementById('shots-date-range-group')) return;

    var buttons = toggleGroup.querySelectorAll('.club-toggle-btn');
    var allBtn = document.getElementById('club-toggle-all-btn');
    var table = document.getElementById('shots-table');

    if (!table) return;

    // Cache rows + their clubs once — avoids DOM re-query on every toggle
    var rows = table.querySelectorAll('tbody .shot-data-row');
    var rowClubs = [];
    rows.forEach(function (row) {
        var cell = row.querySelectorAll('td')[1];
        rowClubs.push(cell ? cell.textContent.trim() : '');
    });

    var countEl = document.getElementById('shot-count');
    var activeSet = {};
    buttons.forEach(function (b) {
        if (b.getAttribute('data-active') === '1') {
            activeSet[b.getAttribute('data-club')] = true;
        }
    });

    function activeCount() {
        var n = 0;
        for (var k in activeSet) { if (activeSet[k]) n++; }
        return n;
    }

    function applyFilter() {
        var total = activeCount();
        var showAll = total === 0 || total === buttons.length;
        var visibleCount = 0;

        for (var i = 0; i < rows.length; i++) {
            var show = showAll || activeSet[rowClubs[i]];
            rows[i].style.display = show ? '' : 'none';
            if (show) visibleCount++;
        }

        if (countEl) countEl.textContent = visibleCount + ' shots';

        if (allBtn) {
            if (total === buttons.length) {
                allBtn.classList.remove('btn-outline-secondary');
                allBtn.classList.add('btn-golf');
            } else {
                allBtn.classList.remove('btn-golf');
                allBtn.classList.add('btn-outline-secondary');
            }
        }
    }

    // "None" button for shots page
    var noneBtn = document.getElementById('club-toggle-none-btn');

    function setButtonState(btn, active) {
        var club = btn.getAttribute('data-club');
        activeSet[club] = active;
        btn.setAttribute('data-active', active ? '1' : '0');
        btn.classList.toggle('btn-golf', active);
        btn.classList.toggle('btn-outline-secondary', !active);
    }

    buttons.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            var club = this.getAttribute('data-club');
            if (e.ctrlKey || e.metaKey) {
                // Ctrl+click: additive toggle (old behavior)
                setButtonState(this, !activeSet[club]);
            } else {
                // Plain click: exclusive select — deselect all, select only this
                buttons.forEach(function (b) { setButtonState(b, false); });
                setButtonState(this, true);
            }
            applyFilter();
        });
    });

    if (allBtn) {
        allBtn.addEventListener('click', function () {
            buttons.forEach(function (btn) { setButtonState(btn, true); });
            applyFilter();
        });
    }

    if (noneBtn) {
        noneBtn.addEventListener('click', function () {
            buttons.forEach(function (btn) { setButtonState(btn, false); });
            applyFilter();
        });
    }
}