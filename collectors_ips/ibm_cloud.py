"""
IBM Cloud IP Sync - Extract IBM Cloud public IP ranges from the documentation page.
"""

import logging
import re

from bs4 import BeautifulSoup

from .base import BaseCollector, Collected
from .ip_utils import is_private_ip

logger = logging.getLogger(__name__)

IPV4_PATTERN = re.compile(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/[0-9]{1,2})?')
IPV6_PATTERN = re.compile(r'(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}(?:/[0-9]{1,3})?')

# Documentation sections (h2/h3 headings) holding IP ranges
SERVICE_HEADERS = [
    'Front-end (public) network',
    'Load balancer IPs',
    'Back-end (private) network',
    'Customer private network space',
    'Service network (on back-end/private network)',
    'SSL VPN network (on back-end/private network)',
    'SSL VPN data centers',
    'Legacy networks',
    'Red Hat Enterprise Linux server requirements',
    'Windows virtual server instance requirements'
]


class IBMCloudIP(BaseCollector):
    """IBM Cloud public IP ranges by documentation section."""

    key = "ibm_cloud"
    name = "IBM Cloud"

    def collect(self) -> Collected:
        soup = BeautifulSoup(self.fetch(self.config['url']).text, 'html.parser')

        services = {}
        for header_text in SERVICE_HEADERS:
            header = soup.find(['h2', 'h3'], string=re.compile(re.escape(header_text), re.IGNORECASE))
            if not header:
                continue

            # Scan siblings until the next h2/h3
            section_ips = set()
            element = header.find_next_sibling()
            while element and element.name not in ('h2', 'h3'):
                texts = [element.get_text()] + [code.get_text() for code in element.find_all(['code', 'pre'])]
                for text in texts:
                    for ip in IPV4_PATTERN.findall(text) + IPV6_PATTERN.findall(text):
                        if not is_private_ip(ip):
                            section_ips.add(ip)
                element = element.find_next_sibling()

            if section_ips:
                services[header_text] = section_ips
                logger.info(f"[IBM Cloud] {header_text}: {len(section_ips)} IPs")

        return Collected(ips=set().union(*services.values()), groups={'services': services})
