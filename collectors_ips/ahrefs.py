#!/usr/bin/env python3
"""
Ahrefs IP Sync - Download Ahrefs crawler IP addresses.

Ahrefs provides a simple JSON API with individual IP addresses (not CIDR ranges).
Format: {"ips": [{"ip_address": "x.x.x.x"}, ...]}
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


class AhrefsIP:
    """Ahrefs IP addresses synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.url = config['ahrefs']['url']
        self.output_dir = os.path.join("cloud_ips", "ahrefs")

    def download_data(self) -> list:
        """
        Download Ahrefs crawler IP addresses.

        Returns:
            List of IP addresses
        """
        all_ips = []

        logger.info(f"Downloading from: {self.url}")
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract IPs from the ips array
            ips_array = data.get('ips', [])
            for entry in ips_array:
                if isinstance(entry, dict):
                    ip = entry.get('ip_address', '')
                    if ip and is_valid_ip(ip):
                        all_ips.append(ip)

            logger.info(f"Downloaded {len(all_ips)} IP addresses")

        except requests.RequestException as e:
            logger.error(f"Error downloading from {self.url}: {e}")

        return all_ips

    def generate_files(self) -> None:
        logger.info("\nStarting IP extraction...")
        ensure_directory(self.output_dir)

        all_ips_list = self.download_data()
        if not all_ips_list:
            logger.info("Warning: No IP addresses found!")
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
            provider_name="Ahrefs",
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
        print_summary("Ahrefs", stats)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = AhrefsIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
