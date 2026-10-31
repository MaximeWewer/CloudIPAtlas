"""
Googlebot IP Sync - Download Google crawler and fetcher IP ranges.
"""

from .base import BotListCollector


class GooglebotIP(BotListCollector):
    """Google crawlers (Googlebot, special crawlers) and user-triggered fetchers, by list."""

    key = "googlebot"
    name = "Googlebot"
    # Most specific first: "user-triggered-fetchers" is a prefix of "user-triggered-fetchers-google"
    bots = ['user-triggered-fetchers-google', 'user-triggered-fetchers', 'special-crawlers', 'googlebot']
