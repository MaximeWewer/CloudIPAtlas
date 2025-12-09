#!/usr/bin/env python3
"""
Outscale IP Sync - Download Outscale IP ranges from HTML documentation and generate organized files.

This script downloads and parses Outscale's HTML documentation to extract
IP range information organized by regions.
"""

import os
import sys
import json
import re
import requests
import logging

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    logger.info("Error: BeautifulSoup4 is required for HTML parsing.")
    logger.info("Install with: pip install beautifulsoup4")
    sys.exit(1)

from .ip_utils import (
    separate_ipv4_ipv6,
    write_separated_ip_files,
    generate_index_markdown,
    calculate_total_ips,
    sanitize_filename,
    print_summary,
    ensure_directory,
    is_valid_ip,
    calculate_detailed_stats
)


class OutscaleIP:
    """Outscale IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.url = config['outscale']['url']
        self.output_dir = os.path.join("cloud_ips", "outscale")
        self.regions_dir = os.path.join(self.output_dir, "regions")
        self.html_content = None

    def download_data(self) -> str:
        logger.info(f"Downloading from: {self.url}")
        try:
            response = requests.get(self.url, timeout=60)
            response.raise_for_status()
            self.html_content = response.text
            logger.info(f"Successfully downloaded HTML content ({len(self.html_content)} bytes)")
            return self.html_content
        except requests.RequestException as e:
            logger.error(f"Error downloading data: {e}")
            raise

    def extract_ips_from_html(self) -> tuple:
        """
        Parse HTML content to extract IP ranges from table.

        Returns:
            Tuple of (regions_ips, all_ips)
            - regions_ips: Dict mapping region names to IP sets
            - all_ips: Set of all IP ranges
        """
        if not self.html_content:
            raise ValueError("HTML content not loaded. Call download_data() first.")

        soup = BeautifulSoup(self.html_content, 'html.parser')
        regions_ips = {}
        all_ips = set()

        # Pattern to match CIDR IP ranges
        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}\b')

        # Find all tables in the page
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # First cell is region, second cell contains IP ranges
                    region_cell = cells[0].get_text(strip=True)
                    ip_cell = cells[1].get_text(strip=True)

                    # Skip header rows
                    if 'Region' in region_cell or 'Public IP' in region_cell:
                        continue

                    # Extract region name (clean it up)
                    region_name = region_cell.strip()
                    if not region_name:
                        continue

                    # Extract all IPs from the IP cell
                    found_ips = ip_pattern.findall(ip_cell)

                    for ip in found_ips:
                        if is_valid_ip(ip):
                            all_ips.add(ip)

                            if region_name not in regions_ips:
                                regions_ips[region_name] = set()
                            regions_ips[region_name].add(ip)

        logger.info(f"Extracted {len(all_ips)} IPs from {len(regions_ips)} regions")
        return regions_ips, all_ips

    def generate_files(self) -> None:
        logger.info("\nStarting IP range extraction from HTML...")

        # Download HTML content if not already loaded
        if not self.html_content:
            self.download_data()

        # Create directories
        ensure_directory(self.output_dir)
        ensure_directory(self.regions_dir)

        # Extract IPs from HTML
        logger.info("Parsing HTML to extract IPs...")
        regions_ips, all_ips = self.extract_ips_from_html()

        if not all_ips:
            logger.info("Warning: No IP ranges found in HTML content!")
            logger.info("The page structure may have changed. Manual review needed.")
            return

        # Convert sets to lists and separate IPv4/IPv6
        logger.info("Separating IPv4/IPv6...")
        all_ips_list = list(all_ips)
        all_ipv4, all_ipv6 = separate_ipv4_ipv6(all_ips_list)

        # Generate global files
        logger.info("Generating global files...")
        all_combined = all_ipv4 + all_ipv6
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

            base_path = os.path.join(self.regions_dir, safe_name)
            all_combined = ipv4 + ipv6
            write_separated_ip_files(base_path, all_combined, "all")

            if ipv4:
                write_separated_ip_files(base_path, ipv4, "ipv4")

            if ipv6:
                write_separated_ip_files(base_path, ipv6, "ipv6")

            region_counts[region_name] = len(ips)

        # Calculate detailed stats
        detailed_stats = calculate_detailed_stats(all_ips_list, all_ipv4, all_ipv6)

        # Generate index.md
        logger.info("Generating index.md...")
        index_content = generate_index_markdown(
            provider_name="Outscale",
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
        print_summary("Outscale", stats)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Outscale IP ranges from HTML and generate organized files"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = OutscaleIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
