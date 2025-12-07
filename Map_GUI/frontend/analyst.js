// analyst.js - Comprehensive report archive management

let reports = [];
let currentEditingReportId = null;
let pendingDeleteId = null;

function showMessage(msg, isError = false) {
    const container = document.getElementById('message-container');
    const className = isError ? 'error' : 'success';
    container.innerHTML = `<div class="${className}">${escapeHtml(msg)}</div>`;
    setTimeout(() => { container.innerHTML = ''; }, 4000);
}

function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>"]+/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c] || c);
}

async function loadReports() {
    const container = document.getElementById('reports-container');
    container.innerHTML = '<div class="loading">Loading reports...</div>';
    try {
        const resp = await fetch('/api/reports');
        if (!resp.ok) throw new Error('Failed to load reports');
        reports = await resp.json();
        renderReports();
    } catch (err) {
        console.error(err);
        container.innerHTML = `<div class="error">Failed to load reports: ${escapeHtml(err.message)}</div>`;
    }
}

function renderReports() {
    const container = document.getElementById('reports-container');
    if (!Array.isArray(reports) || reports.length === 0) {
        container.innerHTML = '<div class="loading">No reports found. Create a new one to get started.</div>';
        return;
    }

    let html = '<table class="table"><thead><tr><th>Type</th><th>Location</th><th>Timestamp</th><th>Description</th><th>Actions</th></tr></thead><tbody>';
    
    reports.forEach(r => {
        const id = r._id || (r.filename ? r.filename.replace(/^report_|\.json$/g, '') : 'unknown');
        const type = r.type || 'drone';
        const badge = type === 'camera' ? 'badge-camera' : type === 'radar' ? 'badge-radar' : 'badge-drone';
        const lat = r.latitude || r.lat || '?';
        const lon = r.longitude || r.lon || '?';
        const ts = r.timestamp ? new Date(r.timestamp * 1000).toLocaleString() : 'N/A';
        const desc = (r.description || r.drone_description || r.notes || '').substring(0, 50);

        html += `<tr>
            <td><span class="badge ${badge}">${escapeHtml(type)}</span></td>
            <td>${lat}, ${lon}</td>
            <td>${ts}</td>
            <td>${escapeHtml(desc)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-primary" onclick="editReport('${id}')">Edit</button>
                    <button class="btn btn-danger" onclick="deleteReport('${id}')">Delete</button>
                </div>
            </td>
        </tr>`;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

function toggleNewReportForm() {
    const form = document.getElementById('new-report-form');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
    if (form.style.display === 'block') {
        // Set current time as default
        const now = new Date().toISOString().slice(0, 16);
        document.getElementById('form-timestamp').value = now;
    }
}

document.getElementById('form-new-report')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const type = document.getElementById('form-type').value;
    const lat = parseFloat(document.getElementById('form-lat').value);
    const lon = parseFloat(document.getElementById('form-lon').value);
    const altitude = document.getElementById('form-altitude').value ? parseInt(document.getElementById('form-altitude').value) : null;
    const droneType = document.getElementById('form-drone-type').value;
    const description = document.getElementById('form-description').value;
    const timestamp = document.getElementById('form-timestamp').value;
    
    if (!type || isNaN(lat) || isNaN(lon)) {
        showMessage('Please fill in all required fields', true);
        return;
    }

    const payload = {
        type: type,
        latitude: lat,
        longitude: lon,
        description: description,
        drone_type: droneType || undefined,
        altitude: altitude || undefined,
        timestamp: timestamp ? new Date(timestamp).getTime() / 1000 : Date.now() / 1000
    };

    try {
        const resp = await fetch('/api/reports', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Failed to create report');
        }

        showMessage('Report created successfully!');
        toggleNewReportForm();
        document.getElementById('form-new-report').reset();
        loadReports();
    } catch (err) {
        console.error(err);
        showMessage(`Error: ${escapeHtml(err.message)}`, true);
    }
});

function editReport(id) {
    const report = reports.find(r => (r._id || (r.filename ? r.filename.replace(/^report_|\.json$/g, '') : null)) === id);
    if (!report) {
        showMessage('Report not found', true);
        return;
    }

    currentEditingReportId = id;
    document.getElementById('edit-type').value = report.type || 'drone';
    document.getElementById('edit-lat').value = report.latitude || report.lat || '';
    document.getElementById('edit-lon').value = report.longitude || report.lon || '';
    document.getElementById('edit-altitude').value = report.altitude || '';
    document.getElementById('edit-description').value = report.description || report.drone_description || report.notes || '';

    document.getElementById('edit-modal').classList.add('show');
}

document.getElementById('form-edit-report')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!currentEditingReportId) {
        showMessage('No report selected for editing', true);
        return;
    }

    const type = document.getElementById('edit-type').value;
    const lat = parseFloat(document.getElementById('edit-lat').value);
    const lon = parseFloat(document.getElementById('edit-lon').value);
    const altitude = document.getElementById('edit-altitude').value ? parseInt(document.getElementById('edit-altitude').value) : null;
    const description = document.getElementById('edit-description').value;

    if (isNaN(lat) || isNaN(lon)) {
        showMessage('Invalid latitude/longitude', true);
        return;
    }

    const payload = {
        type: type,
        latitude: lat,
        longitude: lon,
        description: description,
        altitude: altitude || undefined
    };

    try {
        const resp = await fetch(`/api/reports/${currentEditingReportId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Failed to update report');
        }

        showMessage('Report updated successfully!');
        closeEditModal();
        loadReports();
    } catch (err) {
        console.error(err);
        showMessage(`Error: ${escapeHtml(err.message)}`, true);
    }
});

function closeEditModal() {
    document.getElementById('edit-modal').classList.remove('show');
    currentEditingReportId = null;
}

function deleteReport(id) {
    pendingDeleteId = id;
    const report = reports.find(r => (r._id || (r.filename ? r.filename.replace(/^report_|\.json$/g, '') : null)) === id);
    const desc = report ? (report.description || report.type || 'Unknown') : 'Unknown';
    
    document.getElementById('confirm-title').textContent = 'Delete Report';
    document.getElementById('confirm-message').textContent = `Are you sure you want to delete this report?\n\n${escapeHtml(desc.substring(0, 100))}`;
    document.getElementById('confirm-modal').classList.add('show');
}

function closeConfirmModal() {
    document.getElementById('confirm-modal').classList.remove('show');
    pendingDeleteId = null;
}

async function confirmAction() {
    if (!pendingDeleteId) {
        showMessage('No report selected', true);
        return;
    }

    try {
        const resp = await fetch(`/api/reports/${pendingDeleteId}`, { method: 'DELETE' });
        
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Failed to delete report');
        }

        showMessage('Report deleted successfully!');
        closeConfirmModal();
        loadReports();
    } catch (err) {
        console.error(err);
        showMessage(`Error: ${escapeHtml(err.message)}`, true);
    }
}

function goBack() {
    window.location.href = 'index.html';
}

function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_role');
    window.location.href = 'index.html';
}

function showInfo() {
    document.getElementById('info-modal').classList.add('show');
}

function closeInfoModal() {
    document.getElementById('info-modal').classList.remove('show');
}
// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadReports();
    // Refresh every 30 seconds
    setInterval(loadReports, 30000);
});
