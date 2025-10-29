#!/usr/bin/env python3
"""
IBM Cloud IP Sync - Download IBM Cloud IP ranges and generate organized files.

IBM Cloud provides IP ranges in HTML documentation organized by services.
"""

import os
import sys
import json
import logging
import requests
import re

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    logger.info("Error: BeautifulSoup4 is required. Install with: pip install beautifulsoup4")
    sys.exit(1)

from .ip_utils import (
    separate_ipv4_ipv6,
    write_separated_ip_files,
    generate_index_markdown,
    calculate_total_ips,
    print_summary,
    ensure_directory,
    is_valid_ip,
    sanitize_filename,
    is_private_ip,
    calculate_detailed_stats
)


class IBMCloudIP:
    """IBM Cloud IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.url = config['ibm_cloud']['url']
        self.output_dir = os.path.join("cloud_ips", "ibm_cloud")
        self.services_dir = os.path.join(self.output_dir, "services")

    def download_data(self) -> str:
        logger.info(f"Downloading from: {self.url}")
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            logger.info(f"Downloaded HTML ({len(response.text)} bytes)")
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error: {e}")
            return ""

    def extract_ips(self, html: str) -> tuple:
        """
        Extract IPs from HTML organized by services.

        Returns:
            Tuple of (all_ips, services_ips)
            - all_ips: List of all IPs
            - services_ips: Dict mapping service names to IP sets
        """
        all_ips = []
        services_ips = {}
        soup = BeautifulSoup(html, 'html.parser')

        # Patterns for IP addresses
        ipv4_pattern = re.compile(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/[0-9]{1,2})?')
        ipv6_pattern = re.compile(r'(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}(?:/[0-9]{1,3})?')

        # Define the service sections to extract
        service_headers = [
            'Front-end (public) network',
            'Load balancer IPs',
            'Back-end (private) network',
            'Customer private network space',
            'Service network (on back-end/private network)',
            'SSL VPN network (on back-end/private network)',
            'SSL VPN data centers',
            'Legacy networks',
            'Red Hat Enterprise Linux server requirements',
            'Windows virtual server instance requirements'
        ]

        # Find all h2/h3 headers and extract IPs in their sections
        for header_text in service_headers:
            # Find the header
            header = soup.find(['h2', 'h3'], string=re.compile(re.escape(header_text), re.IGNORECASE))

            if not header:
                continue

            service_name = header_text
            logger.info(f"Processing section: {service_name}")

            # Get all content until the next header of same or higher level
            current_element = header.find_next_sibling()
            section_ips = set()

            while current_element:
                # Stop if we hit another h2 or h3
                if current_element.name in ['h2', 'h3']:
                    break

                # Extract IPs from this element
                text = current_element.get_text()

                # Find IPv4
                for ip in ipv4_pattern.findall(text):
                    if is_valid_ip(ip) and not is_private_ip(ip):
                        section_ips.add(ip)
                        all_ips.append(ip)

                # Find IPv6
                for ip in ipv6_pattern.findall(text):
                    if is_valid_ip(ip) and not is_private_ip(ip):
                        section_ips.add(ip)
                        all_ips.append(ip)

                # Also check in code blocks and pre tags
                for code_elem in current_element.find_all(['code', 'pre']):
                    code_text = code_elem.get_text()

                    for ip in ipv4_pattern.findall(code_text):
                        if is_valid_ip(ip) and not is_private_ip(ip):
                            section_ips.add(ip)
                            all_ips.append(ip)

                    for ip in ipv6_pattern.findall(code_text):
                        if is_valid_ip(ip) and not is_private_ip(ip):
                            section_ips.add(ip)
                            all_ips.append(ip)

                current_element = current_element.find_next_sibling()

            if section_ips:
                services_ips[service_name] = section_ips
                logger.info(f"  Found {len(section_ips)} IPs in {service_name}")

        # Remove duplicates from all_ips
        all_ips = list(set(all_ips))

        logger.info(f"Total unique IPs: {len(all_ips)}")
        logger.info(f"Services found: {len(services_ips)}")

        return all_ips, services_ips

    def generate_files(self) -> None:
        logger.info("\nStarting IP range extraction...")
        ensure_directory(self.output_dir)
        ensure_directory(self.services_dir)

        html = self.download_data()
        if not html:
            return

        logger.info("Extracting IP ranges from HTML...")
        all_ips_list, services_ips = self.extract_ips(html)

        if not all_ips_list:
            logger.info("Warning: No IP ranges found!")
            return

        # Separate IPv4/IPv6 for global files
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

        # Calculate detailed stats
        detailed_stats = calculate_detailed_stats(all_ips_list, all_ipv4, all_ipv6)

        # Generate index.md
        logger.info("Generating index.md...")
        index_content = generate_index_markdown(
            provider_name="IBM Cloud",
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
        print_summary("IBM Cloud", stats)


def main():
    import argparse

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.json")
    args = parser.parse_args()
    try:
        syncer = IBMCloudIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
