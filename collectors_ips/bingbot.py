"""
Bingbot IP Sync - Download Bing crawler IP ranges.
"""

from .base import BaseCollector, Collected, json_prefixes


class BingbotIP(BaseCollector):
    """Bing crawler IP ranges."""

    key = "bingbot"
    name = "Bingbot"

    def collect(self) -> Collected:
        return Collected(ips=json_prefixes(self.fetch(self.config['url']).json()))
