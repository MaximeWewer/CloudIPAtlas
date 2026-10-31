"""
OVH IP Sync - Extract OVH web hosting cluster IPs from the documentation page.
"""

import re

from bs4 import BeautifulSoup

from .base import BaseCollector, Collected
from .ip_utils import is_valid_ip, sanitize_filename

CLUSTER_PATTERN = re.compile(r'Cluster\s+(\d+)', re.IGNORECASE)
COUNTRY_CODE_PATTERN = re.compile(r'[A-Z]{2}')


def ips_in(element) -> set:
    """Return every valid IPv4/IPv6 address found in an element's text."""
    tokens = re.findall(r'[0-9a-fA-F:.]+', element.get_text(' '))
    return {t for t in tokens if ('.' in t or ':' in t) and is_valid_ip(t)}


class OVHIP(BaseCollector):
    """
    OVH web hosting IPs, written in three groups:
    - clusters/: all IPs of each cluster (listed in index.md)
    - services/: CDN and outgoing gateway IPs of each cluster
    - countries/: geolocation IPs per country code, across clusters
    """

    key = "ovh"
    name = "OVH"
    timeout = 60
    services_group = "clusters"

    def file_stem(self, group_name: str) -> str:
        # Keep country codes uppercase (countries/FR_...)
        return group_name if COUNTRY_CODE_PATTERN.fullmatch(group_name) else sanitize_filename(group_name)

    def collect(self) -> Collected:
        soup = BeautifulSoup(self.fetch(self.config['url']).text, 'html.parser')

        all_ips = set()
        clusters, services, countries = {}, {}, {}

        # Each cluster is a <details> block: a <summary> holding the "Cluster NNN"
        # heading, a per-country table, then <p> labels ("Shared CDN",
        # "outgoing IP address") each followed by a <div> holding the IP.
        for details in soup.find_all('details'):
            summary = details.find('summary')
            match = CLUSTER_PATTERN.search(summary.get_text() if summary else '')
            if not match:
                continue
            cluster = f"Cluster-{match.group(1).zfill(3)}"
            cluster_ips = clusters[cluster] = set()

            # Per-country table: Country | Country Code | IPv4 | IPv6
            table = details.find('table')
            for row in table.find_all('tr') if table else []:
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                row_ips = set().union(*(ips_in(cell) for cell in cells[2:]))
                cluster_ips |= row_ips
                country = cells[1].get_text(strip=True).upper()
                if row_ips and COUNTRY_CODE_PATTERN.fullmatch(country):
                    countries.setdefault(country, set()).update(row_ips)

            all_ips |= cluster_ips

            for label in details.find_all('p'):
                text = label.get_text(' ').lower()
                if 'cdn' in text:
                    service = 'cdn'
                elif 'gateway' in text or 'outgoing' in text:
                    service = 'gateway'
                else:
                    continue
                target = label.find_next_sibling()
                ips = {ip for ip in ips_in(target) if '.' in ip} if target else set()
                services.setdefault(f"{cluster.lower()}_{service}", set()).update(ips)
                all_ips |= ips

        return Collected(ips=all_ips, groups={'clusters': clusters, 'services': services, 'countries': countries})
