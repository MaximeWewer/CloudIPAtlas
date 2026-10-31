"""
Cloudflare IP Sync - Download Cloudflare IPv4 and IPv6 ranges.
"""

from .base import BaseCollector, Collected


class CloudflareIP(BaseCollector):
    """Cloudflare CDN and network IP ranges."""

    key = "cloudflare"
    name = "Cloudflare"

    def collect(self) -> Collected:
        all_ips = []
        for url in self.config['urls']:
            # Plain text, one range per line
            all_ips += [line.strip() for line in self.fetch(url).text.splitlines()]
        return Collected(ips=all_ips)
