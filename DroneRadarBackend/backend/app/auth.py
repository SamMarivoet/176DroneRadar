from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import bcrypt
from . import database
from collections import defaultdict
from datetime import datetime, timedelta
import logging

security = HTTPBasic()
logger = logging.getLogger('backend.auth')

# In-memory store for failed login attempts (use Redis in production)
failed_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 60


def _is_ip_locked(ip: str) -> bool:
    """Check if IP is locked due to too many failed attempts."""
    if ip not in failed_attempts:
        return False
    
    # Clean old attempts (older than LOCKOUT_MINUTES)
    cutoff = datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)
    failed_attempts[ip] = [attempt for attempt in failed_attempts[ip] if attempt > cutoff]
    
    # Check if still over limit
    return len(failed_attempts[ip]) >= MAX_ATTEMPTS


def _record_failed_attempt(ip: str):
    """Record a failed login attempt."""
    failed_attempts[ip].append(datetime.now())


def _clear_failed_attempts(ip: str):
    """Clear failed attempts after successful login."""
    if ip in failed_attempts:
        del failed_attempts[ip]


async def _verify_password(username: str, password: str) -> bool:
    """Verify password against database."""
    try:
        user = await database.get_user(username)
        if not user:
            return False
        
        stored_hash = user.get('password_hash')
        if not stored_hash:
            return False
        
        # Ensure both are bytes
        password_bytes = password.encode('utf-8') if isinstance(password, str) else password
        stored_hash_bytes = stored_hash if isinstance(stored_hash, bytes) else stored_hash.encode('utf-8')
        
        return bcrypt.checkpw(password_bytes, stored_hash_bytes)
    except Exception as e:
        logger.error(f"Error verifying password for user {username}: {e}", exc_info=True)
        return False


async def _get_user_role(username: str) -> str:
    """Get user role from database."""
    try:
        user = await database.get_user(username)
        if not user:
            return None
        return user.get('role', None)
    except Exception as e:
        logger.error(f"Error getting role for user {username}: {e}", exc_info=True)
        return None


async def _verify_credentials_with_ratelimit(credentials: HTTPBasicCredentials, request: Request) -> bool:
    """Verify credentials and enforce rate limiting on failed attempts."""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Check if IP is locked
    if _is_ip_locked(client_ip):
        remaining_attempts = failed_attempts[client_ip]
        if remaining_attempts:
            oldest_attempt = min(remaining_attempts)
            unlock_time = oldest_attempt + timedelta(minutes=LOCKOUT_MINUTES)
            minutes_remaining = int((unlock_time - datetime.now()).total_seconds() / 60)
            logger.warning(f"IP {client_ip} is locked due to too many failed login attempts")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {minutes_remaining} minutes.",
                headers={"WWW-Authenticate": "Basic"},
            )
    
    # Verify password
    is_valid = await _verify_password(credentials.username, credentials.password)
    
    if not is_valid:
        _record_failed_attempt(client_ip)
        remaining = MAX_ATTEMPTS - len(failed_attempts[client_ip])
        logger.warning(f"Failed login attempt for user {credentials.username} from IP {client_ip}. Remaining attempts: {remaining}")
        
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Account locked for {LOCKOUT_MINUTES} minutes.",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Successful login - clear failed attempts
    _clear_failed_attempts(client_ip)
    return True


async def verify_admin(credentials: HTTPBasicCredentials = Depends(security), request: Request = None):
    """Verify admin role with rate limiting."""
    await _verify_credentials_with_ratelimit(credentials, request)
    
    role = await _get_user_role(credentials.username)
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


async def verify_airplanefeed(credentials: HTTPBasicCredentials = Depends(security), request: Request = None):
    """Verify airplanefeed role (or admin) with rate limiting."""
    await _verify_credentials_with_ratelimit(credentials, request)
    
    role = await _get_user_role(credentials.username)
    if role not in ["airplanefeed", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Airplanefeed or admin role required",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


async def verify_operator(credentials: HTTPBasicCredentials = Depends(security), request: Request = None):
    """Verify operator role (or admin) with rate limiting."""
    await _verify_credentials_with_ratelimit(credentials, request)
    
    role = await _get_user_role(credentials.username)
    if role not in ["operator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin role required",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# Export for use in other modules
__all__ = ['security', 'verify_admin', 'verify_airplanefeed', 'verify_operator', '_verify_password', '_get_user_role']