#!/usr/bin/env python3
"""
Scaleway IP Sync - Download Scaleway IP ranges from HTML documentation and generate organized files.

This script downloads and parses Scaleway's HTML documentation to extract
IP range information organized by services and regions.
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

# Import shared utilities
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


class ScalewayIP:
    """Scaleway IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the Scaleway IP Sync manager.

        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.url = config['scaleway']['url']
        self.output_dir = os.path.join("cloud_ips", "scaleway")
        self.services_dir = os.path.join(self.output_dir, "services")
        self.regions_dir = os.path.join(self.output_dir, "regions")
        self.html_content = None

    def download_data(self) -> str:
        """
        Download the Scaleway network information HTML page.

        Returns:
            str: HTML content

        Raises:
            requests.RequestException: If download fails
        """
        logger.info(f"[Scaleway] Downloading from: {self.url}")
        try:
            response = requests.get(self.url, timeout=60)
            response.raise_for_status()
            self.html_content = response.text
            logger.info(f"[Scaleway] Successfully downloaded HTML content ({len(self.html_content)} bytes)")
            return self.html_content
        except requests.RequestException as e:
            logger.error(f"[Scaleway] Error downloading data: {e}")
            raise

    def extract_ips_from_html(self) -> tuple:
        """
        Parse HTML content to extract IP ranges.

        Returns:
            Tuple of (services_ips, regions_ips, all_ips)
            - services_ips: Dict mapping service names to IP sets
            - regions_ips: Dict mapping region names to IP sets
            - all_ips: Set of all IP ranges
        """
        if not self.html_content:
            raise ValueError("HTML content not loaded. Call download_data() first.")

        soup = BeautifulSoup(self.html_content, 'html.parser')
        services_ips = {}
        regions_ips = {}
        all_ips = set()

        # Pattern to match IP addresses and CIDR ranges
        ip_pattern = re.compile(
            r'\b(?:'
            r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/[0-9]{1,2})?|'  # IPv4 with optional CIDR
            r'(?:[0-9a-fA-F:]+:){2,}(?:[0-9a-fA-F:]+)(?:/[0-9]{1,3})?'  # IPv6 with optional CIDR
            r')\b'
        )

        # Region mapping for Scaleway zones
        region_mapping = {
            'fr-par-1': 'France-Paris-1',
            'fr-par-2': 'France-Paris-2',
            'fr-par-3': 'France-Paris-3',
            'nl-ams-1': 'Netherlands-Amsterdam-1',
            'nl-ams-2': 'Netherlands-Amsterdam-2',
            'nl-ams-3': 'Netherlands-Amsterdam-3',
            'pl-waw-1': 'Poland-Warsaw-1',
            'pl-waw-2': 'Poland-Warsaw-2',
            'pl-waw-3': 'Poland-Warsaw-3'
        }

        current_service = "General"
        current_region = None

        # Parse text content
        text_content = soup.get_text()
        lines = text_content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()

            # Detect service/section headers
            if 'IPv4' in line and len(line) < 20:
                current_service = "Core-IPv4-Ranges"
            elif 'IPv6' in line and len(line) < 20:
                current_service = "Core-IPv6-Ranges"
            elif 'DNS cache servers' in line or 'NTP servers' in line:
                current_service = "DNS-NTP-Servers"
            elif 'France' in line and len(line) < 20:
                current_region = 'France'
            elif 'Netherlands' in line and len(line) < 20:
                current_region = 'Netherlands'
            elif 'Poland' in line and len(line) < 20:
                current_region = 'Poland'
            elif 'Rdate server' in line:
                current_service = "Rdate-Server"
            elif 'Backup server' in line:
                current_service = "Backup-Server"
            elif 'RPN VPN' in line:
                current_service = "RPN-VPN"
            elif 'Monitoring' in line:
                current_service = "Monitoring"
            elif 'Dedibox' in line and len(line) < 50:
                current_service = "Dedibox-Services"

            # Check for region codes (fr-par-1, nl-ams-2, etc.)
            region_match = re.search(r'\b(fr-par-[1-3]|nl-ams-[1-3]|pl-waw-[1-3])\b', line, re.IGNORECASE)
            if region_match:
                zone_code = region_match.group(1).lower()
                current_region = region_mapping.get(zone_code, zone_code)

            # Extract IPs from this line
            found_ips = ip_pattern.findall(line)
            for ip in found_ips:
                if is_valid_ip(ip):
                    # Add to services
                    if current_service not in services_ips:
                        services_ips[current_service] = set()
                    services_ips[current_service].add(ip)

                    # Add to regions if we have a region context
                    if current_region:
                        if current_region not in regions_ips:
                            regions_ips[current_region] = set()
                        regions_ips[current_region].add(ip)

                    all_ips.add(ip)

        return services_ips, regions_ips, all_ips

    def generate_files(self) -> None:
        """
        Generate all IP range files: global, services, and regions.
        """
        logger.info("\n[Scaleway] Starting IP range extraction from HTML...")

        # Download HTML content if not already loaded
        if not self.html_content:
            self.download_data()

        # Create directories
        ensure_directory(self.output_dir)
        ensure_directory(self.services_dir)
        ensure_directory(self.regions_dir)

        # Extract IPs from HTML
        logger.info("[Scaleway] Parsing HTML to extract IPs...")
        services_ips, regions_ips, all_ips = self.extract_ips_from_html()

        if not all_ips:
            logger.info("[Scaleway] Warning: No IP ranges found in HTML content!")
            logger.info("[Scaleway] The page structure may have changed. Manual review needed.")

        # Convert sets to lists and separate IPv4/IPv6
        logger.info("[Scaleway] Separating IPv4/IPv6...")
        all_ips_list = list(all_ips)
        all_ipv4, all_ipv6 = separate_ipv4_ipv6(all_ips_list)

        # Generate global files
        logger.info("[Scaleway] Generating global files...")
        all_combined = all_ipv4 + all_ipv6
        # Write global files with separation of single IPs and ranges
        base_path = os.path.join(self.output_dir, "ips")
        write_separated_ip_files(base_path, all_combined, "all")
        write_separated_ip_files(base_path, all_ipv4, "ipv4")
        write_separated_ip_files(base_path, all_ipv6, "ipv6")

        # Generate per-service files
        logger.info(f"[Scaleway] Generating service files ({len(services_ips)} services)...")
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

        # Generate per-region files (if any regions detected)
        if regions_ips:
            logger.info(f"[Scaleway] Generating region files ({len(regions_ips)} regions)...")
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
        else:
            region_counts = None

        # Calculate detailed stats
        detailed_stats = calculate_detailed_stats(all_ips, all_ipv4, all_ipv6)

        # Generate index.md
        logger.info("[Scaleway] Generating index.md...")
        index_content = generate_index_markdown(
            provider_name="Scaleway",
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
            'regions': len(regions_ips) if regions_ips else 0,
            'output_dir': self.output_dir
        }
        print_summary("Scaleway", stats)


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Scaleway IP ranges from HTML and generate organized files"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = ScalewayIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\n[Scaleway] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
