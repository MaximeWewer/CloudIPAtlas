"""
Azure IP Sync - Download Azure Service Tags grouped by service and region.
"""

import logging
from collections import defaultdict

from .base import BaseCollector, Collected

logger = logging.getLogger(__name__)


class AzureIP(BaseCollector):
    """Azure IP ranges by service tag and region."""

    key = "azure"
    name = "Azure"
    timeout = 60

    def collect(self) -> Collected:
        data = self.fetch(self.config['url']).json()
        logger.info(f"[Azure] version: {data.get('changeNumber', 'N/A')}")

        all_ips = set()
        services, regions = defaultdict(set), defaultdict(set)
        for value in data.get('values', []):
            # Tag name format: "ServiceName" or "ServiceName.Region"
            service, _, region = value.get('name', '').partition('.')
            address_prefixes = value.get('properties', {}).get('addressPrefixes', [])

            all_ips.update(address_prefixes)
            services[service].update(address_prefixes)
            if region:
                regions[region].update(address_prefixes)

        return Collected(ips=all_ips, groups={'services': services, 'regions': regions})
