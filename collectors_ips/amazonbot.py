"""
Amazonbot IP Sync - Extract Amazon crawler IP ranges from its documentation page.
"""

import json

from bs4 import BeautifulSoup

from .base import BaseCollector, Collected, json_prefixes


class AmazonbotIP(BaseCollector):
    """Amazon crawler (Amazonbot) IP ranges."""

    key = "amazonbot"
    name = "Amazonbot"

    def collect(self) -> Collected:
        soup = BeautifulSoup(self.fetch(self.config['url']).text, 'html.parser')
        # The page embeds the Google-style JSON list in a code block
        ips = []
        for code in soup.find_all('code'):
            text = code.get_text()
            if '"prefixes"' in text:
                ips += json_prefixes(json.loads(text))
        return Collected(ips=ips)
