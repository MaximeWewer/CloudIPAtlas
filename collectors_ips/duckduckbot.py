"""
DuckDuckBot IP Sync - Download DuckDuckGo crawler (DuckDuckBot) IP ranges.
"""

from .base import BaseCollector, Collected, json_prefixes


class DuckDuckBotIP(BaseCollector):
    """DuckDuckGo crawler (DuckDuckBot) IP ranges."""

    key = "duckduckbot"
    name = "DuckDuckBot"

    def collect(self) -> Collected:
        return Collected(ips=json_prefixes(self.fetch(self.config['url']).json()))
