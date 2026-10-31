"""
Exoscale IP Sync - Download Exoscale IP ranges grouped by zone.
"""

from collections import defaultdict

from .base import BaseCollector, Collected


class ExoscaleIP(BaseCollector):
    """Exoscale IP ranges by zone."""

    key = "exoscale"
    name = "Exoscale"

    def collect(self) -> Collected:
        data = self.fetch(self.config['url']).json()

        all_ips = []
        regions = defaultdict(set)
        # { "prefixes": [ { "IPv4Prefix" or "IPv6Prefix", "zone" } ] }
        for prefix in data.get('prefixes', []):
            if not isinstance(prefix, dict):
                continue
            ip = prefix.get('IPv4Prefix') or prefix.get('IPv6Prefix', '')
            all_ips.append(ip)
            if prefix.get('zone'):
                regions[prefix['zone']].add(ip)

        return Collected(ips=all_ips, groups={'regions': regions})
