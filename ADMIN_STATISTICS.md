# Admin Statistics Dashboard

## Overview

The Admin Statistics Dashboard is a new feature that allows authenticated administrators to view comprehensive statistics about the drone radar system, including real-time data about active planes, drone reports, archived data, and database health.

## Features

### 1. **Dashboard Overview**
- **Total Active Objects**: Combined count of all planes and drones currently being tracked
- **Active ADS-B Planes**: Real-time count of aircraft detected via ADS-B/OpenSky
- **Active Drone Reports**: Count of recent drone sightings from form submissions
- **Archived Reports**: Count of drone reports older than 1 hour that have been archived

### 2. **Statistics Tabs**

#### Overview Tab
- **Distribution by Source**: Shows breakdown of data sources (opensky, ogn, dronereport)
- **Drone Type Distribution**: Categorizes drones by type (consumer, commercial, military, racing)
- **Drone Altitude Distribution**: Shows altitude ranges of drone sightings
- **Top Countries**: (Not used — Belgium-only deployment)

#### Recent Activity Tab (Last 24 Hours)
- Real-time statistics for the last 24 hours
- Latest plane updates with timestamps
- Recently archived reports
- Activity trends

#### Detailed Statistics Tab
- Comprehensive breakdown of all metrics
- Collection-level statistics

#### Database Health Tab
- **Collection Statistics**: Size and document count for each collection
  - planes collection: Main active tracking data
  - archive collection: Archived drone reports
  - users collection: System user management
- **Database Size**: Total database size in MB
- **Average Document Size**: Average size of documents in each collection
- **Performance Metrics**: Information about database efficiency

## Accessing the Admin Dashboard

### From the Map GUI

1. Open the map interface at `http://localhost:3000` (or the configured URL)
2. Click the **Login** button in the sidebar
3. Enter your admin credentials (username: `admin`, default password: `pass`)
4. After successful login, an **Admin Stats** button will appear
5. Click **Admin Stats** to navigate to the dashboard

### Direct URL

You can also access the dashboard directly at:
```
http://localhost:3000/admin-stats.html
```

Note: The page will redirect to login if you're not authenticated.

## API Endpoints

The dashboard uses the following backend endpoints (all require admin authentication via HTTP Basic Auth):

### Overview Statistics
```
GET /statistics/overview
```
Returns:
- Total counts by source
- Drone type distribution
- Drone altitude distribution

### Recent Activity
```
GET /statistics/recent-activity?hours=24
```
Returns:
- Activity in the specified time period
- Latest updates and archived reports

### Top Countries (optional)
```
GET /statistics/top-countries?limit=10
```
Returns:
- Top N countries by aircraft count

Note: This endpoint is optional and not required for a Belgium-only deployment; the admin dashboard omits the Top Countries panel when running in a local/Belgium-only configuration.

### Database Health
```
GET /statistics/database-health
```
Returns:
- Collection sizes and document counts
- Database performance metrics

## Usage Examples

### Using curl

Authenticate and get statistics:
```bash
curl -u admin:pass http://localhost:8000/statistics/overview
```

Get recent activity from the last 12 hours:
```bash
curl -u admin:pass 'http://localhost:8000/statistics/recent-activity?hours=12'
```

Get top 20 countries (optional):
```bash
curl -u admin:pass 'http://localhost:8000/statistics/top-countries?limit=20'
```
Note: Not required for Belgium-only deployments; the admin UI hides the Top Countries panel by default.

### Using JavaScript (in frontend)

```javascript
const token = 'admin:pass';
const response = await fetch('http://localhost:8000/statistics/overview', {
    headers: {
        'Authorization': 'Basic ' + btoa(token),
        'Content-Type': 'application/json'
    }
});
const data = await response.json();
console.log(data);
```

## Authentication

The statistics endpoints use HTTP Basic Authentication:

1. **Username**: admin
2. **Password**: Set during system configuration (default: `pass`)

To verify credentials before accessing the dashboard:
```
POST /admin/auth/verify
```

The authentication is enforced at the backend level with:
- Rate limiting (5 attempts per hour)
- Failed attempt tracking
- IP-based lockout after 5 failed attempts
- 60-minute lockout period

