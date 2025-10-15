const map = L.map('map').setView([50.85, 4.35], 8); // centered over RMA/Belgium
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18,
  attribution: '© OpenStreetMap'
}).addTo(map);


let markers = {}; // icao -> marker


async function fetchLatest() {
  try {
    const res = await fetch('/api/aircraft/latest');
    const list = await res.json();
    updateMap(list);
  } catch (e) {
    console.error(e);
  }
}


function updateMap(list) {
  const ul = document.getElementById('planes');
  ul.innerHTML = '';
  const seen = new Set();
  list.forEach(item => {
    const icao = item.icao || item.icao24 || 'unknown';
    seen.add(icao);
    const lat = item.lat || item.latitude || 0;
    const lon = item.lon || item.longitude || 0;
    const flight = item.flight || item.callsign || '';
    const alt = item.alt || item.alt_geom || item.geo_alt || 0;


    // marker
    if (markers[icao]) {
      markers[icao].setLatLng([lat, lon]);
      markers[icao].bindPopup(`<b>${flight}</b><br>${icao}<br>alt ${alt} m`);
    } else {
      const m = L.marker([lat, lon]).addTo(map).bindPopup(`<b>${flight}</b><br>${icao}<br>alt ${alt} m`);
      markers[icao] = m;
    }


    // list entry
    const li = document.createElement('li');
    li.innerHTML = `<b>${flight}</b> (${icao}) &nbsp; ${lat.toFixed(4)}, ${lon.toFixed(4)} &nbsp; alt ${Math.round(alt)} m`;
    ul.appendChild(li);
  });


  // remove markers not seen
  Object.keys(markers).forEach(icao => { if (!seen.has(icao)) { map.removeLayer(markers[icao]); delete markers[icao]; }});
}


let timer = null;
function startPolling() {
  const interval = Number(document.getElementById('poll').value) * 1000;
  if (timer) clearInterval(timer);
  fetchLatest();
  timer = setInterval(fetchLatest, interval);
}


document.getElementById('poll').addEventListener('change', startPolling);
document.getElementById('refresh').addEventListener('click', fetchLatest);
startPolling();
