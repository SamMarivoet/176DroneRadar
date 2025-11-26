from fastapi import APIRouter, Depends
from .. import database
from ..auth import verify_admin
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('backend.statistics')

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get('/overview')
async def get_statistics_overview(username: str = Depends(verify_admin)):
    """Get overall statistics about planes, drones, and archived reports."""
    try:
        # Count total planes (including drones)
        total_planes = await database.db.planes.count_documents({})
        
        # Count active planes (OpenSky/ADS-B)
        active_planes = await database.db.planes.count_documents({'source': {'$in': ['opensky', 'ogn']}})
        
        # Count active drone reports
        active_drones = await database.db.planes.count_documents({'source': 'dronereport'})
        
        # Count archived drone reports
        archived_reports = await database.db.archive.count_documents({})
        
        # Get statistics by source
        sources = await database.db.planes.distinct('source')
        source_stats = {}
        for source in sources:
            count = await database.db.planes.count_documents({'source': source})
            source_stats[source or 'unknown'] = count
        
        # Get statistics by drone type
        drone_types = await database.db.planes.distinct('drone_type', {'source': 'dronereport'})
        drone_type_stats = {}
        for drone_type in drone_types:
            if drone_type:  # Skip None
                count = await database.db.planes.count_documents({
                    'source': 'dronereport',
                    'drone_type': drone_type
                })
                drone_type_stats[drone_type] = count
        
        # Get statistics by altitude (for drone reports)
        altitudes = await database.db.planes.distinct('altitude', {'source': 'dronereport'})
        altitude_stats = {}
        for altitude in altitudes:
            if altitude:  # Skip None
                count = await database.db.planes.count_documents({
                    'source': 'dronereport',
                    'altitude': altitude
                })
                altitude_stats[altitude] = count
        
        return {
            'total_planes': total_planes,
            'active_planes': active_planes,
            'active_drones': active_drones,
            'archived_reports': archived_reports,
            'by_source': source_stats,
            'drone_types': drone_type_stats,
            'drone_altitudes': altitude_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting statistics overview: {e}", exc_info=True)
        return {
            'error': str(e),
            'total_planes': 0,
            'active_planes': 0,
            'active_drones': 0,
            'archived_reports': 0
        }


@router.get('/recent-activity')
async def get_recent_activity(hours: int = 24, username: str = Depends(verify_admin)):
    """Get recent activity statistics for the last N hours."""
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Recent planes (updated or created in the last N hours)
        recent_planes = await database.db.planes.count_documents({
            'last_seen': {'$gte': cutoff_time}
        })
        
        # Recent drone reports
        recent_drones = await database.db.planes.count_documents({
            'source': 'dronereport',
            'last_seen': {'$gte': cutoff_time}
        })
        
        # Recently archived reports
        recently_archived = await database.db.archive.count_documents({
            'archived_at': {'$gte': cutoff_time}
        })
        
        # Get the newest reports
        cursor = database.db.planes.find(
            {'last_seen': {'$gte': cutoff_time}},
            projection={'icao': 1, 'callsign': 1, 'flight': 1, 'source': 1, 'last_seen': 1, '_id': 0}
        ).sort('last_seen', -1).limit(10)
        recent_updates = await cursor.to_list(length=10)
        
        # Get the newest archived reports
        arch_cursor = database.db.archive.find(
            {'archived_at': {'$gte': cutoff_time}},
            projection={'drone_description': 1, 'timestamp': 1, 'archived_at': 1, '_id': 0}
        ).sort('archived_at', -1).limit(10)
        recent_archived_list = await arch_cursor.to_list(length=10)
        
        return {
            'period_hours': hours,
            'recent_planes': recent_planes,
            'recent_drones': recent_drones,
            'recently_archived': recently_archived,
            'latest_updates': recent_updates,
            'latest_archived': recent_archived_list,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}", exc_info=True)
        return {
            'error': str(e),
            'period_hours': hours,
            'recent_planes': 0,
            'recent_drones': 0,
            'recently_archived': 0
        }


@router.get('/top-countries')
async def get_top_countries(limit: int = 10, username: str = Depends(verify_admin)):
    """Get top countries by number of planes."""
    try:
        pipeline = [
            {'$match': {'country': {'$exists': True, '$ne': None}}},
            {'$group': {'_id': '$country', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': limit}
        ]
        
        cursor = database.db.planes.aggregate(pipeline)
        results = await cursor.to_list(length=limit)
        
        country_stats = {item['_id']: item['count'] for item in results}
        
        return {
            'top_countries': country_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting top countries: {e}", exc_info=True)
        return {
            'error': str(e),
            'top_countries': {}
        }


@router.get('/database-health')
async def get_database_health(username: str = Depends(verify_admin)):
    """Get database health and statistics."""
    try:
        # Get collection sizes
        planes_stats = await database.db.command('collStats', 'planes')
        archive_stats = await database.db.command('collStats', 'archive')
        users_stats = await database.db.command('collStats', 'users')
        
        # Size in MB
        planes_size_mb = planes_stats.get('size', 0) / (1024 * 1024)
        archive_size_mb = archive_stats.get('size', 0) / (1024 * 1024)
        users_size_mb = users_stats.get('size', 0) / (1024 * 1024)
        
        return {
            'collections': {
                'planes': {
                    'count': planes_stats.get('count', 0),
                    'size_mb': round(planes_size_mb, 2),
                    'avg_doc_size': planes_stats.get('avgObjSize', 0)
                },
                'archive': {
                    'count': archive_stats.get('count', 0),
                    'size_mb': round(archive_size_mb, 2),
                    'avg_doc_size': archive_stats.get('avgObjSize', 0)
                },
                'users': {
                    'count': users_stats.get('count', 0),
                    'size_mb': round(users_size_mb, 2)
                }
            },
            'total_size_mb': round((planes_size_mb + archive_size_mb + users_size_mb), 2),
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting database health: {e}", exc_info=True)
        return {
            'error': str(e),
            'collections': {}
}
