"""
Yandex IP Sync - Extract Yandex network IP ranges (used by YandexBot) from yandex.com/ips.
"""

from bs4 import BeautifulSoup

from .base import BaseCollector, Collected


class YandexIP(BaseCollector):
    """Yandex network IP ranges."""

    key = "yandex"
    name = "Yandex"

    def collect(self) -> Collected:
        text = BeautifulSoup(self.fetch(self.config['url']).text, 'html.parser').get_text('\n')
        # One range per line; non-IP lines are filtered out later
        return Collected(ips=[line.strip() for line in text.splitlines()])
