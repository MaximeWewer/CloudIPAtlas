"""
DigitalOcean IP Sync - Download DigitalOcean IP ranges grouped by city.
"""

from .base import GeofeedCollector


class DigitalOceanIP(GeofeedCollector):
    """DigitalOcean IP ranges by region (city), from its geofeed."""

    key = "digitalocean"
    name = "DigitalOcean"
