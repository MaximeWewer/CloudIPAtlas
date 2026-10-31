"""
OpenAI IP Sync - Download OpenAI crawler IP ranges (ChatGPT-User, GPTBot, OAI-SearchBot).
"""

from .base import BotListCollector


class OpenAIIP(BotListCollector):
    """OpenAI crawler IP ranges by bot."""

    key = "openai"
    name = "OpenAI"
    bots = ['chatgpt-user', 'gptbot', 'searchbot']
