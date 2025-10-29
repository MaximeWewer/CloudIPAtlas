#!/usr/bin/env python3
"""
Zscaler IP Sync - Download Zscaler IP ranges and generate organized files.
"""

import os
import sys
import json
import logging
import requests
from typing import List

from .ip_utils import (
    separate_ipv4_ipv6,
    write_separated_ip_files,
    generate_index_markdown,
    calculate_total_ips,
    print_summary,
    ensure_directory,
    is_valid_ip,
    calculate_detailed_stats
)

logger = logging.getLogger(__name__)


class ZscalerIP:
    """Zscaler IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.urls = config['zscaler']['urls']
        self.output_dir = os.path.join("cloud_ips", "zscaler")

    def download_data(self) -> List[str]:
        all_ips = []
        for url in self.urls:
            logger.info(f"Downloading from: {url}")
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Extract IPs from JSON structure
                def extract_from_value(value):
                    if isinstance(value, str) and is_valid_ip(value):
                        all_ips.append(value)
                    elif isinstance(value, list):
                        for item in value:
                            extract_from_value(item)
                    elif isinstance(value, dict):
                        for v in value.values():
                            extract_from_value(v)

                extract_from_value(data)
                logger.info(f"Downloaded data from {url}")

            except requests.RequestException as e:
                logger.error(f"Error downloading from {url}: {e}")

        return list(set(all_ips))  # Remove duplicates

    def generate_files(self) -> None:
        logger.info("\nStarting IP range extraction...")
        ensure_directory(self.output_dir)
        all_ips_list = self.download_data()
        if not all_ips_list:
            logger.info("Warning: No IP ranges found!")
            return

        all_ipv4, all_ipv6 = separate_ipv4_ipv6(all_ips_list)
        all_combined = all_ipv4 + all_ipv6

        # Write global files with separation of single IPs and ranges
        base_path = os.path.join(self.output_dir, "ips")
        write_separated_ip_files(base_path, all_combined, "all")
        write_separated_ip_files(base_path, all_ipv4, "ipv4")
        write_separated_ip_files(base_path, all_ipv6, "ipv6")

        # Calculate detailed stats
        detailed_stats = calculate_detailed_stats(all_ips_list, all_ipv4, all_ipv6)

        index_content = generate_index_markdown(
            provider_name="Zscaler",
            total_ranges=detailed_stats['total'],
            ipv4_ranges=detailed_stats['ipv4_ranges'],
            ipv6_ranges=detailed_stats['ipv6_ranges'],
            ipv4_count=detailed_stats['ipv4_count'],
            ipv6_count=calculate_total_ips(all_ipv6),
            services=None,
            regions=None,
            ipv4_single=detailed_stats['ipv4_single'],
            ipv6_single=detailed_stats['ipv6_single'],
            ipv4_ranges_only=detailed_stats['ipv4_ranges_only'],
            ipv6_ranges_only=detailed_stats['ipv6_ranges_only']
        )
        with open(os.path.join(self.output_dir, "index.md"), 'w', encoding='utf-8') as f:
            f.write(index_content)

        stats = {
            **detailed_stats,
            'output_dir': self.output_dir
        }
        print_summary("Zscaler", stats)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = ZscalerIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
