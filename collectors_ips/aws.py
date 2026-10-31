"""
AWS IP Sync - Download AWS IP ranges grouped by service and region.
"""

import logging
from collections import defaultdict

from .base import BaseCollector, Collected

logger = logging.getLogger(__name__)


class AWSIP(BaseCollector):
    """AWS IP ranges by service and region."""

    key = "aws"
    name = "AWS"
    timeout = 60

    def collect(self) -> Collected:
        data = self.fetch(self.config['url']).json()
        logger.info(f"[AWS] sync token: {data.get('syncToken', 'N/A')}, date: {data.get('createDate', 'N/A')}")

        prefixes = [(p.get('ip_prefix'), p) for p in data.get('prefixes', [])]
        prefixes += [(p.get('ipv6_prefix'), p) for p in data.get('ipv6_prefixes', [])]

        all_ips = set()
        services, regions = defaultdict(set), defaultdict(set)
        for ip, prefix in prefixes:
            if not ip:
                continue
            all_ips.add(ip)
            services[prefix.get('service', 'UNKNOWN')].add(ip)
            regions[prefix.get('region', 'GLOBAL')].add(ip)

        return Collected(ips=all_ips, groups={'services': services, 'regions': regions})
