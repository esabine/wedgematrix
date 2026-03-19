/* ==========================================================================
   WedgeMatrix — import.js
   CSV import UI: file upload, shot preview, swing size batch-tagging,
   incremental batch importing, group selection
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    initSwingSizeTagging();
    initSaveValidation();
    initBatchImport();
    initGroupSelect();
});

/* ---------- Swing Size Batch-Tagging ---------- */
function initSwingSizeTagging() {
    var table = document.getElementById('shot-preview-table');
    var assignBtn = document.getElementById('assign-size-btn');
    var clearBtn = document.getElementById('clear-selection-btn');
    var sizeSelect = document.getElementById('swing-size-select');
    var selectAll = document.getElementById('select-all-shots');

    if (!table || !assignBtn) return;

    var checkboxes = table.querySelectorAll('.shot-select');

    // Select all toggle
    if (selectAll) {
        selectAll.addEventListener('change', function () {
            var checked = this.checked;
            getVisibleCheckboxes().forEach(function (cb) { cb.checked = checked; });
            updateAssignButton();
        });
    }

    // Individual checkbox changes
    checkboxes.forEach(function (cb) {
        cb.addEventListener('change', updateAssignButton);
    });

    // Row click to toggle selection
    var lastCheckedIndex = null;

    table.querySelectorAll('.shot-row').forEach(function (row) {
        row.addEventListener('click', function (e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' ||
                e.target.tagName === 'BUTTON') return;

            var cb = row.querySelector('.shot-select');
            if (!cb) return;

            // Shift-click for range selection
            if (e.shiftKey && lastCheckedIndex !== null) {
                var currentIndex = parseInt(cb.getAttribute('data-index'));
                var start = Math.min(lastCheckedIndex, currentIndex);
                var end = Math.max(lastCheckedIndex, currentIndex);

                getVisibleCheckboxes().forEach(function (c) {
                    var idx = parseInt(c.getAttribute('data-index'));
                    if (idx >= start && idx <= end) {
                        c.checked = true;
                        c.closest('tr').classList.add('selected');
                    }
                });
            } else {
                cb.checked = !cb.checked;
            }

            if (cb.checked) {
                row.classList.add('selected');
                lastCheckedIndex = parseInt(cb.getAttribute('data-index'));
            } else {
                row.classList.remove('selected');
            }
            updateAssignButton();
        });
    });

    // Sync row highlight with checkbox state
    checkboxes.forEach(function (cb) {
        cb.addEventListener('change', function () {
            var row = this.closest('tr');
            if (this.checked) {
                row.classList.add('selected');
                lastCheckedIndex = parseInt(this.getAttribute('data-index'));
            } else {
                row.classList.remove('selected');
            }
        });
    });

    // Assign swing size to selected rows
    assignBtn.addEventListener('click', function () {
        var size = sizeSelect.value;
        if (!size) {
            alert('Please select a swing size first.');
            return;
        }

        var selected = table.querySelectorAll('.shot-select:checked');
        selected.forEach(function (cb) {
            var index = cb.getAttribute('data-index');
            var badge = table.querySelector('.swing-size-badge[data-index="' + index + '"]');
            var input = table.querySelector('.swing-size-input[data-index="' + index + '"]');

            if (badge) {
                badge.textContent = size;
                badge.classList.add('assigned');
            }
            if (input) {
                input.value = size;
            }

            cb.checked = false;
            cb.closest('tr').classList.remove('selected');
        });

        sizeSelect.value = '';
        if (selectAll) selectAll.checked = false;
        updateAssignButton();
        updateSaveButton();
        updateBatchButton();
    });

    // Clear selection
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            getVisibleCheckboxes().forEach(function (cb) {
                cb.checked = false;
                cb.closest('tr').classList.remove('selected');
            });
            if (selectAll) selectAll.checked = false;
            updateAssignButton();
        });
    }

    function updateAssignButton() {
        var anyChecked = table.querySelectorAll('.shot-select:checked').length > 0;
        assignBtn.disabled = !anyChecked;
    }

    if (sizeSelect) {
        sizeSelect.addEventListener('change', updateAssignButton);
    }
}

/* ---------- Group Selection ---------- */
function initGroupSelect() {
    var selectGroupBtn = document.getElementById('select-group-btn');
    var groupSizeInput = document.getElementById('group-size-input');

    if (!selectGroupBtn || !groupSizeInput) return;

    selectGroupBtn.addEventListener('click', function () {
        var count = parseInt(groupSizeInput.value) || 5;
        var visible = getVisibleCheckboxes();

        // Clear all first
        visible.forEach(function (cb) {
            cb.checked = false;
            cb.closest('tr').classList.remove('selected');
        });

        // Select the first N visible unimported rows
        var selected = 0;
        for (var i = 0; i < visible.length && selected < count; i++) {
            visible[i].checked = true;
            visible[i].closest('tr').classList.add('selected');
            selected++;
        }

        // Update button states
        var assignBtn = document.getElementById('assign-size-btn');
        if (assignBtn) assignBtn.disabled = (selected === 0);
    });
}

