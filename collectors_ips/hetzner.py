"""
Hetzner IP Sync - Download Hetzner IPv4 ranges grouped by city.
"""

from .base import Collected, GeofeedCollector
from .ip_utils import is_ipv6


def ipv4_only(ips) -> list:
    return [ip for ip in ips if not is_ipv6(ip)]


class HetznerIP(GeofeedCollector):
    """
    Hetzner IPv4 ranges by region (city), from its geofeed.

    IPv6 is skipped: the geofeed lists ~150k non-contiguous /6x prefixes (~15 MB of output).
    """

    key = "hetzner"
    name = "Hetzner"

    def collect(self) -> Collected:
        result = super().collect()
        return Collected(
            ips=ipv4_only(result.ips),
            groups={subdir: {name: ipv4_only(ips) for name, ips in groups.items()}
                    for subdir, groups in result.groups.items()}
        )
