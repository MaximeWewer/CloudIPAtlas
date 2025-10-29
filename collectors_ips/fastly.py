#!/usr/bin/env python3
"""
Fastly IP Sync - Download Fastly IP ranges and generate organized files.

Fastly provides a JSON API with IP addresses.
"""

import os
import sys
import json
import logging
import requests
from typing import List

# Import shared utilities
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


class FastlyIP:
    """Fastly IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the Fastly IP Sync manager.

        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.url = config['fastly']['url']
        self.output_dir = os.path.join("cloud_ips", "fastly")

    def download_data(self) -> dict:
        """
        Download Fastly IP ranges from API.

        Returns:
            JSON data from Fastly API
        """
        logger.info(f"Downloading from: {self.url}")
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info("Successfully downloaded JSON data")
            return data
        except requests.RequestException as e:
            logger.error(f"Error downloading data: {e}")
            return {}

    def extract_ips(self, data: dict) -> List[str]:
        """
        Extract IP ranges from Fastly JSON data.

        Args:
            data: JSON data from Fastly API

        Returns:
            List of IP ranges
        """
        all_ips = []

        # Fastly API returns addresses in different fields
        # Common fields: addresses, ipv4, ipv6
        for key in ['addresses', 'ipv4', 'ipv6']:
            if key in data and isinstance(data[key], list):
                for ip in data[key]:
                    if isinstance(ip, str) and is_valid_ip(ip):
                        all_ips.append(ip)

        # Also check nested structures
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and is_valid_ip(item):
                            all_ips.append(item)

        return list(set(all_ips))  # Remove duplicates

    def generate_files(self) -> None:
        """
        Generate all IP range files for Fastly.
        """
        logger.info("\nStarting IP range extraction...")

        # Create output directory
        ensure_directory(self.output_dir)

        # Download data
        data = self.download_data()

        if not data:
            logger.info("Warning: No data downloaded!")
            return

        # Extract IPs
        logger.info("Extracting IP ranges...")
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
        # Write global files with separation of single IPs and ranges
        base_path = os.path.join(self.output_dir, "ips")
        write_separated_ip_files(base_path, all_combined, "all")
        write_separated_ip_files(base_path, all_ipv4, "ipv4")
        write_separated_ip_files(base_path, all_ipv6, "ipv6")

        # Calculate detailed stats
        detailed_stats = calculate_detailed_stats(all_ips_list, all_ipv4, all_ipv6)

        # Generate index.md
        logger.info("Generating index.md...")
        index_content = generate_index_markdown(
            provider_name="Fastly",
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

        # Print summary
        stats = {
            **detailed_stats,
            'output_dir': self.output_dir
        }
        print_summary("Fastly", stats)


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Fastly IP ranges and generate organized files"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = FastlyIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
