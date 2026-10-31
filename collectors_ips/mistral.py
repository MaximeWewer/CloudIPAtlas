"""
Mistral IP Sync - Download Mistral AI fetcher (MistralAI-User) IP ranges.
"""

from .base import BaseCollector, Collected, json_prefixes


class MistralIP(BaseCollector):
    """Mistral AI fetcher (MistralAI-User) IP ranges."""

    key = "mistral"
    name = "Mistral"

    def collect(self) -> Collected:
        return Collected(ips=json_prefixes(self.fetch(self.config['url']).json()))
