"""
GitHub IP Sync - Download GitHub IP ranges grouped by service.
"""

from .base import BaseCollector, Collected

# Keys of https://api.github.com/meta holding IP ranges
GITHUB_SERVICES = [
    'hooks',
    'web',
    'api',
    'git',
    'actions',
    'actions_macos',
    'pages',
    'packages',
    'importer',
    'github_enterprise_importer',
    'copilot'
]


class GitHubIP(BaseCollector):
    """GitHub IP ranges by service."""

    key = "github"
    name = "GitHub"

    def collect(self) -> Collected:
        data = self.fetch(self.config['url']).json()
        services = {
            service: set(data[service])
            for service in GITHUB_SERVICES
            if isinstance(data.get(service), list)
        }
        return Collected(ips=set().union(*services.values()), groups={'services': services})
