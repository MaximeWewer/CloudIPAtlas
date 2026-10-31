"""
Bunny CDN IP Sync - Download Bunny CDN edge server IPs.
"""

from .base import BaseCollector, Collected, json_strings


class BunnyCDNIP(BaseCollector):
    """Bunny CDN edge server IPs (IPv4 and IPv6 lists)."""

    key = "bunnycdn"
    name = "Bunny CDN"

    def collect(self) -> Collected:
        # Each URL returns a JSON array of IPs
        return Collected(ips=[ip for url in self.config['urls'] for ip in json_strings(self.fetch(url).json())])
