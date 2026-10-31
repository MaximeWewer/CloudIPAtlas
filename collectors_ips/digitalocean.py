"""
DigitalOcean IP Sync - Download DigitalOcean IP ranges grouped by city.
"""

import csv
import io
from collections import defaultdict

from .base import BaseCollector, Collected


class DigitalOceanIP(BaseCollector):
    """DigitalOcean IP ranges by region (city)."""

    key = "digitalocean"
    name = "DigitalOcean"

    def collect(self) -> Collected:
        text = self.fetch(self.config['url']).text

        all_ips = []
        regions = defaultdict(set)
        # CSV geofeed: IP, Country, Region, City, Postal Code
        for row in csv.reader(io.StringIO(text)):
            if len(row) < 4:
                continue
            ip, country, city = row[0].strip(), row[1].strip(), row[3].strip()
            all_ips.append(ip)
            if city:
                regions[f"{city}, {country}" if country else city].add(ip)

        return Collected(ips=all_ips, groups={'regions': regions})
