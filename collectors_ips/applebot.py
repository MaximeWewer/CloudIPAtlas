"""
Applebot IP Sync - Download Apple crawler (Applebot) IP ranges.
"""

from .base import BaseCollector, Collected, json_prefixes


class ApplebotIP(BaseCollector):
    """Apple crawler (Applebot) IP ranges."""

    key = "applebot"
    name = "Applebot"

    def collect(self) -> Collected:
        return Collected(ips=json_prefixes(self.fetch(self.config['url']).json()))
