"""
Zscaler IP Sync - Download Zscaler cloud IP ranges.
"""

from .base import BaseCollector, Collected, json_strings


class ZscalerIP(BaseCollector):
    """Zscaler security cloud IP ranges."""

    key = "zscaler"
    name = "Zscaler"

    def collect(self) -> Collected:
        # IPs are nested at various depths of each JSON document
        return Collected(ips=[ip for url in self.config['urls'] for ip in json_strings(self.fetch(url).json())])
