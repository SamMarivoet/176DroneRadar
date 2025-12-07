from fastapi import APIRouter, Depends
from .. import database
from ..auth import verify_admin
from datetime import datetime
import logging

logger = logging.getLogger('backend.sensors')
router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.get('/list')
async def get_sensors(username: str = Depends(verify_admin)):
    """Get all active sensors (cameras/radars) and their status"""
    try:
        sensors_col = database.db.sensors
        
        sensors = await sensors_col.find({}, projection={'_id': False}).to_list(None)
        
        return {
            'sensors': sensors,
            'total': len(sensors)
        }
    except Exception as e:
        logger.error(f"Error getting sensors: {e}")
        return {'error': str(e), 'sensors': []}


@router.post('/toggle-status')
async def toggle_sensor_status(body: dict, username: str = Depends(verify_admin)):
    """Toggle sensor on/off (active/inactive)"""
    try:
        country = body.get('country')  # Changed from site_name
        source = body.get('source')
        is_active = body.get('is_active')
        
        if not country or not source:
            return {'error': 'Missing country or source'}
        
        sensors_col = database.db.sensors
        result = await sensors_col.update_one(
            {'country': country, 'source': source},  # Changed from site_name
            {
                '$set': {
                    'is_active': is_active,
                    'last_modified': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return {
            'success': True,
            'country': country,
            'source': source,
            'is_active': is_active
        }
    except Exception as e:
        logger.error(f"Error toggling sensor: {e}")
        return {'error': str(e)}


@router.get('/by-source/{source}')
async def get_sensors_by_source(source: str, username: str = Depends(verify_admin)):
    """Get all reports by source type (camera/radar/dronereport)"""
    try:
        planes_col = database.db.planes
        
        reports = await planes_col.find({'source': source}, projection={'_id': False}).to_list(None)

        # Group by site_name
        by_site = {}
        for report in reports:
            site = report.get('country', 'Unknown')
            if site not in by_site:
                by_site[site] = []
            by_site[site].append(report)
        
        return {
            'source': source,
            'total_count': len(reports),
            'by_site': by_site
        }
    except Exception as e:
        logger.error(f"Error getting reports by source: {e}")
        return {'error': str(e)}