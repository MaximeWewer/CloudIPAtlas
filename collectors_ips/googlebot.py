#!/usr/bin/env python3
"""
Googlebot IP Sync - Download Googlebot IP ranges and generate organized files.

Googlebot provides a JSON file with IPv4 and IPv6 prefixes used by Google's crawlers.
"""

import os
import sys
import json
import logging
import requests

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


class GooglebotIP:
    """Googlebot IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.url = config['googlebot']['url']
        self.output_dir = os.path.join("cloud_ips", "googlebot")

    def download_data(self) -> dict:
        logger.info(f"Downloading from: {self.url}")
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info("Successfully downloaded JSON data")
            return data
        except requests.RequestException as e:
            logger.error(f"Error: {e}")
            return {}

    def extract_ips(self, data: dict) -> list:
        """
        Extract IPs from Googlebot JSON.

        Returns:
            List of all IPs
        """
        all_ips = []

        # Googlebot JSON structure: { "prefixes": [ { "ipv4Prefix" or "ipv6Prefix" } ] }
        prefixes = data.get('prefixes', [])

        for prefix in prefixes:
            if isinstance(prefix, dict):
                # Get IPv4 or IPv6 prefix
                ip = prefix.get('ipv4Prefix') or prefix.get('ipv6Prefix', '')

                if ip and is_valid_ip(ip):
                    all_ips.append(ip)

        logger.info(f"Extracted {len(all_ips)} IPs from {len(prefixes)} prefixes")
        return all_ips

    def generate_files(self) -> None:
        logger.info("\nStarting IP range extraction...")
        ensure_directory(self.output_dir)

        data = self.download_data()
        if not data:
            return

        all_ips_list = self.extract_ips(data)
        if not all_ips_list:
            logger.info("Warning: No IP ranges found!")
            return

        # Separate IPv4/IPv6
        logger.info("Separating IPv4/IPv6...")
        all_ipv4, all_ipv6 = separate_ipv4_ipv6(all_ips_list)

        # Generate global files
        logger.info("Generating global files...")
        all_combined = all_ipv4 + all_ipv6
        base_path = os.path.join(self.output_dir, "ips")
        write_separated_ip_files(base_path, all_combined, "all")
        write_separated_ip_files(base_path, all_ipv4, "ipv4")
        write_separated_ip_files(base_path, all_ipv6, "ipv6")

        # Calculate detailed stats
        detailed_stats = calculate_detailed_stats(all_ips_list, all_ipv4, all_ipv6)

        # Generate index.md
        logger.info("Generating index.md...")
        index_content = generate_index_markdown(
            provider_name="Googlebot",
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
        print_summary("Googlebot", stats)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = GooglebotIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
