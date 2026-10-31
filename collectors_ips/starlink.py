"""
Starlink IP Sync - Download Starlink IP ranges.
"""

import csv
import io

from .base import BaseCollector, Collected


class StarlinkIP(BaseCollector):
    """Starlink satellite internet IP ranges."""

    key = "starlink"
    name = "Starlink"

    def collect(self) -> Collected:
        text = self.fetch(self.config['url']).text
        # CSV geofeed: keep every field that is an IP
        return Collected(ips=[field.strip() for row in csv.reader(io.StringIO(text)) for field in row])
