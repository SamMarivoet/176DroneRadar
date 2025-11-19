from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel
from .. import database
from ..auth import _verify_password, verify_admin
from ..dependencies import limiter
import logging

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