"""
Googlebot IP Sync - Download Google crawler IP ranges.
"""

from .base import BaseCollector, Collected, json_prefixes


class GooglebotIP(BaseCollector):
    """Google crawler IP ranges."""

    key = "googlebot"
    name = "Googlebot"

    def collect(self) -> Collected:
        return Collected(ips=json_prefixes(self.fetch(self.config['url']).json()))
