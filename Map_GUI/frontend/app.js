document.addEventListener("DOMContentLoaded", () => {
  const planeTrails = {}; // flight ID → array of LatLngs

  // --- MAP SETUP ---
  const map = L.map('map').setView([50.85, 4.35], 7);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
  }).addTo(map);

  // --- LAYER GROUPS ---
  const droneLayer = L.layerGroup();
  const planeLayer = L.layerGroup();

  // add both by default
  droneLayer.addTo(map);
  planeLayer.addTo(map);

  // --- FILTER STATE ---
  let showDrones = true;
  let showPlanes = true;

  // --- FILTER LOGIC ---
  function updateLayersVisibility() {
    if (showDrones) {
      map.addLayer(droneLayer);
    } else {
      map.removeLayer(droneLayer);
    }

    if (showPlanes) {
      map.addLayer(planeLayer);
    } else {
      map.removeLayer(planeLayer);
    }
  }

  // attach listeners once DOM is ready
  const toggleDrones = document.getElementById('toggle-drones');
  const togglePlanes = document.getElementById('toggle-planes');

  if (toggleDrones && togglePlanes) {
    toggleDrones.addEventListener('change', e => {
      showDrones = e.target.checked;
      updateLayersVisibility();
    });

    togglePlanes.addEventListener('change', e => {
      showPlanes = e.target.checked;
      updateLayersVisibility();
    });
  }

  // --- FETCH + RENDER LOGIC ---
  async function loadPlanes() {
    try {
      const resp = await fetch('/api/planes');
      const data = await resp.json();
      const planes = data.planes || [];

      // reset layers
      droneLayer.clearLayers();
      planeLayer.clearLayers();

      planes.forEach(p => {
        // detect whether this document is a drone report or plane telemetry
        const source = (p.source || p.producer || '').toString().toLowerCase();
        const isReport = source === 'dronereport' || source === 'form' || p.report_type || p.kind === 'report';

        // defensive coordinate extraction
        const lat = p.lat || p.latitude || (p.position?.coordinates?.[1]);
        const lon = p.lon || p.longitude || (p.position?.coordinates?.[0]);
        if (typeof lat !== 'number' || typeof lon !== 'number') return;

        if (isReport) {
          const color = getMarkerColor(p.drone_type || 'consumer');
          const radius = getMarkerRadius(p.altitude || p.alt || '0-50m (low)');
          const marker = L.circleMarker([lat, lon], {
            color,
            fillColor: color,
            fillOpacity: 0.8,
            radius
          }).bindPopup(`
            <b>${capitalize(p.drone_type || 'Drone')} Report</b><br>
            Altitude: ${p.altitude || p.alt || ''}<br>
            ${p.description || ''}<br>
            <small>${p.timestamp ? new Date(p.timestamp).toLocaleString() : ''}</small>
          `);
          droneLayer.addLayer(marker);
        } else {
          const icon = L.icon({
            iconUrl: 'icons/plane.png',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
          });
          const flight = p.flight || p.callsign || p.registration || '';
          const alt = p.alt || p.altitude || p.geo_alt || 0;
          const spd = p.spd || p.speed || 0;
          const heading = p.heading || p.track || 0;

          const marker = L.marker([lat, lon], {
            icon,
            rotationAngle: heading - 45,
            rotationOrigin: 'center center'
          }).bindPopup(`
            <b>Flight ${flight}</b><br>
            Country: ${p.country || ''}<br>
            Altitude: ${Math.round(alt)} m<br>
            Speed: ${Math.round(spd)} km/h<br>
            Heading: ${Math.round(heading)}°
          `);
          planeLayer.addLayer(marker);

          // trail logic
          const flightId = flight || `unknown-${lat}-${lon}`;
          if (!planeTrails[flightId]) {
            planeTrails[flightId] = [];
          }
          planeTrails[flightId].push([lat, lon]);
          if (planeTrails[flightId].length > 100) {
            planeTrails[flightId].shift();
          }

          const trail = L.polyline(planeTrails[flightId], {
            color: 'blue',
            weight: 2,
            opacity: 0.6
          });
          planeLayer.addLayer(trail);
        }
      });

    } catch (err) {
      console.error('Error loading planes:', err);
    }
  }

  // --- UTILITIES ---
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

  // --- MAIN UPDATE LOOP ---
  async function updateLoop() {
    console.log('Update tick at', new Date().toLocaleTimeString());
    await loadPlanes();
    document.dispatchEvent(new Event('updateComplete'));
    setTimeout(updateLoop, 5000);
  }

  updateLoop(); // Start it!
});

