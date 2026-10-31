"""
Outscale IP Sync - Extract Outscale public IP ranges from the documentation page.
"""

import re
from collections import defaultdict

from bs4 import BeautifulSoup

from .base import BaseCollector, Collected

CIDR_PATTERN = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}\b')


class OutscaleIP(BaseCollector):
    """Outscale public IP ranges by region."""

    key = "outscale"
    name = "Outscale"
    timeout = 60

    def collect(self) -> Collected:
        soup = BeautifulSoup(self.fetch(self.config['url']).text, 'html.parser')

        regions = defaultdict(set)
        # Table rows: region | public IP ranges
        for row in soup.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            region = cells[0].get_text(strip=True)
            if not region or 'Region' in region or 'Public IP' in region:
                continue
            regions[region].update(CIDR_PATTERN.findall(cells[1].get_text(strip=True)))

        return Collected(ips=set().union(*regions.values()), groups={'regions': regions})
