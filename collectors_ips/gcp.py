"""
GCP IP Sync - Download Google Cloud IP ranges grouped by service and scope.
"""

import logging
from collections import defaultdict

from .base import BaseCollector, Collected

logger = logging.getLogger(__name__)


class GCPIP(BaseCollector):
    """Google Cloud IP ranges by service and scope (region)."""

    key = "gcp"
    name = "GCP"
    timeout = 60

    def collect(self) -> Collected:
        data = self.fetch(self.config['url']).json()
        logger.info(f"[GCP] sync token: {data.get('syncToken', 'N/A')}, time: {data.get('creationTime', 'N/A')}")

        all_ips = set()
        services, regions = defaultdict(set), defaultdict(set)
        for prefix in data.get('prefixes', []):
            ip = prefix.get('ipv4Prefix') or prefix.get('ipv6Prefix')
            if not ip:
                continue
            all_ips.add(ip)
            services[prefix.get('service', 'UNKNOWN')].add(ip)
            regions[prefix.get('scope', 'global')].add(ip)

        return Collected(ips=all_ips, groups={'services': services, 'regions': regions})
