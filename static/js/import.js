/* ==========================================================================
   WedgeMatrix — import.js
   CSV import UI: file upload, shot preview, swing size batch-tagging
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    initSwingSizeTagging();
    initSaveValidation();
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
            checkboxes.forEach(function (cb) { cb.checked = checked; });
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

                checkboxes.forEach(function (c) {
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
    });

    // Clear selection
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            checkboxes.forEach(function (cb) {
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

/* ---------- Save Validation ---------- */
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