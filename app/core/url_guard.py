"""SSRF protection for HTTP column type.

Validates URLs before making outbound requests, blocking private IPs,
localhost, and dangerous protocols.
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger("clay-webhook-os")

# Private/reserved IP ranges that must be blocked
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),         # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),      # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),     # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]

_ALLOWED_SCHEMES = {"https", "http"}

_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "metadata.google.internal"}


def validate_url(url: str, *, allow_http: bool = True) -> str | None:
    """Validate a URL for safe outbound requests.

    Returns None if the URL is safe, or an error message string if blocked.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL format"

    # Scheme check
    if not parsed.scheme:
        return "URL must include a scheme (https:// or http://)"
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return f"Blocked scheme: {parsed.scheme}:// — only http(s) allowed"
    if parsed.scheme == "http" and not allow_http:
        return "HTTP not allowed — use HTTPS"

    # Hostname check
    hostname = parsed.hostname
    if not hostname:
        return "URL must include a hostname"
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return f"Blocked hostname: {hostname}"

    # IP resolution check — resolve hostname and check against private ranges
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                for network in _BLOCKED_NETWORKS:
                    if ip in network:
                        return f"Blocked private/reserved IP: {ip_str} (resolved from {hostname})"
            except ValueError:
                continue
    except socket.gaierror:
        # Can't resolve — let the HTTP client handle the DNS error
        pass

    return None
