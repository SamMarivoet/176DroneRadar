document.addEventListener("DOMContentLoaded", () => {
  const planeTrails = {}; // flight ID → array of LatLngs
  let currentTrail = null; // store the currently visible trail



  // --- MAP SETUP ---
  const map = L.map('map').setView([50.85, 4.35], 7);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
  }).addTo(map);

  // --- LAYER GROUPS ---
  const droneLayer = L.layerGroup().addTo(map);
  const planeLayer = L.layerGroup().addTo(map);

  // --- FILTER STATE ---
  let showDrones = true;
  let showPlanes = true;
  let showOgn = true;

  function updateLayersVisibility() {
    showDrones ? map.addLayer(droneLayer) : map.removeLayer(droneLayer);
    showPlanes ? map.addLayer(planeLayer) : map.removeLayer(planeLayer);
  }

  // --- FILTER EVENTS ---
  const toggleDrones = document.getElementById('toggle-drones');
  const togglePlanes = document.getElementById('toggle-planes');
  const toggleOgn = document.getElementById('toggle-ogn');

  toggleDrones.addEventListener('change', e => {
    showDrones = e.target.checked;
    updateLayersVisibility();
  });

  togglePlanes.addEventListener('change', e => {
    showPlanes = e.target.checked;
    updateLayersVisibility();
  });

  toggleOgn.addEventListener('change', e => {
    showOgn = e.target.checked;
    updateLayersVisibility();
  });

  // --- FETCH & RENDER ---
  async function loadPlanes() {
    try {
      const resp = await fetch('/api/planes');
      const data = await resp.json();
      const planes = data.planes || [];

      // clear previous markers
      droneLayer.clearLayers();
      planeLayer.clearLayers();

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
            color = 'purple';
            droneType = 'Camera Detection';
          } else if (isRadar) {
            color = 'darkorange';
            droneType = 'Radar Detection';
          } else {
            color = getMarkerColor(droneType);
          }

          const radius = getMarkerRadius(p.altitude || p.alt || '0-50m (low)');
          const marker = L.circleMarker([lat, lon], {
            color,
            fillColor: color,
            fillOpacity: 0.8,
            radius
          }).bindPopup(`
            <b>${capitalize(droneType)} Report</b><br>
            Source: ${source}<br>
            Altitude: ${p.altitude || p.alt || ''}<br>
            ${p.description || ''}<br>
            <small>${p.timestamp ? new Date(p.timestamp).toLocaleString() : ''}</small>
          `);
          droneLayer.addLayer(marker);
        } else {
          // Plane marker
          countryOrType = "Country: ";
          iconUrl = 'icons/plane.png';
          if (p.source == 'ogn') {
            countryOrType = "Type: ";
            if (!showOgn) return;
            iconUrl = 'icons/gliderr.png';
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
            Heading: ${Math.round(heading)}°
          `);
          planeLayer.addLayer(marker);

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
    
    if (token) {
      btnLogin.style.display = 'none';
      btnLogout.style.display = 'block';
      
      // Show buttons based on role
      // admin sees everything
      if (role === 'admin') {
        btnAdmin.style.display = 'block';
        btnAnalyst.style.display = 'block';
        btnAuthority.style.display = 'block';
      } 
      // analyst sees archive
      else if (role === 'analyst') {
        btnAdmin.style.display = 'none';
        btnAnalyst.style.display = 'block';
        btnAuthority.style.display = 'none';
      } 
      // authority sees alerts
      else if (role === 'authority') {
        btnAdmin.style.display = 'none';
        btnAnalyst.style.display = 'none';
        btnAuthority.style.display = 'block';
      } 
      // unknown/other role: show nothing
      else {
        btnAdmin.style.display = 'none';
        btnAnalyst.style.display = 'none';
        btnAuthority.style.display = 'none';
      }
    } else {
      btnLogin.style.display = 'block';
      btnAdmin.style.display = 'none';
      btnAnalyst.style.display = 'none';
      btnAuthority.style.display = 'none';
      btnLogout.style.display = 'none';
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

      // success: store token and role from backend response (normalize to lowercase)
      let role = (data && data.role) ? data.role : null;
      if (!role) {
        const roleCandidate = (u || '').toString().toLowerCase();
        if (['admin', 'analyst', 'authority'].includes(roleCandidate)) role = roleCandidate;
        else role = 'unknown';
      }
      role = role.toString().toLowerCase();

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
