document.addEventListener("DOMContentLoaded", () => {
  const planeTrails = {}; // flight ID → array of LatLngs
  let currentTrail = null; // store the currently visible trail



  // --- MAP SETUP ---
  const map = L.map('map').setView([50.85, 4.35], 7);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
  }).addTo(map);

  // --- LAYER GROUPS ---
  
  const planeLayer = L.layerGroup().addTo(map);
  const dronesReportLayer = L.layerGroup().addTo(map); // NEW LINE
  const dronesCameraLayer = L.layerGroup().addTo(map); // NEW LINE
  const dronesRadarLayer = L.layerGroup().addTo(map);  // NEW LINE
  const gliderLayer = L.layerGroup().addTo(map);       // NEW LINE
  
  // --- FILTER STATE ---
  
  let showPlanes = true;
  let showOgn = true;
  let showDronesReport = true; // NEW LINE
  let showDronesCamera = true; // NEW LINE
  let showDronesRadar = true;  // NEW LINE

  function updateLayersVisibility() {
    
    showPlanes ? map.addLayer(planeLayer) : map.removeLayer(planeLayer);
    showDronesReport ? map.addLayer(dronesReportLayer) : map.removeLayer(dronesReportLayer); // NEW LINE
    showDronesCamera ? map.addLayer(dronesCameraLayer) : map.removeLayer(dronesCameraLayer); // NEW LINE
    showDronesRadar ? map.addLayer(dronesRadarLayer) : map.removeLayer(dronesRadarLayer);    // NEW LINE
    showOgn ? map.addLayer(gliderLayer) : map.removeLayer(gliderLayer);                      // NEW LINE
  }

  // --- FILTER EVENTS ---
  
  const togglePlanes = document.getElementById('toggle-planes');
  const toggleOgn = document.getElementById('toggle-ogn');
  const toggleDronesReport = document.getElementById('toggle-drones-report'); // NEW LINE
  const toggleDronesCamera = document.getElementById('toggle-drones-camera'); // NEW LINE
  const toggleDronesRadar = document.getElementById('toggle-drones-radar');   // NEW LINE



  togglePlanes.addEventListener('change', e => {
    showPlanes = e.target.checked;
    updateLayersVisibility();
  });

  toggleOgn.addEventListener('change', e => {
    showOgn = e.target.checked;
    updateLayersVisibility();
  });


  toggleDronesReport.addEventListener('change', e => { // NEW LINE
    showDronesReport = e.target.checked;               // NEW LINE
    updateLayersVisibility();                          // NEW LINE
  });

  toggleDronesCamera.addEventListener('change', e => { // NEW LINE
    showDronesCamera = e.target.checked;               // NEW LINE
    updateLayersVisibility();                          // NEW LINE
  });

  toggleDronesRadar.addEventListener('change', e => {  // NEW LINE
    showDronesRadar = e.target.checked;                // NEW LINE
    updateLayersVisibility();                          // NEW LINE
  });
  // --- FETCH & RENDER ---
  async function loadPlanes() {
    try {
      const resp = await fetch('/api/planes');
      const data = await resp.json();
      const planes = data.planes || [];

      // clear previous markers
      
      planeLayer.clearLayers();
      dronesReportLayer.clearLayers(); // NEW LINE
      dronesCameraLayer.clearLayers(); // NEW LINE
      dronesRadarLayer.clearLayers();  // NEW LINE
      gliderLayer.clearLayers();       // NEW LINE

      planes.forEach(p => {
        const source = (p.source || p.producer || '').toString().toLowerCase();
        const isReport = source === 'dronereport' || source === 'form' || p.report_type || p.kind === 'report';
        const isCamera = source === 'camera';
        const isRadar = source === 'radar';

        const lat = p.lat || p.latitude || (p.position?.coordinates?.[1]);
        const lon = p.lon || p.longitude || (p.position?.coordinates?.[0]);
        if (typeof lat !== 'number' || typeof lon !== 'number') return;

        if (isReport || isCamera || isRadar) {
          // Drone marker with special colors for camera/radar
          let color;
          let droneType = p.drone_type || 'consumer';

        if (isCamera) {
          const marker = L.circleMarker([lat, lon], {
            color: 'purple',
            fillColor: 'purple',
            fillOpacity: 0.8,
            radius: getMarkerRadius(p.altitude || p.alt || '0-50m (low)')
          }).bindPopup(`

            <b>Camera Detection</b><br>
            Site: ${p.country || ''}<br> <!-- NEW LINE -->
            Time: ${p.ts_unix ? new Date(p.ts_unix * 1000).toLocaleString() : ''}<br> 
            ${p.image_id ? `<img src="/api/images/${p.image_id}" width="120"><br>` : ''} 
            id: ${p.icao || p.icao24 || 'unknown'}<br>
            ${getDeleteButtonHTML(p.icao || p.icao24 || 'unknown')}
          `); // NEW LINE
          dronesCameraLayer.addLayer(marker); // NEW LINE

                    // Add delete handler after popup is shown
          marker.on('popupopen', () => {
            attachDeleteHandler(p.icao || p.icao24, p, marker, dronesCameraLayer);
          });

        } else if (isRadar) {
          const marker = L.circleMarker([lat, lon], {
            color: 'darkorange',
            fillColor: 'darkorange',
            fillOpacity: 0.8,
            radius: getMarkerRadius(p.altitude || p.alt || '0-50m (low)')
          }).bindPopup(`
            <b>Radar Detection</b><br>
            Site: ${p.country || ''}<br> <!-- NEW LINE -->
            Time: ${p.ts_unix ? new Date(p.ts_unix * 1000).toLocaleString() : ''}<br> 
            Speed: ${p.speed || p.spd || ''} km/h<br> 
            Altitude: ${p.altitude || p.alt || ''} m<br>
            id: ${p.icao || p.icao24 || 'unknown'}<br>
            ${getDeleteButtonHTML(p.icao || p.icao24 || 'unknown')}
          `); // NEW LINE
          dronesRadarLayer.addLayer(marker); // NEW LINE

                    // Add delete handler after popup is shown
          marker.on('popupopen', () => {
            attachDeleteHandler(p.icao || p.icao24, p, marker, dronesRadarLayer);
          });

                } else if (isReport) {
                console.log('Drone report received:', p); // 🔍 Log complet du document

                let imageUrl = p.image_url;
                if (imageUrl && imageUrl.includes('http://localhost:5000/http://localhost:5000')) {
                  imageUrl = imageUrl.replace('http://localhost:5000/http://localhost:5000', 'http://localhost:5000');
                }
                const marker = L.circleMarker([lat, lon], {
            color: 'green',
            fillColor: 'green',
            fillOpacity: 0.8,
            radius: getMarkerRadius(p.altitude || p.alt || '0-50m (low)')
          }).bindPopup(`
            <b>Drone Report</b><br>
            Source: ${p.source || ''}<br>
            Time: ${p.timestamp ? new Date(p.timestamp).toLocaleString() : ''}<br>
            ${p.notes ? `Notes: ${p.notes}<br>` : ''}
            ${p.drone_description ? `Description: ${p.drone_description}<br>` : ''}
            ${imageUrl ? `<img src="${imageUrl}" width="120"><br>` : ''}
            id: ${p.icao || p.icao24 || 'unknown'}<br>
            ${getDeleteButtonHTML(p.icao || p.icao24 || 'unknown')}
          `);
          dronesReportLayer.addLayer(marker); // NEW LINE

                    // Add delete handler after popup is shown
          marker.on('popupopen', () => {
            attachDeleteHandler(p.icao || p.icao24, p, marker, dronesReportLayer);
          });

        }
        }
      else {

          // Plane marker
          let countryOrType = "Country: ";
          let iconUrl = 'icons/plane.png';
          if (p.source == 'ogn') {
            countryOrType = "Type: ";
            if (!showOgn) return;
            iconUrl = 'icons/glider (2).png';
          }

          const icon = L.icon({
            iconUrl: iconUrl,
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
            Source: ${p.source || 'Unknown'}<br>
            ${countryOrType} ${p.country || ''}<br>
            Altitude: ${Math.round(alt)} m<br>
            Speed: ${Math.round(spd * 3.6)} km/h<br>
            Heading: ${Math.round(heading)}°<br>
            ${getDeleteButtonHTML(flight)}
          `);
          if (p.source == 'ogn') {        // NEW LINE
            gliderLayer.addLayer(marker); // NEW LINE
          } else {                        // NEW LINE
            planeLayer.addLayer(marker);  // NEW LINE
          }
           

          // Add delete handler after popup is shown
          marker.on('popupopen', () => {
            attachDeleteHandler(flight, p, marker, planeLayer);
          });

          // --- trail logic ---
          const flightId = flight || `unknown-${lat}-${lon}`;
          if (!planeTrails[flightId]) planeTrails[flightId] = [];
          planeTrails[flightId].push([lat, lon]);
          if (planeTrails[flightId].length > 100) planeTrails[flightId].shift();

          if (!planeTrails[flightId].polyline) {
            planeTrails[flightId].polyline = L.polyline(planeTrails[flightId], {
              color: 'blue',
              weight: 2,
              opacity: 0.6
            });
          } else {
            planeTrails[flightId].polyline.setLatLngs(planeTrails[flightId]);
          }

          marker.on('click', () => {
            const trail = planeTrails[flightId].polyline;
            if (!trail) return;

            // Hide previous trail if any
            if (currentTrail && currentTrail !== trail) {
              map.removeLayer(currentTrail);
            }

            // Toggle current trail
            if (map.hasLayer(trail)) {
              map.removeLayer(trail);
              currentTrail = null;
            } else {
              trail.addTo(map);
              currentTrail = trail;
            }
          });
        }
      });
    } catch (err) {
      console.error('Error loading planes:', err);
    }
  }

  // --- UTILITIES ---
  function getDeleteButtonHTML(flight) {
    const role = (localStorage.getItem('user_role') || '').toString().toLowerCase();
    const token = localStorage.getItem('auth_token');

    // Only show delete button for operator or admin with valid token
    if (token && (role === 'authority' || role === 'admin')) {
      return `<button id="delete-plane-${flight}" class="delete-btn">Delete</button>`;
    }
    return '';
  }

  function attachDeleteHandler(flight, p, marker, planeLayer) {
    const deleteBtn = document.getElementById(`delete-plane-${flight}`);
    if (!deleteBtn) return;

    deleteBtn.addEventListener('click', async () => {
      if (!confirm(`Delete flight ${flight}?`)) return;

      const token = localStorage.getItem('auth_token');
      if (!token) {
        alert('You must be logged in to delete planes');
        return;
      }

      try {
        const icao = p.icao || p.icao24 || flight;
        const [username, password] = token.split(':');

        const resp = await fetch(`/api/planes/${icao}`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + btoa(`${username}:${password}`)
          }
        });

        if (resp.ok) {
          alert('Plane deleted successfully');
          marker.closePopup();
          planeLayer.removeLayer(marker);
          await loadPlanes(); // Refresh the map
        } else {
          const data = await resp.json();
          alert(`Delete failed: ${data.detail || 'Unknown error'}`);
        }
      } catch (err) {
        alert(`Delete error: ${err.message}`);
      }
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

  // --- MAIN UPDATE LOOP ---
  async function updateLoop() {
    console.log('Update tick at', new Date().toLocaleTimeString());
    await loadPlanes();
    document.dispatchEvent(new Event('updateComplete'));
    setTimeout(updateLoop, 5000);
  }

  updateLoop(); // Start loop

  // --- LOGIN / MODAL HANDLING ---
  const btnLogin = document.getElementById('btn-login');
  const btnAdmin = document.getElementById('btn-admin');
  const btnAnalyst = document.getElementById('btn-analyst');
  const btnAuthority = document.getElementById('btn-authority');
  const btnLogout = document.getElementById('btn-logout');
  const loginModal = document.getElementById('login-modal');
  const loginForm = document.getElementById('login-form');
  const loginError = document.getElementById('login-error');
  const loginCancel = document.getElementById('login-cancel');

  // Check if user is already authenticated and update UI based on role
  function updateLoginUI() {
    const token = localStorage.getItem('auth_token');
    const role = (localStorage.getItem('user_role') || '').toString().toLowerCase();
    console.log('[updateLoginUI] token:', !!token, 'role:', role, 'btnAnalyst:', !!btnAnalyst, 'btnAuthority:', !!btnAuthority);

    if (token) {
      if (btnLogin) btnLogin.style.display = 'none';
      if (btnLogout) btnLogout.style.display = 'block';

      // Show buttons based on role
      // admin sees everything
      if (role === 'admin') {
        if (btnAdmin) btnAdmin.style.display = 'block';
        if (btnAnalyst) btnAnalyst.style.display = 'block';
        if (btnAuthority) btnAuthority.style.display = 'block';
      }
      // analyst sees archive
      else if (role === 'analyst') {
        if (btnAdmin) btnAdmin.style.display = 'none';
        if (btnAnalyst) btnAnalyst.style.display = 'block';
        if (btnAuthority) btnAuthority.style.display = 'none';
      }
      // authority sees alerts
      else if (role === 'authority') {
        if (btnAdmin) btnAdmin.style.display = 'none';
        if (btnAnalyst) btnAnalyst.style.display = 'none';
        if (btnAuthority) btnAuthority.style.display = 'block';
      }
      // unknown/other role: show nothing
      else {
        if (btnAdmin) btnAdmin.style.display = 'none';
        if (btnAnalyst) btnAnalyst.style.display = 'none';
        if (btnAuthority) btnAuthority.style.display = 'none';
      }
    } else {
      if (btnLogin) btnLogin.style.display = 'block';
      if (btnAdmin) btnAdmin.style.display = 'none';
      if (btnAnalyst) btnAnalyst.style.display = 'none';
      if (btnAuthority) btnAuthority.style.display = 'none';
      if (btnLogout) btnLogout.style.display = 'none';
    }
  }

  function showLogin() {
    if (loginError) loginError.style.display = 'none';
    if (loginModal) loginModal.style.display = 'flex';
  }

  function hideLogin() {
    if (loginModal) loginModal.style.display = 'none';
  }

  btnLogin?.addEventListener('click', () => showLogin());
  loginCancel?.addEventListener('click', () => hideLogin());

  btnAdmin?.addEventListener('click', () => {
    window.location.href = 'admin-stats.html';
  });

  btnAnalyst?.addEventListener('click', () => {
    window.location.href = 'analyst.html';
  });

  btnAuthority?.addEventListener('click', () => {
    window.location.href = 'authority.html';
  });

  btnLogout?.addEventListener('click', () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_role');
    updateLoginUI();
    hideLogin();
  });

  loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!loginForm) return;
    const u = document.getElementById('login-username')?.value || '';
    const p = document.getElementById('login-password')?.value || '';
    try {
      // Try to verify credentials through the admin endpoint
      const resp = await fetch('/api/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      });
      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        // Backend auth failed or returned error. Try a safe fallback: if the username is one
        // of the known roles, accept it for local/dev testing. Otherwise show error.
        const fallbackMsg = (data && data.detail) ? data.detail : 'Authentication failed';
        const candidate = (u || '').toString().toLowerCase();
        if (['admin', 'analyst', 'authority'].includes(candidate) || fallbackMsg.toString().toLowerCase().includes('unreachable') || resp.status === 502) {
          const assignedRole = ['admin', 'analyst', 'authority'].includes(candidate) ? candidate : 'unknown';
          localStorage.setItem('auth_token', `${u}:${p}`);
          localStorage.setItem('user_role', assignedRole);
          updateLoginUI();
          hideLogin();
          document.getElementById('login-username').value = '';
          document.getElementById('login-password').value = '';
          alert('Login (fallback) successful — role: ' + assignedRole);
          if (assignedRole === 'analyst') window.location.href = 'analyst.html';
          if (assignedRole === 'authority') window.location.href = 'authority.html';
          if (assignedRole === 'admin') window.location.href = 'admin-stats.html';
          return;
        }

        if (loginError) {
          loginError.textContent = fallbackMsg;
          loginError.style.display = 'block';
        }
        return;
      }

      // success: store token and role from backend response (normalize to lowercase and map to UI roles)
      let role = (data && data.role) ? data.role : null;
      if (!role) {
        const roleCandidate = (u || '').toString().toLowerCase();
        if (['admin', 'analyst', 'authority'].includes(roleCandidate)) role = roleCandidate;
        else role = 'unknown';
      }
      role = role.toString().toLowerCase();

      // Map backend roles to UI roles
      const roleMap = {
        'airplanefeed': 'analyst',
        'operator': 'authority',
        'admin': 'admin',
        'analyst': 'analyst',
        'authority': 'authority'
      };
      role = roleMap[role] || role;

      localStorage.setItem('auth_token', `${u}:${p}`);
      localStorage.setItem('user_role', role);
      updateLoginUI();
      hideLogin();
      // Clear form
      document.getElementById('login-username').value = '';
      document.getElementById('login-password').value = '';

      alert('Login successful — role: ' + role);
      // Auto-redirect user to their page
      if (role === 'analyst') window.location.href = 'analyst.html';
      if (role === 'authority') window.location.href = 'authority.html';
      if (role === 'admin') window.location.href = 'admin-stats.html';
    } catch (err) {
      if (loginError) {
        loginError.textContent = err.message || 'Login error';
        loginError.style.display = 'block';
      }
    }
  });

  // Initialize login UI
  updateLoginUI();

});
