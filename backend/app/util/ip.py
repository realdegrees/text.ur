from starlette.requests import HTTPConnection


def get_client_ip(conn: HTTPConnection) -> str:
    """Extract client IP from proxy headers or direct connection.

    Works with both ``Request`` and ``WebSocket`` objects since they
    share the ``HTTPConnection`` base class.

    Checks headers in order:
    1. X-Forwarded-For (set by reverse proxies like Traefik)
    2. X-Real-IP (alternative proxy header)
    3. Direct connection IP (fallback for non-proxied requests)
    """
    # X-Forwarded-For contains comma-separated list, first is original
    forwarded_for = conn.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # Fallback to X-Real-IP
    real_ip = conn.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Last resort: direct connection (works for non-proxied requests)
    return conn.client.host if conn.client else "unknown"
