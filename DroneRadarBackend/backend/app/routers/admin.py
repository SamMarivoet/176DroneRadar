from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .. import database
from ..auth import verify_admin
import logging

logger = logging.getLogger('backend.admin')

router = APIRouter(prefix="/admin", tags=["admin"])


class PasswordUpdate(BaseModel):
    username: str
    new_password: str


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