# Quick Start: Admin Statistics Dashboard

## 30-Second Setup

1. **Restart Backend** (to load new statistics router and CORS):
   ```bash
   docker compose -f DroneRadarBackend/docker-compose.yml restart
   ```

2. **Open Map GUI**:
   ```
   http://localhost:3000
   ```

3. **Login**:
    - Click "Login" button
    - Username: `admin`
    - Password: `pass`
    - Click "Sign In"

4. **View Statistics**:
   - Click "📊 Admin Stats" button
   - Dashboard loads with real-time data

## What You'll See

### Dashboard Tabs

| Tab | Content |
|-----|---------|
| **Overview** | Source breakdown, drone types, altitudes |
| **Activity** | Last 24 hours stats, latest updates, recent archives |
| **Detailed Stats** | Complete metric breakdown |
| **Health** | Database size, collection stats, performance |

### Key Metrics

- **Total Active Objects**: All planes + drones combined
- **Active ADS-B Planes**: OpenSky/OGN aircraft
- **Drone Reports**: Form submissions and sightings
- **Archived**: Aged-out reports (>1 hour)

## Features

✅ Real-time data from backend  
✅ Auto-refresh every 30 seconds  
✅ Manual refresh button  
✅ Session authentication  
✅ Responsive design (mobile/tablet/desktop)  
✅ Professional UI with visualizations  
✅ Color-coded metrics  

## Files Created/Modified

### New Files
- `Map_GUI/frontend/admin-stats.html` - Dashboard page
- `DroneRadarBackend/backend/app/routers/statistics.py` - API endpoints
- `ADMIN_STATISTICS.md` - Full documentation
- `IMPLEMENTATION_SUMMARY.md` - Technical details

### Modified Files
- `DroneRadarBackend/backend/app/main.py` - Added CORS & statistics router
- `Map_GUI/frontend/index.html` - Added admin buttons
- `Map_GUI/frontend/app.js` - Enhanced authentication

## Authentication Flow

```
Login Credentials → Verify with Backend → Store Token → Show Admin Button
                                                                    ↓
                                                          Navigate to Dashboard
                                                                    ↓
                                                        Use Token for API Calls
                                                                    ↓
                                                      Display Statistics
```

## API Endpoints (Admin Only)

```bash
# Overview statistics
curl -u admin:pass http://localhost:8000/statistics/overview

# Last 24 hours activity
curl -u admin:pass http://localhost:8000/statistics/recent-activity?hours=24

# Top countries (top 10) - optional (not used in Belgium-only deployment)
# curl -u admin:pass http://localhost:8000/statistics/top-countries

# Database health
curl -u admin:pass http://localhost:8000/statistics/database-health
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Login fails | Check admin password (default: `pass`) |
| Admin button doesn't appear | Clear browser cache, reload page |
| No data in dashboard | Verify backend is running, check browser console |
| CORS errors | Restart backend to load CORS middleware |
| Page blank | Check browser console for JavaScript errors |

## Customization

### Change Auto-Refresh (admin-stats.html)
```javascript
// Line ~500: Change 30000 (30 sec) to any milliseconds
setInterval(refreshData, 30000); // 30 seconds
setInterval(refreshData, 60000); // 60 seconds
```

### Change Color Scheme
Edit CSS gradients in `<style>` section:
```css
/* Main color */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

## Next Steps

1. Deploy to production server
2. Update CORS origins in backend for production URL
3. Use HTTPS for security
4. Change default admin password
5. Monitor database growth
6. Consider adding charts/graphs

## Support

For detailed documentation, see:
- `ADMIN_STATISTICS.md` - Complete feature guide
- `IMPLEMENTATION_SUMMARY.md` - Technical architecture

## Architecture Overview

```
Map GUI (index.html)
    ↓ [Login]
    ↓ [Redirect if auth]
Admin Dashboard (admin-stats.html)
    ↓ [API Calls]
Backend (statistics.py endpoints)
    ↓ [Query]
MongoDB
    ↓ [Data]
Backend → Dashboard Display
```

## Key Files

- **Frontend**: `Map_GUI/frontend/admin-stats.html`
- **Backend**: `DroneRadarBackend/backend/app/routers/statistics.py`
- **Integration**: `DroneRadarBackend/backend/app/main.py`
- **Auth**: `Map_GUI/frontend/app.js`

## Security Features

🔒 HTTP Basic Auth  
🔒 Admin-only endpoints  
🔒 Rate limiting (5 attempts/hour)  
🔒 IP-based lockout  
🔒 CORS protected  
🔒 Token-based session  

---

**Ready to use!** Start at step 1 of the 30-Second Setup above.
