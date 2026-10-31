"""
Perplexity IP Sync - Download Perplexity crawler IP ranges (PerplexityBot, Perplexity-User).
"""

from .base import BotListCollector


class PerplexityIP(BotListCollector):
    """Perplexity crawler IP ranges by bot."""

    key = "perplexity"
    name = "Perplexity"
    bots = ['perplexitybot', 'perplexity-user']
