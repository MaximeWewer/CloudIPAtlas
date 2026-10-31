"""
Linode IP Sync - Download Linode/Akamai IP ranges grouped by city.
"""

from .base import GeofeedCollector


class LinodeIP(GeofeedCollector):
    """Linode IP ranges by region (city), from its geofeed."""

    key = "linode"
    name = "Linode"
