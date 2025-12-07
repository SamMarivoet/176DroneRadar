// authority.js - Airport corridor monitoring and alerting

const CORRIDOR_RADIUS_METERS = 3000; // 3 km radius
const POLL_INTERVAL_MS = 5000; // 5 seconds

// Configured airports with their corridors
const AIRPORTS = [
    { id: 'BRU', name: 'Brussels-Zaventem', lat: 50.9010, lon: 4.4844 },
    { id: 'CRL', name: 'Brussels South Charleroi', lat: 50.4593, lon: 4.4516 },
    { id: 'LGG', name: 'Liège Airport', lat: 50.6330, lon: 5.4375 },
    { id: 'ANR', name: 'Antwerp Airport', lat: 51.1897, lon: 4.4144 },
    { id: 'MST', name: 'Maastricht Airport', lat: 50.9170, lon: 5.7755 }
];

let alerts = []; // Store active alerts
let alertedSet = new Set(); // Track alerted items to avoid duplicates
let currentAlertData = null; // For modal display

// Initialize map
const map = L.map('map').setView([50.85, 4.35], 7);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);

// Layer for airports and their corridors
const airportsLayer = L.layerGroup().addTo(map);

// Layer for detections
const detectionsLayer = L.layerGroup().addTo(map);

// Draw airports and corridors
function drawAirports() {
    airportsLayer.clearLayers();
    AIRPORTS.forEach(airport => {
        // Draw corridor circle
        const circle = L.circle([airport.lat, airport.lon], {
            radius: CORRIDOR_RADIUS_METERS,
            color: '#ff6b6b',
            weight: 2,
            opacity: 0.3,
            fillOpacity: 0.05,
            dashArray: '5, 5'
        }).addTo(airportsLayer);
        
        // Add airport marker
        const marker = L.marker([airport.lat, airport.lon], {
            icon: L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            })
        }).bindPopup(`<b>${airport.name}</b><br>3 km Corridor`).addTo(airportsLayer);
    });
}

// Calculate distance between two points (Haversine formula)
function haversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000; // Earth radius in meters
    const toRad = deg => deg * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Load and check current reports for corridor violations
async function checkReports() {
    try {
        const resp = await fetch('/api/planes');
        if (!resp.ok) return;
        const data = await resp.json();
        const planes = (data && data.planes) ? data.planes : [];

        detectionsLayer.clearLayers();

        planes.forEach(p => {
            const source = (p.source || p.producer || '').toString().toLowerCase();
            const isReport = source === 'dronereport' || source === 'form' || p.report_type || p.kind === 'report';
            const isCamera = source === 'camera';
            const isRadar = source === 'radar';

            const lat = p.lat || p.latitude || (p.position && p.position.coordinates && p.position.coordinates[1]);
            const lon = p.lon || p.longitude || (p.position && p.position.coordinates && p.position.coordinates[0]);
            
            if (typeof lat !== 'number' || typeof lon !== 'number') return;

            // Show detection on map
            const color = isCamera ? '#9c27b0' : isRadar ? '#ff9800' : '#4caf50';
            const marker = L.circleMarker([lat, lon], {
                radius: 6,
                color: color,
                fillColor: color,
                fillOpacity: 0.8,
                weight: 2
            }).bindPopup(`<b>${isCamera ? 'Camera' : isRadar ? 'Radar' : 'Drone'} Detection</b><br>${p.description || ''}`).addTo(detectionsLayer);

            // Only process reports for corridor violations
            if (!(isReport || isCamera || isRadar)) return;

            // Check each airport
            AIRPORTS.forEach(airport => {
                const distance = haversineDistance(lat, lon, airport.lat, airport.lon);
                
                if (distance <= CORRIDOR_RADIUS_METERS) {
                    // Create unique alert ID to avoid duplicates
                    const alertId = `${p.icao || p.id || p.flight || (lat+lon)}_${airport.id}_${Math.round(distance/100)*100}`;
                    
                    if (!alertedSet.has(alertId)) {
                        alertedSet.add(alertId);
                        createAlert(p, airport, distance);
                        
                        // Send notification to backend
                        notifyBackend(p, airport, distance);
                    }
                }
            });
        });
    } catch (err) {
        console.error('Error checking reports:', err);
    }
}

function createAlert(report, airport, distance) {
    const alert = {
        id: Date.now(),
        timestamp: new Date(),
        report: report,
        airport: airport,
        distance: distance,
        type: (report.source || '').toString().toLowerCase() === 'camera' ? 'camera' :
              (report.source || '').toString().toLowerCase() === 'radar' ? 'radar' : 'drone'
    };
    
    alerts.unshift(alert); // Add to front
    renderAlerts();
    
    // Show browser notification if supported
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('⚠️ Corridor Violation!', {
            body: `${airport.name} - ${(distance/1000).toFixed(2)} km`
        });
    }
}

