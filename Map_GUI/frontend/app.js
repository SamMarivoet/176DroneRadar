const map = L.map('map').setView([50.85, 4.35], 7);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

async function loadSightings() {
  const resp = await fetch('/api/reports');
  const reports = await resp.json();

  reports.forEach(r => {
    const color = getMarkerColor(r.drone_type);
    const radius = getMarkerRadius(r.altitude);
    const marker = L.circleMarker([r.latitude, r.longitude], {
      color,
      fillColor: color,
      fillOpacity: 0.8,
      radius
    }).addTo(map);

    marker.bindPopup(`
      <b>${capitalize(r.drone_type)} Drone</b><br>
      Altitude: ${r.altitude}<br>
      ${r.description}<br>
      <small>${new Date(r.timestamp).toLocaleString()}</small>
    `);
  });
}

async function loadPlanes() {
  const resp = await fetch('/api/planes');
  const data = await resp.json();
  const planes = data.planes || [];

  planes.forEach(p => {
    const icon = L.icon({
      iconUrl: 'icons/plane.png',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    const marker = L.marker([p.lat, p.lon], { icon }).addTo(map);
    marker.bindPopup(`
      <b>Flight ${p.flight}</b><br>
      Country: ${p.country}<br>
      Altitude: ${Math.round(p.alt)} m<br>
      Speed: ${Math.round(p.spd)} km/h<br>
      Heading: ${Math.round(p.heading)}°
    `);
  });
}

function getMarkerColor(type) {
  switch (type) {
    case 'consumer': return 'green';
    case 'commercial': return 'blue';
    case 'military': return 'red';
    case 'racing': return 'orange';
    default: return 'gray';
  }
}

function getMarkerRadius(altitude) {
  switch (altitude) {
    case '0-50m (low)': return 5;
    case '50-150m (medium)': return 8;
    case '150-400m (high)': return 11;
    case '+400m (very high)': return 14;
    default: return 6;
  }
}

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

loadSightings();
loadPlanes();
