"""
Meta IP Sync - Download Meta/Facebook IP ranges grouped by location.
"""

from collections import defaultdict

from .base import BaseCollector, Collected


class MetaIP(BaseCollector):
    """Meta IP ranges by region (city, country)."""

    key = "meta"
    name = "Meta"

    def collect(self) -> Collected:
        text = self.fetch(self.config['url']).text

        all_ips = []
        regions = defaultdict(set)
        # Geofeed lines with "#" comments: IP,Country,Region,City,
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [part.strip() for part in line.split(',')]
            ip = parts[0]
            country = parts[1] if len(parts) > 1 else ''
            city = parts[3] if len(parts) > 3 else ''
            all_ips.append(ip)
            if country:
                regions[f"{city}, {country}" if city else country].add(ip)

        return Collected(ips=all_ips, groups={'regions': regions})
