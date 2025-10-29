#!/usr/bin/env python3
"""
GCP IP Sync - Download GCP IP ranges and generate organized files.

This script downloads the latest GCP IP ranges JSON file and generates
IP range files organized by services and regions (scopes).
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
    sanitize_filename,
    print_summary,
    ensure_directory,
    calculate_detailed_stats
)

logger = logging.getLogger(__name__)


class GCPIP:
    """GCP IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the GCP IP Sync manager.

        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.url = config['gcp']['url']
        self.output_dir = os.path.join("cloud_ips", "gcp")
        self.services_dir = os.path.join(self.output_dir, "services")
        self.regions_dir = os.path.join(self.output_dir, "regions")
        self.data = None

    def download_data(self) -> dict:
        """
        Download the GCP IP ranges JSON file.

        Returns:
            dict: Parsed JSON data

        Raises:
            requests.RequestException: If download fails
        """
        logger.info(f"Downloading from: {self.url}")
        try:
            response = requests.get(self.url, timeout=60)
            response.raise_for_status()
            self.data = response.json()
            sync_token = self.data.get('syncToken', 'N/A')
            creation_time = self.data.get('creationTime', 'N/A')
            logger.info(f"Successfully downloaded (sync token: {sync_token}, time: {creation_time})")
            return self.data
        except requests.RequestException as e:
            logger.error(f"Error downloading data: {e}")
            raise

    def extract_ips(self) -> tuple:
        """
        Extract all IP ranges organized by service and region (scope).

        Returns:
            Tuple of (services_ips, regions_ips, all_ips)
            - services_ips: Dict mapping service names to IP sets
            - regions_ips: Dict mapping region/scope names to IP sets
            - all_ips: Set of all IP ranges
        """
        if not self.data:
            raise ValueError("Data not loaded. Call download_data() first.")

        services_ips = {}
        regions_ips = {}
        all_ips = set()

        # Process prefixes (both IPv4 and IPv6 in same array)
        for prefix in self.data.get("prefixes", []):
            # Get IP prefix (could be ipv4Prefix or ipv6Prefix)
            ip_prefix = prefix.get("ipv4Prefix") or prefix.get("ipv6Prefix")
            service = prefix.get("service", "UNKNOWN")
            scope = prefix.get("scope", "global")  # scope is like region

            if not ip_prefix:
                continue

            # Add to services
            if service not in services_ips:
                services_ips[service] = set()
            services_ips[service].add(ip_prefix)

            # Add to regions (scopes)
            if scope not in regions_ips:
                regions_ips[scope] = set()
            regions_ips[scope].add(ip_prefix)

            # Add to all IPs
            all_ips.add(ip_prefix)

        return services_ips, regions_ips, all_ips

    def generate_files(self) -> None:
        """
        Generate all IP range files: global, services, and regions.
        """
        logger.info("\nStarting IP range extraction...")

        # Download data if not already loaded
        if not self.data:
            self.download_data()

        # Create directories
        ensure_directory(self.output_dir)
        ensure_directory(self.services_dir)
        ensure_directory(self.regions_dir)

        # Extract IPs by service and region
        logger.info("Extracting IPs by service and scope...")
        services_ips, regions_ips, all_ips = self.extract_ips()

        # Convert sets to lists and separate IPv4/IPv6
        logger.info("Separating IPv4/IPv6...")
        all_ips_list = list(all_ips)
        all_ipv4, all_ipv6 = separate_ipv4_ipv6(all_ips_list)

        # Generate global files
        logger.info("Generating global files...")
        all_combined = all_ipv4 + all_ipv6
        # Write global files with separation of single IPs and ranges
        base_path = os.path.join(self.output_dir, "ips")
        write_separated_ip_files(base_path, all_combined, "all")
        write_separated_ip_files(base_path, all_ipv4, "ipv4")
        write_separated_ip_files(base_path, all_ipv6, "ipv6")

        # Generate per-service files
        logger.info(f"Generating service files ({len(services_ips)} services)...")
        service_counts = {}
        for service_name, ips in services_ips.items():
            safe_name = sanitize_filename(service_name)
            ips_list = list(ips)
            ipv4, ipv6 = separate_ipv4_ipv6(ips_list)

            # Write files with separation of single IPs and ranges
            base_path = os.path.join(self.services_dir, safe_name)
            all_combined = ipv4 + ipv6
            write_separated_ip_files(base_path, all_combined, "all")

            # Write IPv4 if present
            if ipv4:
                write_separated_ip_files(base_path, ipv4, "ipv4")

            # Write IPv6 if present
            if ipv6:
                write_separated_ip_files(base_path, ipv6, "ipv6")

            service_counts[service_name] = len(ips)

        # Generate per-region files (scopes)
        logger.info(f"Generating region/scope files ({len(regions_ips)} scopes)...")
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
        detailed_stats = calculate_detailed_stats(all_ips, all_ipv4, all_ipv6)

        # Generate index.md
        logger.info("Generating index.md...")
        index_content = generate_index_markdown(
            provider_name="GCP",
            total_ranges=detailed_stats['total'],
            ipv4_ranges=detailed_stats['ipv4_ranges'],
            ipv6_ranges=detailed_stats['ipv6_ranges'],
            ipv4_count=detailed_stats['ipv4_count'],
            ipv6_count=calculate_total_ips(all_ipv6),
            services=service_counts,
            regions=region_counts,
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
            'services': len(services_ips),
            'regions': len(regions_ips),
            'output_dir': self.output_dir
        }
        print_summary("GCP", stats)


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download GCP IP ranges and generate organized files"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = GCPIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
