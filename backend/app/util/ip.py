import ipaddress

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


def anonymize_ip(ip: str) -> str:
    """Anonymize an IP address for GDPR-compliant logging.

    Zeroes the last octet for IPv4 (e.g. 192.168.1.42 -> 192.168.1.0)
    and the last 80 bits for IPv6, matching the anonymization approach
    used by the University of Regensburg's Matomo deployment.

    Non-parseable values (e.g. ``"unknown"``) are returned as-is.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip

    if isinstance(addr, ipaddress.IPv4Address):
        # Zero the last octet (/24 mask)
        network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
        return str(network.network_address)

    # IPv6: zero the last 80 bits (/48 mask)
    network = ipaddress.IPv6Network(f"{ip}/48", strict=False)
    return str(network.network_address)
