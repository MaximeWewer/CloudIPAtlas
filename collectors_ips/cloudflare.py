#!/usr/bin/env python3
"""
Cloudflare IP Sync - Download Cloudflare IP ranges and generate organized files.

Cloudflare provides simple text files with one CIDR per line for IPv4 and IPv6.
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


class CloudflareIP:
    """Cloudflare IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the Cloudflare IP Sync manager.

        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.urls = config['cloudflare']['urls']
        self.output_dir = os.path.join("cloud_ips", "cloudflare")

    def download_data(self) -> List[str]:
        """
        Download Cloudflare IP ranges from text files.

        Returns:
            List of IP ranges (CIDR notation)
        """
        all_ips = []

        for url in self.urls:
            logger.info(f"Downloading from: {url}")
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                # Parse text file (one IP per line)
                lines = response.text.strip().split('\n')
                for line in lines:
                    ip = line.strip()
                    if ip and is_valid_ip(ip):
                        all_ips.append(ip)

                logger.info(f"Downloaded {len(lines)} IPs from {url}")

            except requests.RequestException as e:
                logger.error(f"Error downloading from {url}: {e}")

        return all_ips

    def generate_files(self) -> None:
        """
        Generate all IP range files for Cloudflare.
        """
        logger.info("\nStarting IP range extraction...")

        # Create output directory
        ensure_directory(self.output_dir)

        # Download data
        all_ips_list = self.download_data()

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
            provider_name="Cloudflare",
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
        print_summary("Cloudflare", stats)


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Cloudflare IP ranges and generate organized files"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = CloudflareIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
