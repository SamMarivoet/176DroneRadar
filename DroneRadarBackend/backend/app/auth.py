from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import bcrypt
from . import database

security = HTTPBasic()


async def _verify_password(username: str, password: str) -> bool:
    """Verify password against database."""
    user = await database.get_user(username)
    if not user:
        return False
    
    stored_hash = user.get('password_hash')
    if not stored_hash:
        return False
    
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash)


async def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin user credentials."""
    if credentials.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if not await _verify_password(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


async def verify_airplanefeed(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify airplanefeed user credentials (or admin)."""
    if credentials.username not in ["airplanefeed", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if not await _verify_password(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


async def verify_operator(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify operator user credentials (or admin)."""
    if credentials.username not in ["operator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if not await _verify_password(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


# Export for use in other modules
__all__ = ['security', 'verify_admin', 'verify_airplanefeed', 'verify_operator', '_verify_password']