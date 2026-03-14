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
    var selectAll = document.getElementById('select-all');
    var excludeBtn = document.getElementById('batch-exclude-btn');
    var includeBtn = document.getElementById('batch-include-btn');
    var checkboxes = document.querySelectorAll('.shot-checkbox');

    if (!selectAll || !excludeBtn) return;

    selectAll.addEventListener('change', function () {
        var checked = this.checked;
        checkboxes.forEach(function (cb) { cb.checked = checked; });
        updateBatchButtons();
    });

    checkboxes.forEach(function (cb) {
        cb.addEventListener('change', updateBatchButtons);
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
        var ids = Array.from(selected).map(function (cb) { return cb.value; });

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