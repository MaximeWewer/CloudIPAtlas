"""
Fastly IP Sync - Download Fastly CDN IP ranges.
"""

from .base import BaseCollector, Collected


class FastlyIP(BaseCollector):
    """Fastly CDN IP ranges."""

    key = "fastly"
    name = "Fastly"

    def collect(self) -> Collected:
        data = self.fetch(self.config['url']).json()
        # Ranges are listed under several keys ("addresses", "ipv6_addresses", ...)
        return Collected(ips=[
            ip
            for value in data.values() if isinstance(value, list)
            for ip in value if isinstance(ip, str)
        ])
