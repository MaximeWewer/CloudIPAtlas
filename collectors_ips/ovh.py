#!/usr/bin/env python3
"""
OVH IP Sync - Download OVH IP ranges from HTML documentation and generate organized files.

This script uses Selenium to scrape dynamically-loaded content from OVH's website
and extract IP range information organized by clusters.
"""

import os
import sys
import json
import re
import time
import requests
import logging

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    logger.info("Error: BeautifulSoup4 is required for HTML parsing.")
    logger.info("Install with: pip install beautifulsoup4")
    sys.exit(1)

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.info("Warning: Selenium not available. Install with: pip install selenium")

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

    def __init__(self, config_path: str = "config.json", data_file: str = "ovh_data.json", use_selenium: bool = True):
        """
        Initialize the OVH IP Sync manager.

        Args:
            config_path: Path to configuration file
            data_file: Path to OVH data JSON file (fallback if scraping fails)
            use_selenium: Whether to use Selenium for scraping (default: True)
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.url = config['ovh']['url']
        self.output_dir = os.path.join("cloud_ips", "ovh")
        self.clusters_dir = os.path.join(self.output_dir, "clusters")
        self.services_dir = os.path.join(self.output_dir, "services")
        self.countries_dir = os.path.join(self.output_dir, "countries")
        self.data_file = data_file
        self.html_content = None
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.use_static_data = False  # Will be set to True if scraping fails

    def scrape_with_selenium(self) -> str:
        """
        Scrape OVH page using Selenium to handle JavaScript-loaded content.

        Returns:
            str: Rendered HTML content after JavaScript execution

        Raises:
            Exception: If scraping fails
        """
        logger.info(f"Scraping with Selenium from: {self.url}")

        # Setup Chrome options
        chrome_options = ChromeOptions()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        driver = None
        try:
            # Initialize Chrome driver
            driver = webdriver.Chrome(options=chrome_options)

            # Load page
            logger.info("Loading page...")
            driver.get(self.url)

            # Wait for content to load (look for cluster headers)
            logger.info("Waiting for JavaScript to load content...")
            try:
                # Wait up to 30 seconds for at least one cluster to appear
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Cluster')]"))
                )
                logger.info("Content loaded successfully")
            except Exception as e:
                logger.info(f"Warning: Timeout waiting for content: {e}")

            # Additional wait to ensure all content is rendered
            time.sleep(3)

            # Get rendered HTML
            html_content = driver.page_source
            logger.info(f"Successfully scraped ({len(html_content)} bytes)")

            return html_content

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise

        finally:
            if driver:
                driver.quit()

    def download_data(self) -> str:
        """
        Download the OVH IP documentation HTML page.
        Uses Selenium if available, otherwise falls back to simple requests.

        Returns:
            str: HTML content

        Raises:
            requests.RequestException: If download fails
        """
        if self.use_selenium:
            try:
                self.html_content = self.scrape_with_selenium()
                return self.html_content
            except Exception as e:
                logger.info(f"Selenium scraping failed: {e}")
                logger.info("Falling back to static data file...")
                self.use_static_data = True
                return ""
        else:
            logger.info(f"Downloading from: {self.url} (basic request)")
            try:
                response = requests.get(self.url, timeout=60)
                response.raise_for_status()
                self.html_content = response.text
                logger.info(f"Downloaded HTML content ({len(self.html_content)} bytes)")
                return self.html_content
            except requests.RequestException as e:
                logger.error(f"Error downloading data: {e}")
                self.use_static_data = True
                return ""

    def extract_ips_from_static_data(self) -> tuple:
        """
        Extract IP ranges from static JSON data file.

        Returns:
            Tuple of (services_ips, all_ips)
            - services_ips: Dict mapping cluster/service names to IP sets
            - all_ips: Set of all IP ranges
        """
        logger.info(f"Using static data file: {self.data_file}")

        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        services_ips = {}
        all_ips = set()

        # Process clusters
        for cluster_num, cluster_data in data.get('clusters', {}).items():
            cluster_name = f"Cluster-{cluster_num}"

            # Main cluster IPs
            if 'main' in cluster_data:
                for country, ips in cluster_data['main'].items():
                    for ip in ips:
                        if is_valid_ip(ip):
                            # Add to cluster
                            if cluster_name not in services_ips:
                                services_ips[cluster_name] = set()
                            services_ips[cluster_name].add(ip)
                            all_ips.add(ip)

            # CDN IPs
            if 'cdn' in cluster_data:
                cdn_name = f"{cluster_name}-CDN"
                for ip in cluster_data['cdn']:
                    if is_valid_ip(ip):
                        if cdn_name not in services_ips:
                            services_ips[cdn_name] = set()
                        services_ips[cdn_name].add(ip)
                        all_ips.add(ip)

            # Gateway IPs
            if 'gateway' in cluster_data:
                gateway_name = f"{cluster_name}-Gateway"
                for ip in cluster_data['gateway']:
                    if is_valid_ip(ip):
                        if gateway_name not in services_ips:
                            services_ips[gateway_name] = set()
                        services_ips[gateway_name].add(ip)
                        all_ips.add(ip)

        return services_ips, all_ips

    def extract_ips_from_html(self) -> tuple:
        """
        Parse HTML content to extract IP ranges from OVH clusters.
        Works with Selenium-rendered content.

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

        # Pattern to match IP addresses (relaxed boundaries to handle "Copy" button text)
        ipv4_pattern = re.compile(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}')
        ipv6_pattern = re.compile(r'(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}')

        # Pattern to detect country codes (2 uppercase letters)
        country_code_pattern = re.compile(r'\b([A-Z]{2})\b')

        # Find all h3 elements containing cluster headers
        cluster_headers = soup.find_all('h3', string=re.compile(r'Cluster\s+\d+', re.IGNORECASE))

        logger.info(f"Found {len(cluster_headers)} clusters")

        for h3 in cluster_headers:
            # Extract cluster number
            cluster_match = re.search(r'Cluster\s+(\d+)', h3.get_text(), re.IGNORECASE)
            if not cluster_match:
                continue

            cluster_num = cluster_match.group(1).zfill(3)

            # Initialize cluster data structure
            clusters_data[cluster_num] = {
                'main': set(),
                'cdn': set(),
                'gateway': set(),
                'countries': {}
            }

            # Find the table following this h3
            table = h3.find_next('table')
            if table:
                # Extract IPs from table rows (organized by country)
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])

                    if len(cells) < 3:  # Skip header or incomplete rows
                        continue

                    row_text = ' '.join([cell.get_text() for cell in cells])

                    # Try to find country code in this row
                    country_match = country_code_pattern.search(row_text)
                    current_country = country_match.group(1) if country_match else None

                    # Extract all IPs from this row
                    row_ips = set()

                    for cell in cells:
                        text = cell.get_text()

                        # Extract IPv4
                        for ip in ipv4_pattern.findall(text):
                            if is_valid_ip(ip):
                                row_ips.add(ip)
                                all_ips.add(ip)

                        # Extract IPv6
                        for ip in ipv6_pattern.findall(text):
                            if is_valid_ip(ip):
                                row_ips.add(ip)
                                all_ips.add(ip)

                    # Add IPs to cluster main
                    clusters_data[cluster_num]['main'].update(row_ips)

                    # Add IPs to country if we found one
                    if current_country and row_ips:
                        # Add to this cluster's country data
                        if current_country not in clusters_data[cluster_num]['countries']:
                            clusters_data[cluster_num]['countries'][current_country] = set()
                        clusters_data[cluster_num]['countries'][current_country].update(row_ips)

                        # Add to global countries data
                        if current_country not in countries_data:
                            countries_data[current_country] = set()
                        countries_data[current_country].update(row_ips)

            # Look for CDN and Gateway info after the table
            next_sibling = table.find_next_sibling() if table else h3.find_next_sibling()
            section_count = 0
            while next_sibling and section_count < 10:  # Limit search
                text = next_sibling.get_text()

                # CDN section - look for "CDN" keyword, then check this and next element for IPs
                if 'CDN' in text or 'cdn' in text.lower():
                    # Check current element
                    for ip in ipv4_pattern.findall(text):
                        if is_valid_ip(ip):
                            clusters_data[cluster_num]['cdn'].add(ip)
                            all_ips.add(ip)

                    # Also check next sibling (IP might be in next <div>/<pre> element)
                    next_elem = next_sibling.find_next_sibling()
                    if next_elem:
                        next_text = next_elem.get_text()
                        for ip in ipv4_pattern.findall(next_text):
                            if is_valid_ip(ip):
                                clusters_data[cluster_num]['cdn'].add(ip)
                                all_ips.add(ip)

                # Gateway section - look for "gateway" or "outgoing" keywords
                if 'gateway' in text.lower() or 'outgoing' in text.lower():
                    # Check current element
                    for ip in ipv4_pattern.findall(text):
                        if is_valid_ip(ip):
                            clusters_data[cluster_num]['gateway'].add(ip)
                            all_ips.add(ip)

                    # Also check next sibling (IP might be in next <div>/<pre> element)
                    next_elem = next_sibling.find_next_sibling()
                    if next_elem:
                        next_text = next_elem.get_text()
                        for ip in ipv4_pattern.findall(next_text):
                            if is_valid_ip(ip):
                                clusters_data[cluster_num]['gateway'].add(ip)
                                all_ips.add(ip)

                # Stop if we hit next cluster
                if re.search(r'Cluster\s+\d+', text, re.IGNORECASE):
                    break

                next_sibling = next_sibling.find_next_sibling()
                section_count += 1

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

        # Try scraping first
        if not self.html_content:
            self.download_data()

        # Extract data from HTML
        if not self.use_static_data:
            logger.info("Parsing scraped content...")
            clusters_data, countries_data, all_ips = self.extract_ips_from_html()
        else:
            logger.info("Error: Static data fallback not yet implemented for new structure")
            clusters_data, countries_data, all_ips = {}, {}, set()

        if not all_ips:
            logger.info("Warning: No IP ranges found!")
            if not SELENIUM_AVAILABLE:
                logger.info("Tip: Install Selenium for automatic scraping: pip install selenium")
            return

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


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download OVH IP ranges from HTML and generate organized files"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        syncer = OVHIP(config_path=args.config)
        syncer.generate_files()
    except Exception as e:
        logger.error(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
