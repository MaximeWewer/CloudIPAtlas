#!/usr/bin/env python3
"""
Perplexity IP Sync - Download Perplexity IP ranges and generate organized files.

Perplexity provides two JSON files:
- perplexitybot.json: PerplexityBot crawler IP ranges
- perplexity-user.json: Perplexity user IP ranges
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


class PerplexityIP:
    """Perplexity IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.urls = config['perplexity']['urls']
        self.output_dir = os.path.join("cloud_ips", "perplexity")
        self.services_dir = os.path.join(self.output_dir, "services")

    def download_data(self) -> tuple:
        """
        Download Perplexity IP ranges from multiple JSON files.

        Returns:
            Tuple of (all_ips, services_ips)
        """
        all_ips = []
        services_ips = {}

        # Map URL patterns to service names
        service_mapping = {
            'perplexitybot': 'perplexitybot',
            'perplexity-user': 'perplexity-user'
        }

        for url in self.urls:
            logger.info(f"Downloading from: {url}")
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Determine service name from URL
                service_name = 'unknown'
                for key, name in service_mapping.items():
                    if key in url:
                        service_name = name
                        break

                # Extract IPs from prefixes array
                prefixes = data.get('prefixes', [])
                for prefix in prefixes:
                    if isinstance(prefix, dict):
                        ip = prefix.get('ipv4Prefix') or prefix.get('ipv6Prefix', '')
                        if ip and is_valid_ip(ip):
                            all_ips.append(ip)

                            if service_name not in services_ips:
                                services_ips[service_name] = set()
                            services_ips[service_name].add(ip)

                logger.info(f"Downloaded {len(prefixes)} prefixes from {service_name}")

            except requests.RequestException as e:
                logger.error(f"Error downloading from {url}: {e}")

        logger.info(f"Total: {len(all_ips)} IPs from {len(services_ips)} services")
        return all_ips, services_ips

    def generate_files(self) -> None:
        logger.info("\nStarting IP range extraction...")
        ensure_directory(self.output_dir)
        ensure_directory(self.services_dir)

        all_ips_list, services_ips = self.download_data()
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

        # Generate per-service files
        logger.info(f"Generating service files ({len(services_ips)} services)...")
        service_counts = {}
        for service_name, ips in services_ips.items():
            safe_name = sanitize_filename(service_name)
            ips_list = list(ips)
            ipv4, ipv6 = separate_ipv4_ipv6(ips_list)

            base_path = os.path.join(self.services_dir, safe_name)
            all_combined = ipv4 + ipv6
            write_separated_ip_files(base_path, all_combined, "all")

            if ipv4:
                write_separated_ip_files(base_path, ipv4, "ipv4")

            if ipv6:
                write_separated_ip_files(base_path, ipv6, "ipv6")

            service_counts[service_name] = len(ips)

        # Calculate detailed stats
        detailed_stats = calculate_detailed_stats(all_ips_list, all_ipv4, all_ipv6)

        # Generate index.md
        logger.info("Generating index.md...")
        index_content = generate_index_markdown(
            provider_name="Perplexity",
            total_ranges=detailed_stats['total'],
            ipv4_ranges=detailed_stats['ipv4_ranges'],
            ipv6_ranges=detailed_stats['ipv6_ranges'],
            ipv4_count=detailed_stats['ipv4_count'],
            ipv6_count=calculate_total_ips(all_ipv6),
            services=service_counts,
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
            'services': len(services_ips),
            'output_dir': self.output_dir
        }
        print_summary("Perplexity", stats)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = PerplexityIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
