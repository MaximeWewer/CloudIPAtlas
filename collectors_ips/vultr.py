#!/usr/bin/env python3
"""
Vultr IP Sync - Download Vultr IP ranges and generate organized files.
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
    sanitize_filename,
    calculate_detailed_stats
)

logger = logging.getLogger(__name__)


class VultrIP:
    """Vultr IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.url = config['vultr']['url']
        self.output_dir = os.path.join("cloud_ips", "vultr")
        self.regions_dir = os.path.join(self.output_dir, "regions")

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

    def extract_ips(self, data: dict) -> tuple:
        """
        Extract IPs and regions from Vultr JSON.

        Returns:
            Tuple of (all_ips, regions_ips)
        """
        all_ips = []
        regions_ips = {}

        # Vultr JSON structure: { "subnets": [ { "ip_prefix", "city", "alpha2code", ... } ] }
        subnets = data.get('subnets', [])

        for subnet in subnets:
            if isinstance(subnet, dict):
                ip = subnet.get('ip_prefix', '')
                city = subnet.get('city', '')
                country = subnet.get('alpha2code', '')

                if ip and is_valid_ip(ip):
                    all_ips.append(ip)

                    # Use city as region identifier
                    if city:
                        # Create region name: "City, Country" (e.g., "Tokyo, JP")
                        region_name = f"{city}, {country}" if country else city

                        if region_name not in regions_ips:
                            regions_ips[region_name] = set()
                        regions_ips[region_name].add(ip)

        logger.info(f"Extracted {len(all_ips)} IPs from {len(subnets)} subnets")
        logger.info(f"Found {len(regions_ips)} regions")
        return all_ips, regions_ips

    def generate_files(self) -> None:
        logger.info("\nStarting IP range extraction...")
        ensure_directory(self.output_dir)
        ensure_directory(self.regions_dir)

        data = self.download_data()
        if not data:
            return

        all_ips_list, regions_ips = self.extract_ips(data)
        if not all_ips_list:
            logger.info("Warning: No IP ranges found!")
            return

        # Separate IPv4/IPv6 for global files
        all_ipv4, all_ipv6 = separate_ipv4_ipv6(all_ips_list)

        # Generate global files
        logger.info("Generating global files...")
        all_combined = all_ipv4 + all_ipv6
        # Write global files with separation of single IPs and ranges
        base_path = os.path.join(self.output_dir, "ips")
        write_separated_ip_files(base_path, all_combined, "all")
        write_separated_ip_files(base_path, all_ipv4, "ipv4")
        write_separated_ip_files(base_path, all_ipv6, "ipv6")

        # Generate per-region files
        logger.info(f"Generating region files ({len(regions_ips)} regions)...")
        region_counts = {}
        for region_name, ips in regions_ips.items():
            safe_name = sanitize_filename(region_name)
            ips_list = list(ips)
            ipv4, ipv6 = separate_ipv4_ipv6(ips_list)

            # Write files with separation of single IPs and ranges
            base_path = os.path.join(self.regions_dir, safe_name)
            all_combined = ipv4 + ipv6
            write_separated_ip_files(base_path, all_combined, "all")

            # Write IPv4 if present
            if ipv4:
                write_separated_ip_files(base_path, ipv4, "ipv4")

            # Write IPv6 if present
            if ipv6:
                write_separated_ip_files(base_path, ipv6, "ipv6")

            region_counts[region_name] = len(ips)

        # Calculate detailed stats
        detailed_stats = calculate_detailed_stats(all_ips_list, all_ipv4, all_ipv6)

        # Generate index.md
        logger.info("Generating index.md...")
        index_content = generate_index_markdown(
            provider_name="Vultr",
            total_ranges=detailed_stats['total'],
            ipv4_ranges=detailed_stats['ipv4_ranges'],
            ipv6_ranges=detailed_stats['ipv6_ranges'],
            ipv4_count=detailed_stats['ipv4_count'],
            ipv6_count=calculate_total_ips(all_ipv6),
            services=None,
            regions=region_counts,
            ipv4_single=detailed_stats['ipv4_single'],
            ipv6_single=detailed_stats['ipv6_single'],
            ipv4_ranges_only=detailed_stats['ipv4_ranges_only'],
            ipv6_ranges_only=detailed_stats['ipv6_ranges_only']
        )
        with open(os.path.join(self.output_dir, "index.md"), 'w', encoding='utf-8') as f:
            f.write(index_content)

        stats = {
            **detailed_stats,
            'regions': len(regions_ips),
            'output_dir': self.output_dir
        }
        print_summary("Vultr", stats)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = VultrIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
