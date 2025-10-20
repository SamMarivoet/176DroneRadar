const map = L.map('map').setView([50.85, 4.35], 7);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

async function loadSightings() {
  const response = await fetch('/api/reports'); // backend endpoint that lists JSON reports
  const sightings = await response.json();

  sightings.forEach(sighting => {
    const color = getMarkerColor(sighting.drone_type);
    const radius = getMarkerRadius(sighting.altitude);

    const marker = L.circleMarker([sighting.latitude, sighting.longitude], {
      color,
      fillColor: color,
      fillOpacity: 0.8,
      radius
    }).addTo(map);

    marker.bindPopup(`
      <b>${capitalize(sighting.drone_type)} Drone</b><br>
      Altitude: ${sighting.altitude}<br>
      ${sighting.description}<br>
      <small>${new Date(sighting.timestamp).toLocaleString()}</small>
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
  return s.charAt(0).toUpperCase() + s.slice(1);
}

loadSightings();
