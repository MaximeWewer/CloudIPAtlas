"""
Scaleway IP Sync - Extract Scaleway IP ranges from the network information page.
"""

import re
from collections import defaultdict

from bs4 import BeautifulSoup

from .base import BaseCollector, Collected

IP_PATTERN = re.compile(
    r'\b(?:'
    r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/[0-9]{1,2})?|'  # IPv4 with optional CIDR
    r'(?:[0-9a-fA-F:]+:){2,}(?:[0-9a-fA-F:]+)(?:/[0-9]{1,3})?'  # IPv6 with optional CIDR
    r')\b'
)
ZONE_PATTERN = re.compile(r'\b(fr-par-[1-3]|nl-ams-[1-3]|pl-waw-[1-3])\b', re.IGNORECASE)

ZONE_NAMES = {
    'fr-par-1': 'France-Paris-1',
    'fr-par-2': 'France-Paris-2',
    'fr-par-3': 'France-Paris-3',
    'nl-ams-1': 'Netherlands-Amsterdam-1',
    'nl-ams-2': 'Netherlands-Amsterdam-2',
    'nl-ams-3': 'Netherlands-Amsterdam-3',
    'pl-waw-1': 'Poland-Warsaw-1',
    'pl-waw-2': 'Poland-Warsaw-2',
    'pl-waw-3': 'Poland-Warsaw-3'
}


class ScalewayIP(BaseCollector):
    """Scaleway IP ranges by service and availability zone."""

    key = "scaleway"
    name = "Scaleway"
    timeout = 60

    def collect(self) -> Collected:
        # Source is the MDX of the docs page; get_text() drops the embedded components
        text = BeautifulSoup(self.fetch(self.config['url']).text, 'html.parser').get_text()

        all_ips = set()
        services, regions = defaultdict(set), defaultdict(set)
        current_service, current_region = "General", None

        for line in text.split('\n'):
            line = line.strip()

            # Section headings switch the current service or country
            if 'IPv4' in line and len(line) < 20:
                current_service = "Core-IPv4-Ranges"
            elif 'IPv6' in line and len(line) < 20:
                current_service = "Core-IPv6-Ranges"
            elif 'DNS cache servers' in line or 'NTP servers' in line:
                current_service = "DNS-NTP-Servers"
            elif 'France' in line and len(line) < 20:
                current_region = 'France'
            elif 'Netherlands' in line and len(line) < 20:
                current_region = 'Netherlands'
            elif 'Poland' in line and len(line) < 20:
                current_region = 'Poland'
            elif 'Rdate server' in line:
                current_service = "Rdate-Server"
            elif 'Backup server' in line:
                current_service = "Backup-Server"
            elif 'RPN VPN' in line:
                current_service = "RPN-VPN"
            elif 'Monitoring' in line:
                current_service = "Monitoring"
            elif 'Dedibox' in line and len(line) < 50:
                current_service = "Dedibox-Services"

            zone = ZONE_PATTERN.search(line)
            if zone:
                code = zone.group(1).lower()
                current_region = ZONE_NAMES.get(code, code)

            for ip in IP_PATTERN.findall(line):
                all_ips.add(ip)
                services[current_service].add(ip)
                if current_region:
                    regions[current_region].add(ip)

        return Collected(ips=all_ips, groups={'services': services, 'regions': regions})
