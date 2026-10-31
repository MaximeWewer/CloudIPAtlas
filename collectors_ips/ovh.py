"""
OVH IP Sync - Download OVH IP ranges from HTML documentation and generate organized files.

This script parses OVH's web hosting documentation page and extracts
IP range information organized by clusters.
"""

import os
import json
import re
import requests
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

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


class OVHIP:
    """OVH IP ranges synchronization manager."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the OVH IP Sync manager.

        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.url = config['ovh']['url']
        self.output_dir = os.path.join("cloud_ips", "ovh")
        self.clusters_dir = os.path.join(self.output_dir, "clusters")
        self.services_dir = os.path.join(self.output_dir, "services")
        self.countries_dir = os.path.join(self.output_dir, "countries")
        self.html_content = None

    def download_data(self) -> str:
        """
        Download the OVH IP documentation HTML page.

        Returns:
            str: HTML content

        Raises:
            requests.RequestException: If download fails
        """
        logger.info(f"Downloading from: {self.url}")
        try:
            response = requests.get(self.url, timeout=60)
            response.raise_for_status()
            self.html_content = response.text
            logger.info(f"Downloaded HTML content ({len(self.html_content)} bytes)")
            return self.html_content
        except requests.RequestException as e:
            logger.error(f"Error downloading data: {e}")
            raise

    @staticmethod
    def _ips_in(element) -> set:
        """Return every valid IPv4/IPv6 address found in an element's text."""
        tokens = re.findall(r'[0-9a-fA-F:.]+', element.get_text(' '))
        return {t for t in tokens if ('.' in t or ':' in t) and is_valid_ip(t)}

    def extract_ips_from_html(self) -> tuple:
        """
        Parse HTML content to extract IP ranges from OVH clusters.

        Each cluster is a <details> block: a <summary> holding the "Cluster NNN"
        heading, a per-country table, then <p> labels ("Shared CDN",
        "outgoing IP address") each followed by a <div> holding the IP.

        Returns:
            Tuple of (clusters_data, countries_data, all_ips)
            - clusters_data: Dict[cluster_num] -> {main: set(ips), cdn: set(ips), gateway: set(ips), countries: dict[country_code] -> set(ips)}
            - countries_data: Dict[country_code] -> set(all ips from all clusters)
            - all_ips: Set of all IP ranges
        """
        if not self.html_content:
            raise ValueError("HTML content not loaded. Call download_data() first.")

        soup = BeautifulSoup(self.html_content, 'html.parser')
        clusters_data = {}
        countries_data = {}
        all_ips = set()

        for details in soup.find_all('details'):
            summary = details.find('summary')
            cluster_match = re.search(r'Cluster\s+(\d+)', summary.get_text() if summary else '', re.IGNORECASE)
            if not cluster_match:
                continue

            cluster_num = cluster_match.group(1).zfill(3)
            cluster = clusters_data[cluster_num] = {
                'main': set(),
                'cdn': set(),
                'gateway': set(),
                'countries': {}
            }

            # Per-country table: Country | Country Code | IPv4 | IPv6
            table = details.find('table')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) < 3:  # Skip header or incomplete rows
                        continue

                    country = cells[1].get_text(strip=True).upper()
                    row_ips = set()
                    for cell in cells[2:]:
                        row_ips |= self._ips_in(cell)
                    if not row_ips:
                        continue

                    cluster['main'] |= row_ips
                    all_ips |= row_ips
                    if re.fullmatch(r'[A-Z]{2}', country):
                        cluster['countries'].setdefault(country, set()).update(row_ips)
                        countries_data.setdefault(country, set()).update(row_ips)

            # CDN and gateway: a <p> label followed by the IP in the next element
            for label in details.find_all('p'):
                text = label.get_text(' ').lower()
                if 'cdn' in text:
                    key = 'cdn'
                elif 'gateway' in text or 'outgoing' in text:
                    key = 'gateway'
                else:
                    continue
                target = label.find_next_sibling()
                if target:
                    ips = {ip for ip in self._ips_in(target) if '.' in ip}
                    cluster[key] |= ips
                    all_ips |= ips

        logger.info(f"Extracted {len(clusters_data)} clusters")
        logger.info(f"Extracted {len(countries_data)} countries")
        logger.info(f"Total IPs found: {len(all_ips)}")

        return clusters_data, countries_data, all_ips

    def generate_files(self) -> None:
        """
        Generate all IP range files organized in three folders:
        - clusters/: All IPs per cluster
        - services/: CDN and Gateway IPs per cluster
        - countries/: IPs grouped by country code across all clusters
        """
        logger.info("\nStarting IP range extraction...")

        # Create directories
        ensure_directory(self.output_dir)
        ensure_directory(self.clusters_dir)
        ensure_directory(self.services_dir)
        ensure_directory(self.countries_dir)

        if not self.html_content:
            self.download_data()

        logger.info("Parsing HTML content...")
        clusters_data, countries_data, all_ips = self.extract_ips_from_html()

        if not all_ips:
            raise ValueError("No IP ranges found, page structure may have changed")

        # Convert sets to lists and separate IPv4/IPv6 for global files
        logger.info("Separating IPv4/IPv6...")
        all_ips_list = list(all_ips)
        all_ipv4, all_ipv6 = separate_ipv4_ipv6(all_ips_list)

        # Generate global files at root level
        logger.info("Generating global files...")
        all_combined = all_ipv4 + all_ipv6
        base_path = os.path.join(self.output_dir, "ips")
        write_separated_ip_files(base_path, all_combined, "all")
        write_separated_ip_files(base_path, all_ipv4, "ipv4")
        write_separated_ip_files(base_path, all_ipv6, "ipv6")

        # Generate clusters/ files
        logger.info(f"Generating cluster files ({len(clusters_data)} clusters)...")
        cluster_counts = {}
        for cluster_num, cluster_info in sorted(clusters_data.items()):
            cluster_name = f"Cluster-{cluster_num}"

            # Get all IPs for this cluster (main IPs)
            cluster_ips = list(cluster_info['main'])
            if cluster_ips:
                cluster_ipv4, cluster_ipv6 = separate_ipv4_ipv6(cluster_ips)

                # Write files with separation of single IPs and ranges
                base_path = os.path.join(self.clusters_dir, f"cluster-{cluster_num}")
                all_combined = cluster_ipv4 + cluster_ipv6
                write_separated_ip_files(base_path, all_combined, "all")

                # Write IPv4 if present
                if cluster_ipv4:
                    write_separated_ip_files(base_path, cluster_ipv4, "ipv4")

                # Write IPv6 if present
                if cluster_ipv6:
                    write_separated_ip_files(base_path, cluster_ipv6, "ipv6")

                cluster_counts[cluster_name] = len(cluster_ips)

        # Generate services/ files (CDN and Gateway per cluster)
        logger.info("Generating service files...")
        service_file_count = 0
        for cluster_num, cluster_info in sorted(clusters_data.items()):
            # CDN file
            if cluster_info['cdn']:
                cdn_ips = list(cluster_info['cdn'])
                cdn_ipv4, cdn_ipv6 = separate_ipv4_ipv6(cdn_ips)
                base_path = os.path.join(self.services_dir, f"cluster-{cluster_num}_cdn")
                write_separated_ip_files(base_path, cdn_ipv4 + cdn_ipv6, "all")
                service_file_count += 1

            # Gateway file
            if cluster_info['gateway']:
                gateway_ips = list(cluster_info['gateway'])
                gateway_ipv4, gateway_ipv6 = separate_ipv4_ipv6(gateway_ips)
                base_path = os.path.join(self.services_dir, f"cluster-{cluster_num}_gateway")
                write_separated_ip_files(base_path, gateway_ipv4 + gateway_ipv6, "all")
                service_file_count += 1

        logger.info(f"Generated {service_file_count} service files")

        # Generate countries/ files
        logger.info(f"Generating country files ({len(countries_data)} countries)...")
        country_counts = {}
        for country_code, country_ips in sorted(countries_data.items()):
            country_ips_list = list(country_ips)
            if country_ips_list:
                country_ipv4, country_ipv6 = separate_ipv4_ipv6(country_ips_list)

                # Write files with separation of single IPs and ranges
                base_path = os.path.join(self.countries_dir, country_code)
                all_combined = country_ipv4 + country_ipv6
                write_separated_ip_files(base_path, all_combined, "all")

                # Write IPv4 if present
                if country_ipv4:
                    write_separated_ip_files(base_path, country_ipv4, "ipv4")

                # Write IPv6 if present
                if country_ipv6:
                    write_separated_ip_files(base_path, country_ipv6, "ipv6")

                country_counts[country_code] = len(country_ips_list)

        # Calculate detailed stats (single IPs vs ranges)
        detailed_stats = calculate_detailed_stats(all_ips, all_ipv4, all_ipv6)

        # Generate index.md
        logger.info("Generating index.md...")
        index_content = generate_index_markdown(
            provider_name="OVH",
            total_ranges=detailed_stats['total'],
            ipv4_ranges=detailed_stats['ipv4_ranges'],
            ipv6_ranges=detailed_stats['ipv6_ranges'],
            ipv4_count=detailed_stats['ipv4_count'],
            ipv6_count=calculate_total_ips(all_ipv6),
            services=cluster_counts,
            regions=None,  # OVH doesn't expose regions
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
            'services': len(cluster_counts),
            'output_dir': self.output_dir
        }
        print_summary("OVH", stats)
        logger.info(f"Additional files: {service_file_count} service files, {len(country_counts)} country files")
