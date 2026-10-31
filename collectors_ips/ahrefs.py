"""
Ahrefs IP Sync - Download Ahrefs SEO crawler IP addresses.
"""

from .base import BaseCollector, Collected


class AhrefsIP(BaseCollector):
    """Ahrefs crawler IP addresses."""

    key = "ahrefs"
    name = "Ahrefs"

    def collect(self) -> Collected:
        data = self.fetch(self.config['url']).json()
        # { "ips": [ { "ip_address": ... } ] }
        return Collected(ips=[
            entry.get('ip_address', '')
            for entry in data.get('ips', [])
            if isinstance(entry, dict)
        ])
