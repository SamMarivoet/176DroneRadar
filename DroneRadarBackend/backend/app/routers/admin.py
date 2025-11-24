from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel
from .. import database
from ..auth import _verify_password, verify_admin
from ..dependencies import limiter
import logging
from typing import List
from bson import ObjectId

logger = logging.getLogger('backend.admin')

router = APIRouter(prefix="/admin", tags=["admin"])


class PasswordUpdate(BaseModel):
    username: str
    new_password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post('/auth/verify')
@limiter.limit("5/hour")
async def verify_credentials(request: Request, login: LoginRequest):
    """Verify if username and password are correct. Public endpoint. Rate limited to 5 attempts per hour."""
    # First check if password is valid
    is_valid = await _verify_password(login.username, login.password)
    
    # If not valid, return error immediately - don't try to fetch user
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Only fetch user AFTER password is verified
    user = await database.get_user(login.username)
    
    # Double-check user exists (should always be true here)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Now safe to access user fields
    return {
        "status": "ok",
        "username": user['username'],
        "role": user.get('role', 'unknown'),
        "message": "Credentials valid"
    }


@router.post('/settings/passwords')
async def update_passwords(
    password_update: PasswordUpdate,
    admin_username: str = Depends(verify_admin)
):
    """Update a user's password. Admin only. Changes persist in database."""
    if password_update.username not in ["admin", "airplanefeed", "operator"]:
        raise HTTPException(status_code=404, detail="User not found")
    
    success = await database.update_user_password(password_update.username, password_update.new_password)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update password")
    
    logger.info(f"Admin {admin_username} updated password for user: {password_update.username}")
    
    return {
        "status": "ok",
        "username": password_update.username,
        "message": f"Password updated successfully for {password_update.username}"
    }


@router.get('/users')
async def list_users(username: str = Depends(verify_admin)):
    """List all users (admin only). Passwords are hidden."""
    cursor = database.db.users.find({}, {'password_hash': 0})
    users = await cursor.to_list(length=100)
    for user in users:
        if '_id' in user:
            user['_id'] = str(user['_id'])
    return users


@router.get('/drone-reports')
async def list_active_drone_reports(limit: int = 100, username: str = Depends(verify_admin)):
    """List active drone reports (source == 'dronereport'). Returns up to `limit` reports."""
    # Only return reports that are not hidden by admins. Use `admin_visible` flag for soft-hide.
    cursor = database.db.planes.find(
        {'source': 'dronereport', 'admin_visible': {'$ne': False}},
        projection={'_id': 1, 'drone_description': 1, 'timestamp': 1, 'latitude': 1, 'longitude': 1, 'image_id': 1, 'created_at': 1}
    ).sort('created_at', -1).limit(limit)
    results = await cursor.to_list(length=limit)
    # stringify _id
    for doc in results:
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
    return results


class DeleteReportsRequest(BaseModel):
    ids: List[str]


@router.post('/drone-reports/delete')
async def delete_drone_reports(payload: DeleteReportsRequest, username: str = Depends(verify_admin)):
    """Soft-hide one or more drone reports by their document _id values. Admin only.

    This does not remove documents from the database; it marks them with `admin_visible=false`
    so they will not appear in the admin listing but remain in the database for auditing.
    """
    if not payload.ids:
        raise HTTPException(status_code=400, detail='No ids provided')

    object_ids = []
    for s in payload.ids:
        try:
            object_ids.append(ObjectId(s))
        except Exception:
            raise HTTPException(status_code=400, detail=f'Invalid id: {s}')

    # Soft-hide only docs that are drone reports to avoid accidental modification
    res = await database.db.planes.update_many(
        {'_id': {'$in': object_ids}, 'source': 'dronereport'},
        {'$set': {'admin_visible': False}}
    )
    return {'matched_count': res.matched_count, 'modified_count': res.modified_count}