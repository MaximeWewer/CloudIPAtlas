"""
CCBot IP Sync - Download Common Crawl crawler (CCBot) IP ranges.
"""

from .base import BaseCollector, Collected, json_prefixes


class CCBotIP(BaseCollector):
    """Common Crawl crawler (CCBot) IP ranges."""

    key = "ccbot"
    name = "CCBot"

    def collect(self) -> Collected:
        return Collected(ips=json_prefixes(self.fetch(self.config['url']).json()))