## Dashboard Features

### Auto-Refresh
The dashboard automatically refreshes data every 30 seconds. You can also:
- Click the **Refresh** button for immediate update
- The timestamp shows when data was last updated

### Real-Time Updates
All statistics are fetched directly from the MongoDB database:
- Active planes and drones
- Archived reports
- Database health metrics

### Responsive Design
The dashboard is fully responsive and works on:
- Desktop browsers (full layout)
- Tablet devices (simplified layout)
- Mobile devices (stacked layout)

### Visual Indicators
- **Badges**: Color-coded source types (blue for info)
- **Progress Bars**: Percentage distribution visualization
- **Status Cards**: Key metrics with color coding

## Data Sources

The statistics dashboard pulls data from:

1. **planes collection**: Active ADS-B and drone report data
2. **archive collection**: Aged-out drone reports (>1 hour old)
3. **Database metrics**: MongoDB collection statistics

### Data Retention
- **Active Collection**: Live tracking data
- **Archive Collection**: Automatically archives drone reports older than 1 hour
- **Archiving**: Background task runs every 5 minutes

## Customization

### Adding New Statistics

To add new statistics endpoints, add methods to `DroneRadarBackend/backend/app/routers/statistics.py`:

```python
@router.get('/custom-stat')
async def get_custom_stat(username: str = Depends(verify_admin)):
    # Your custom logic here
    return {
        'custom_data': value,
        'timestamp': datetime.utcnow().isoformat()
    }
```

Then add a section in `admin-stats.html` to display the new data.

### Styling Customization

The dashboard uses CSS variables for theming. Modify the `<style>` section in `admin-stats.html`:

```css
/* Main gradient colors */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Stat card colors */
border-left-color: #667eea;  /* Primary */
border-left-color: #f093fb;  /* Drones */
border-left-color: #4facfe;  /* Archive */
border-left-color: #43e97b;  /* Health */
```

## Files Modified

### Backend
- `DroneRadarBackend/backend/app/main.py`: Added CORS middleware and statistics router
- `DroneRadarBackend/backend/app/routers/statistics.py`: New file with statistics endpoints

### Frontend
- `Map_GUI/frontend/index.html`: Added Admin Stats button
- `Map_GUI/frontend/app.js`: Enhanced authentication handling
- `Map_GUI/frontend/admin-stats.html`: New admin dashboard page

## Security Considerations

1. **Authentication Required**: All statistics endpoints require admin credentials
2. **Rate Limiting**: Failed login attempts are rate-limited to prevent brute force
3. **CORS Protection**: Backend allows cross-origin requests from localhost only (configurable)
4. **Session Management**: Authentication tokens are stored in browser localStorage
5. **HTTPS Recommended**: Use HTTPS in production to encrypt credentials

## Troubleshooting

### "Authentication failed" error
- Verify admin credentials are correct
- Check backend is running: `curl http://localhost:8000/health`
- Verify CORS is enabled in backend

### No data displayed
- Check backend connection: Open browser console and verify API calls succeed
- Verify admin credentials are correct
- Check MongoDB is running and has data

### Page won't load
- Clear browser cache and localStorage
- Check browser console for JavaScript errors
- Verify frontend is served from correct URL
- Check that both backend and frontend are running

### Slow dashboard performance
- Reduce auto-refresh interval in admin-stats.html (currently 30 seconds)
- Check MongoDB indexes are properly created
- Monitor database size in the Health tab

## Future Enhancements

Potential additions to the dashboard:

1. **Charts & Graphs**: Visual representations of statistics
2. **Export Data**: Download statistics as CSV/JSON
3. **Historical Data**: Time-series trends
4. **Alerts**: Configurable alerts for anomalies
5. **User Management**: Admin panel for user credentials
6. **Database Cleanup**: Manual controls for archiving and cleanup
7. **System Logs**: Application event logging
8. **Custom Reports**: Scheduled report generation

## Support

For issues or questions about the Admin Statistics Dashboard:
1. Check the troubleshooting section above
2. Review browser console for errors
3. Check backend logs: `docker logs droneradar-backend`
4. Review MongoDB logs if data-related issues occur
