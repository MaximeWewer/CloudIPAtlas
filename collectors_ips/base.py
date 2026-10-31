"""
Base class shared by all provider collectors.

A collector only implements collect(): download its source and return the IPs,
optionally split into named groups (services, regions, ...). generate_files()
then writes every output file, index.md included.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

import requests

from .ip_utils import (
    is_valid_ip,
    write_ip_group,
    generate_index_markdown,
    calculate_total_ips,
    calculate_detailed_stats,
    sanitize_filename,
    print_summary,
    ensure_directory
)

logger = logging.getLogger(__name__)

OUTPUT_ROOT = "cloud_ips"


@dataclass
class Collected:
    """
    Result of a collection.

    Attributes:
        ips: Every IP address / CIDR range of the provider
        groups: Output subdirectory (e.g. "services", "regions") -> {group name: IPs}
    """
    ips: Iterable[str]
    groups: Dict[str, Dict[str, Iterable[str]]] = field(default_factory=dict)


class BaseCollector(ABC):
    """Download a provider's IP ranges and write them under cloud_ips/<key>/."""

    key: str                         # config.json key and output directory name
    name: str                        # Display name used in index.md and logs
    timeout: int = 30                # HTTP timeout in seconds
    services_group: str = "services" # Group listed in the index "Services" table
    regions_group: str = "regions"   # Group listed in the index "Regions" table

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)[self.key]
        self.output_dir = os.path.join(OUTPUT_ROOT, self.key)

    @abstractmethod
    def collect(self) -> Collected:
        """Download the provider source and extract its IPs."""

    def fetch(self, url: str) -> requests.Response:
        """GET a URL, raising on network errors and HTTP error statuses."""
        logger.info(f"[{self.name}] Downloading from: {url}")
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response

    def file_stem(self, group_name: str) -> str:
        """File name (without suffix) used for a group."""
        return sanitize_filename(group_name)

    def generate_files(self) -> None:
        """Collect IPs and write global, per-group and index.md files."""
        result = self.collect()

        all_ips = {ip for ip in result.ips if is_valid_ip(ip)}
        if not all_ips:
            raise ValueError("No IP ranges found, source format may have changed")

        ensure_directory(self.output_dir)
        all_ipv4, all_ipv6 = write_ip_group(os.path.join(self.output_dir, "ips"), all_ips)

        counts = {}
        for subdir, groups in result.groups.items():
            counts[subdir] = {}
            for group_name, ips in groups.items():
                ips = {ip for ip in ips if is_valid_ip(ip)}
                if ips:
                    write_ip_group(os.path.join(self.output_dir, subdir, self.file_stem(group_name)), ips)
                    counts[subdir][group_name] = len(ips)

        services = counts.get(self.services_group) or None
        regions = counts.get(self.regions_group) or None
        stats = calculate_detailed_stats(all_ips, all_ipv4, all_ipv6)

        index_content = generate_index_markdown(
            provider_name=self.name,
            total_ranges=stats['total'],
            ipv4_ranges=stats['ipv4_ranges'],
            ipv6_ranges=stats['ipv6_ranges'],
            ipv4_count=stats['ipv4_count'],
            ipv6_count=calculate_total_ips(all_ipv6),
            services=services,
            regions=regions,
            ipv4_single=stats['ipv4_single'],
            ipv6_single=stats['ipv6_single'],
            ipv4_ranges_only=stats['ipv4_ranges_only'],
            ipv6_ranges_only=stats['ipv6_ranges_only']
        )
        with open(os.path.join(self.output_dir, "index.md"), 'w', encoding='utf-8') as f:
            f.write(index_content)

        summary = {**stats, 'output_dir': self.output_dir}
        for subdir, group_counts in counts.items():
            summary[subdir] = len(group_counts)
        print_summary(self.name, summary)


def json_prefixes(data: dict) -> List[str]:
    """IPs of the Google-style format: {"prefixes": [{"ipv4Prefix" or "ipv6Prefix": ...}]}."""
    return [
        prefix.get('ipv4Prefix') or prefix.get('ipv6Prefix', '')
        for prefix in data.get('prefixes', [])
        if isinstance(prefix, dict)
    ]


class BotListCollector(BaseCollector):
    """Crawler published as one Google-style JSON list per bot (config "urls")."""

    bots: List[str]  # Bot names, each matched against the URL to label its IPs

    def collect(self) -> Collected:
        services = {}
        for url in self.config['urls']:
            bot = next((b for b in self.bots if b in url), 'unknown')
            services.setdefault(bot, set()).update(json_prefixes(self.fetch(url).json()))
        return Collected(ips=set().union(*services.values()), groups={'services': services})
