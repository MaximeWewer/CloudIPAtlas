"""
Vultr IP Sync - Download Vultr IP ranges grouped by city.
"""

from collections import defaultdict

from .base import BaseCollector, Collected


class VultrIP(BaseCollector):
    """Vultr IP ranges by region (city)."""

    key = "vultr"
    name = "Vultr"

    def collect(self) -> Collected:
        data = self.fetch(self.config['url']).json()

        all_ips = []
        regions = defaultdict(set)
        # { "subnets": [ { "ip_prefix", "city", "alpha2code", ... } ] }
        for subnet in data.get('subnets', []):
            if not isinstance(subnet, dict):
                continue
            ip = subnet.get('ip_prefix', '')
            city, country = subnet.get('city', ''), subnet.get('alpha2code', '')
            all_ips.append(ip)
            if city:
                regions[f"{city}, {country}" if country else city].add(ip)

        return Collected(ips=all_ips, groups={'regions': regions})