function renderAlerts() {
    const container = document.getElementById('alerts-container');
    
    if (alerts.length === 0) {
        container.innerHTML = '<div class="no-alerts">No alerts yet. Monitoring in progress...</div>';
        return;
    }
    
    let html = '';
    alerts.forEach(alert => {
        const distKm = (alert.distance / 1000).toFixed(2);
        const typeIcon = alert.type === 'camera' ? '📷' : alert.type === 'radar' ? '📡' : '🛸';
        const time = alert.timestamp.toLocaleTimeString();
        const desc = (alert.report.description || alert.report.drone_description || '').substring(0, 40);
        
        html += `<div class="alert new">
            <div class="alert-title">${typeIcon} ${alert.airport.name}</div>
            <div class="alert-distance">Distance: ${distKm} km</div>
            <div class="alert-airport">Code: ${alert.airport.id}</div>
            <div class="alert-desc">
                <small>${time} - ${escapeHtml(desc)}</small>
            </div>
            <button class="btn copy-btn" style="margin-top: 8px; padding: 6px;" onclick="showAlertDetails(${alert.id})">View Details</button>
        </div>`;
    });
    
    container.innerHTML = html;
}

function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>"]+/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c] || c);
}

async function notifyBackend(report, airport, distance) {
    // Prepare alert message for backend consumption
    const alertMessage = {
        timestamp: new Date().toISOString(),
        alert_type: 'corridor_violation',
        corridor_radius_m: CORRIDOR_RADIUS_METERS,
        report: report,
        airport: {
            id: airport.id,
            name: airport.name,
            latitude: airport.lat,
            longitude: airport.lon
        },
        distance_m: Math.round(distance),
        distance_km: (distance / 1000).toFixed(3),
        severity: distance < 1000 ? 'critical' : distance < 2000 ? 'high' : 'medium',
        detection_type: (report.source || '').toString().toLowerCase() === 'camera' ? 'camera' :
                       (report.source || '').toString().toLowerCase() === 'radar' ? 'radar' : 'drone'
    };

    // Send to backend for storage and notification to analyst/admin
    try {
        const resp = await fetch('/api/alert/authority', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(alertMessage)
        });
        
        if (resp.ok || resp.status === 202) {
            console.log('Alert sent to backend:', alertMessage);
        } else {
            console.warn('Backend alert failed:', resp.status);
        }
    } catch (err) {
        console.warn('Failed to send alert to backend:', err);
    }
}

function showAlertDetails(alertId) {
    const alert = alerts.find(a => a.id === alertId);
    if (!alert) return;
    
    currentAlertData = alert;
    
    const modalBody = document.getElementById('modal-body');
    const html = `
        <div class="field">
            <label>Alert Type:</label>
            <div class="field-value">${escapeHtml(alert.type.toUpperCase())} Detection</div>
        </div>
        <div class="field">
            <label>Airport:</label>
            <div class="field-value">${escapeHtml(alert.airport.name)} (${escapeHtml(alert.airport.id)})</div>
        </div>
        <div class="field">
            <label>Distance:</label>
            <div class="field-value">${(alert.distance/1000).toFixed(3)} km (${Math.round(alert.distance)} m)</div>
        </div>
        <div class="field">
            <label>Severity:</label>
            <div class="field-value">${alert.distance < 1000 ? 'CRITICAL' : alert.distance < 2000 ? 'HIGH' : 'MEDIUM'}</div>
        </div>
        <div class="field">
            <label>Timestamp:</label>
            <div class="field-value">${alert.timestamp.toLocaleString()}</div>
        </div>
        <div class="field">
            <label>Report Location:</label>
            <div class="field-value">${alert.report.latitude || alert.report.lat || '?'}, ${alert.report.longitude || alert.report.lon || '?'}</div>
        </div>
        <div class="field">
            <label>Description:</label>
            <div class="field-value">${escapeHtml(alert.report.description || alert.report.drone_description || 'N/A')}</div>
        </div>
        <div class="field">
            <label>Full Alert JSON:</label>
            <div class="field-value" style="white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto;">
${escapeHtml(JSON.stringify(alert, null, 2))}
            </div>
        </div>
    `;
    
    modalBody.innerHTML = html;
    document.getElementById('alert-modal').classList.add('show');
}

function closeAlertModal() {
    document.getElementById('alert-modal').classList.remove('show');
    currentAlertData = null;
}

function copyAlertJson() {
    if (!currentAlertData) return;
    
    const json = JSON.stringify(currentAlertData, null, 2);
    navigator.clipboard.writeText(json).then(() => {
        alert('Alert JSON copied to clipboard!');
    }).catch(err => {
        console.error('Copy failed:', err);
    });
}

function clearAlerts() {
    alerts = [];
    alertedSet.clear();
    renderAlerts();
}

function goBack() {
    window.location.href = 'index.html';
}

function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_role');
    window.location.href = 'index.html';
}

// Request notification permission
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    drawAirports();
    checkReports();
    // Poll for new reports
    setInterval(checkReports, POLL_INTERVAL_MS);
});

function showInfo() {
    document.getElementById('info-modal').classList.add('show');
}

function closeInfoModal() {
    document.getElementById('info-modal').classList.remove('show');
}
