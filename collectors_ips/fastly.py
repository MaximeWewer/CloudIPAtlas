"""
Fastly IP Sync - Download Fastly CDN IP ranges.
"""

from .base import BaseCollector, Collected, json_strings


class FastlyIP(BaseCollector):
    """Fastly CDN IP ranges."""

    key = "fastly"
    name = "Fastly"

    def collect(self) -> Collected:
        # {"addresses": [...], "ipv6_addresses": [...]}
        return Collected(ips=json_strings(self.fetch(self.config['url']).json()))
