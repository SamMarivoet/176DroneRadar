from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from .config import settings

security = HTTPBasic()

async def verify_airplanefeed(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify airplanefeed user credentials (or admin)."""
    is_airplanefeed = (
        secrets.compare_digest(credentials.username, "airplanefeed") and
        secrets.compare_digest(credentials.password, settings.AIRPLANEFEED_PASSWORD)
    )
    is_admin = (
        secrets.compare_digest(credentials.username, "admin") and
        secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    )
    
    if not (is_airplanefeed or is_admin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


async def verify_operator(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify operator user credentials (or admin)."""
    is_operator = (
        secrets.compare_digest(credentials.username, "operator") and
        secrets.compare_digest(credentials.password, settings.OPERATOR_PASSWORD)
    )
    is_admin = (
        secrets.compare_digest(credentials.username, "admin") and
        secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    )
    
    if not (is_operator or is_admin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username