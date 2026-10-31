"""
Zscaler IP Sync - Download Zscaler cloud IP ranges.
"""

from .base import BaseCollector, Collected


def strings_in(value):
    """Yield every string nested anywhere in a JSON value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings_in(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_in(item)


class ZscalerIP(BaseCollector):
    """Zscaler security cloud IP ranges."""

    key = "zscaler"
    name = "Zscaler"

    def collect(self) -> Collected:
        all_ips = []
        for url in self.config['urls']:
            # IPs are nested at various depths; non-IP strings are filtered out later
            all_ips += strings_in(self.fetch(url).json())
        return Collected(ips=all_ips)