/* ---------- Batch Import ---------- */
var batchSessionId = null;  // track across multiple batches

function initBatchImport() {
    var importBtn = document.getElementById('import-batch-btn');
    if (!importBtn) return;

    importBtn.addEventListener('click', function () {
        var table = document.getElementById('shot-preview-table');
        if (!table) return;

        // Gather all tagged (swing_size assigned) rows that are still visible
        var taggedRows = [];
        table.querySelectorAll('tbody tr.shot-row').forEach(function (row) {
            var input = row.querySelector('.swing-size-input');
            if (input && input.value) {
                var index = parseInt(row.getAttribute('data-index'));
                taggedRows.push({ row: row, index: index, swingSize: input.value });
            }
        });

        if (taggedRows.length === 0) {
            alert('No shots have been tagged with a swing size. Assign sizes first.');
            return;
        }

        // Read session_info from hidden field
        var sessionInfoEl = document.querySelector('input[name="session_info"]');
        var shotsDataEl = document.querySelector('input[name="shots_data"]');
        if (!sessionInfoEl || !shotsDataEl) return;

        var sessionInfo = JSON.parse(sessionInfoEl.value);
        var allShots = JSON.parse(shotsDataEl.value);

        // Build shot payloads from tagged rows
        var batchShots = taggedRows.map(function (item) {
            var shotData = allShots[item.index];
            shotData.swing_size = item.swingSize;
            return shotData;
        });

        importBtn.disabled = true;
        importBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Importing…';

        fetch('/api/import/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_info: sessionInfo,
                session_id: batchSessionId,
                shots: batchShots,
            }),
        })
        .then(function (r) { return r.json(); })
        .then(function (result) {
            if (result.success) {
                batchSessionId = result.session_id;

                // Remove imported rows from DOM
                taggedRows.forEach(function (item) {
                    item.row.remove();
                });

                // Update remaining count
                var remaining = table.querySelectorAll('tbody tr.shot-row').length;
                var countBadge = document.getElementById('remaining-count');
                if (countBadge) countBadge.textContent = remaining + ' shots remaining';

                var statusEl = document.getElementById('import-status');
                if (statusEl) statusEl.textContent = result.saved_count + ' shots saved ✓';

                // If no rows left, show "all done"
                if (remaining === 0) {
                    var allDone = document.getElementById('all-done-section');
                    var viewLink = document.getElementById('view-session-link');
                    if (allDone) allDone.style.display = '';
                    if (viewLink) viewLink.href = '/sessions/' + batchSessionId;
                    importBtn.style.display = 'none';
                }

                updateBatchButton();
            } else {
                alert('Import error: ' + (result.error || 'Unknown error'));
            }
        })
        .catch(function (err) {
            alert('Network error: ' + err.message);
        })
        .finally(function () {
            importBtn.disabled = false;
            importBtn.innerHTML = '<i class="bi bi-cloud-upload"></i> Import Tagged Shots';
            updateBatchButton();
        });
    });
}

function updateBatchButton() {
    var importBtn = document.getElementById('import-batch-btn');
    if (!importBtn) return;

    var table = document.getElementById('shot-preview-table');
    if (!table) return;

    // Enable only if at least one visible row has a swing size
    var anyTagged = false;
    table.querySelectorAll('tbody tr.shot-row .swing-size-input').forEach(function (input) {
        if (input.value) anyTagged = true;
    });
    importBtn.disabled = !anyTagged;
}

/* ---------- Save Validation (club data — full save) ---------- */
function initSaveValidation() {
    var saveBtn = document.getElementById('save-import-btn');
    var form = document.getElementById('save-import-form');

    if (!saveBtn || !form) return;

    form.addEventListener('submit', function (e) {
        var swingSizeInputs = form.querySelectorAll('.swing-size-input');
        if (swingSizeInputs.length === 0) return;

        var untagged = [];
        swingSizeInputs.forEach(function (input) {
            if (!input.value) {
                untagged.push(parseInt(input.getAttribute('data-index')) + 1);
            }
        });

        if (untagged.length > 0) {
            e.preventDefault();
            alert(
                'The following shots need a swing size assigned:\n' +
                'Rows: ' + untagged.join(', ') +
                '\n\nPlease select rows and assign swing sizes before saving.'
            );
        }
    });
}

function updateSaveButton() {
    var saveBtn = document.getElementById('save-import-btn');
    var swingSizeInputs = document.querySelectorAll('.swing-size-input');

    if (!saveBtn || swingSizeInputs.length === 0) return;

    var allTagged = true;
    swingSizeInputs.forEach(function (input) {
        if (!input.value) allTagged = false;
    });

    if (allTagged) {
        saveBtn.classList.remove('btn-secondary');
        saveBtn.classList.add('btn-golf');
    }
}

/* ---------- Helpers ---------- */
function getVisibleCheckboxes() {
    var table = document.getElementById('shot-preview-table');
    if (!table) return [];
    return Array.from(table.querySelectorAll('tbody tr.shot-row .shot-select'));
}