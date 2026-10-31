"""
OCI IP Sync - Download Oracle Cloud IP ranges grouped by region and tag.
"""

import logging
from collections import defaultdict

from .base import BaseCollector, Collected

logger = logging.getLogger(__name__)


class OCIIP(BaseCollector):
    """Oracle Cloud IP ranges by region and service tag."""

    key = "oci"
    name = "OCI"
    timeout = 60

    def collect(self) -> Collected:
        data = self.fetch(self.config['url']).json()
        logger.info(f"[OCI] last updated: {data.get('last_updated_timestamp', 'N/A')}")

        all_ips = set()
        services, regions = defaultdict(set), defaultdict(set)
        for region_data in data.get('regions', []):
            region = region_data.get('region', 'UNKNOWN')
            for cidr_data in region_data.get('cidrs', []):
                cidr = cidr_data.get('cidr')
                if not cidr:
                    continue
                all_ips.add(cidr)
                regions[region].add(cidr)
                for tag in cidr_data.get('tags') or ['UNTAGGED']:
                    services[tag].add(cidr)

        return Collected(ips=all_ips, groups={'services': services, 'regions': regions})
