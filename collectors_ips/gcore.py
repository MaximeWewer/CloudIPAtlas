"""
Gcore IP Sync - Download Gcore CDN IP ranges.
"""

from .base import BaseCollector, Collected, json_strings


class GcoreIP(BaseCollector):
    """Gcore CDN IP ranges."""

    key = "gcore"
    name = "Gcore"

    def collect(self) -> Collected:
        # {"addresses": [...], "addresses_v6": [...]}
        return Collected(ips=json_strings(self.fetch(self.config['url']).json()))
