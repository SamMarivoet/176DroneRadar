from slowapi import Limiter
from fastapi import Request


def get_real_ip(request: Request) -> str:
    """Extract real client IP from proxy headers."""
    # Check forwarded headers
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_real_ip)