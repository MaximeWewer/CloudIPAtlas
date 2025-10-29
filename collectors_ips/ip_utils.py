"""
Shared utility module for IP range processing across cloud providers.
Provides common functions for IP validation, sorting, file operations, and reporting.
"""

import os
import logging
import ipaddress
from typing import List, Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def is_ipv6(ip_range: str) -> bool:
    """
    Determine if an IP range is IPv6.

    Args:
        ip_range: IP address or CIDR range (e.g., "192.168.1.0/24" or "2001:db8::/32")

    Returns:
        True if IPv6, False if IPv4
    """
    try:
        return isinstance(ipaddress.ip_network(ip_range, strict=False), ipaddress.IPv6Network)
    except ValueError:
        return False


def is_valid_ip(ip_range: str) -> bool:
    """
    Validate if a string is a valid IP address or CIDR range.

    Args:
        ip_range: IP address or CIDR range

    Returns:
        True if valid, False otherwise
    """
    try:
        ipaddress.ip_network(ip_range, strict=False)
        return True
    except ValueError:
        return False


def is_private_ip(ip_range: str) -> bool:
    """
    Check if an IP address or CIDR range is private.

    Args:
        ip_range: IP address or CIDR range

    Returns:
        True if private, False if public
    """
    try:
        network = ipaddress.ip_network(ip_range, strict=False)
        return network.is_private
    except ValueError:
        return False


def separate_ipv4_ipv6(ip_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Separate a list of IP ranges into IPv4 and IPv6 lists.

    Args:
        ip_list: List of IP ranges in CIDR notation

    Returns:
        Tuple of (ipv4_list, ipv6_list)
    """
    ipv4_list = []
    ipv6_list = []

    for ip_range in ip_list:
        if not is_valid_ip(ip_range):
            continue

        if is_ipv6(ip_range):
            ipv6_list.append(ip_range)
        else:
            ipv4_list.append(ip_range)

    return ipv4_list, ipv6_list


def separate_single_ips_and_ranges(ip_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Separate single IPs from CIDR ranges.

    Args:
        ip_list: List of IP addresses and CIDR ranges

    Returns:
        Tuple of (single_ips, cidr_ranges)
        - single_ips: IPs without CIDR notation (no slash)
        - cidr_ranges: IPs with CIDR notation (with slash)
    """
    single_ips = []
    cidr_ranges = []

    for ip in ip_list:
        if '/' in ip:
            cidr_ranges.append(ip)
        else:
            single_ips.append(ip)

    return single_ips, cidr_ranges


def sort_ip_list(ip_list: List[str]) -> List[str]:
    """
    Sort IP ranges numerically (not alphabetically).
    Separates IPv4 and IPv6 first, then sorts each separately.

    Args:
        ip_list: List of IP ranges in CIDR notation

    Returns:
        Sorted list of IP ranges (IPv4 first, then IPv6)
    """
    try:
        # Separate IPv4 and IPv6
        ipv4_list = []
        ipv6_list = []

        for ip in ip_list:
            if is_ipv6(ip):
                ipv6_list.append(ip)
            else:
                ipv4_list.append(ip)

        # Sort each separately
        ipv4_sorted = sorted(ipv4_list, key=lambda x: ipaddress.ip_network(x, strict=False))
        ipv6_sorted = sorted(ipv6_list, key=lambda x: ipaddress.ip_network(x, strict=False))

        # Return IPv4 first, then IPv6
        return ipv4_sorted + ipv6_sorted
    except (ValueError, TypeError):
        # Fallback to alphabetical sort if parsing fails
        return sorted(ip_list)


def calculate_total_ips(ip_list: List[str]) -> int:
    """
    Calculate total number of IP addresses in a list of CIDR ranges.
    Note: For IPv6, returns count of /64 subnets instead of individual IPs.

    Args:
        ip_list: List of IP ranges in CIDR notation

    Returns:
        Total IP count (or subnet count for IPv6)
    """
    total = 0
    for ip_range in ip_list:
        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            if isinstance(network, ipaddress.IPv6Network):
                # For IPv6, count /64 subnets instead of individual IPs
                total += network.num_addresses // (2 ** (128 - 64))
            else:
                total += network.num_addresses
        except ValueError:
            continue
    return total


def ensure_directory(directory: str) -> None:
    """
    Create directory if it doesn't exist.

    Args:
        directory: Path to directory
    """
    os.makedirs(directory, exist_ok=True)


def write_ip_file(file_path: str, ip_list: List[str], sort_ips: bool = True) -> None:
    """
    Write IP ranges to a file (one per line, no headers).

    Args:
        file_path: Output file path
        ip_list: List of IP ranges in CIDR notation
        sort_ips: Whether to sort the IPs before writing (default: True)
    """
    if sort_ips:
        ip_list = sort_ip_list(ip_list)

    ensure_directory(os.path.dirname(file_path))

    with open(file_path, 'w', encoding='utf-8') as f:
        for ip_range in ip_list:
            f.write(f"{ip_range}\n")


def write_separated_ip_files(base_path: str, ip_list: List[str], suffix: str = "all") -> None:
    """
    Write IP files separated into single IPs and CIDR ranges.

    Creates files based on content:
    - {base_path}_single_{suffix}.txt: Only single IPs (no CIDR) - if present
    - {base_path}_ranges_{suffix}.txt: Only CIDR ranges - if present

    Args:
        base_path: Base file path without extension (e.g., "azure/ips")
        ip_list: List of IP addresses and CIDR ranges
        suffix: Suffix for the file (e.g., "all", "ipv4", "ipv6")
    """
    if not ip_list:
        return

    # Separate single IPs from ranges
    single_ips, cidr_ranges = separate_single_ips_and_ranges(ip_list)

    # Write single IPs file if any
    if single_ips:
        write_ip_file(f"{base_path}_single_{suffix}.txt", single_ips)

    # Write ranges file if any
    if cidr_ranges:
        write_ip_file(f"{base_path}_ranges_{suffix}.txt", cidr_ranges)


def generate_index_markdown(
    provider_name: str,
    total_ranges: int,
    ipv4_ranges: int,
    ipv6_ranges: int,
    ipv4_count: int,
    ipv6_count: int,
    services: Optional[Dict[str, int]] = None,
    regions: Optional[Dict[str, int]] = None,
    last_updated: Optional[str] = None,
    ipv4_single: Optional[int] = None,
    ipv6_single: Optional[int] = None,
    ipv4_ranges_only: Optional[int] = None,
    ipv6_ranges_only: Optional[int] = None
) -> str:
    """
    Generate markdown content for index.md file.

    Args:
        provider_name: Cloud provider name (e.g., "Azure", "AWS")
        total_ranges: Total number of IP ranges
        ipv4_ranges: Number of IPv4 ranges
        ipv6_ranges: Number of IPv6 ranges
        ipv4_count: Total IPv4 addresses
        ipv6_count: Total IPv6 addresses (or /64 subnets)
        services: Optional dict of service names to IP range counts
        regions: Optional dict of region names to IP range counts
        last_updated: Optional timestamp string (uses current time if None)
        ipv4_single: Number of single IPv4 addresses (no CIDR)
        ipv6_single: Number of single IPv6 addresses (no CIDR)
        ipv4_ranges_only: Number of IPv4 CIDR ranges
        ipv6_ranges_only: Number of IPv6 CIDR ranges

    Returns:
        Markdown formatted string
    """
    if last_updated is None:
        last_updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    md = f"# {provider_name} IP Ranges\n\n"
    md += f"Last updated: {last_updated}\n\n"
    md += "## Summary Statistics\n\n"

    # If detailed stats provided, show breakdown
    if ipv4_single is not None and ipv4_ranges_only is not None:
        md += f"- **Total IPs/Ranges**: {total_ranges:,}\n"
        if ipv4_single > 0:
            md += f"- **IPv4 single IPs**: {ipv4_single:,}\n"
        if ipv4_ranges_only > 0:
            md += f"- **IPv4 ranges**: {ipv4_ranges_only:,} ({ipv4_count:,} addresses)\n"
        if ipv6_single is not None and ipv6_single > 0:
            md += f"- **IPv6 single IPs**: {ipv6_single:,}\n"
        if ipv6_ranges_only is not None and ipv6_ranges_only > 0:
            md += f"- **IPv6 ranges**: {ipv6_ranges_only:,} ({ipv6_count:,} /64 subnets)\n"
    else:
        # Legacy format
        md += f"- **Total IP ranges**: {total_ranges:,}\n"
        md += f"- **IPv4 ranges**: {ipv4_ranges:,} ({ipv4_count:,} addresses)\n"
        md += f"- **IPv6 ranges**: {ipv6_ranges:,} ({ipv6_count:,} /64 subnets)\n"

    md += "\n"

    if services:
        md += f"## Services ({len(services)})\n\n"
        md += "| Service | IP Ranges |\n"
        md += "|---------|----------:|\n"
        for service, count in sorted(services.items()):
            md += f"| {service} | {count:,} |\n"
        md += "\n"

    if regions:
        md += f"## Regions ({len(regions)})\n\n"
        md += "| Region | IP Ranges |\n"
        md += "|--------|----------:|\n"
        for region, count in sorted(regions.items()):
            md += f"| {region} | {count:,} |\n"
        md += "\n"

    return md


def calculate_detailed_stats(all_ips: List[str], all_ipv4: List[str], all_ipv6: List[str]) -> Dict[str, int]:
    """
    Calculate detailed statistics distinguishing single IPs from ranges.

    Args:
        all_ips: List of all IP addresses/ranges
        all_ipv4: List of IPv4 addresses/ranges
        all_ipv6: List of IPv6 addresses/ranges

    Returns:
        Dictionary with detailed statistics including:
        - total: Total count
        - ipv4_ranges: Total IPv4 count
        - ipv6_ranges: Total IPv6 count
        - ipv4_count: Total IPv4 addresses
        - ipv4_single: Number of single IPv4 addresses
        - ipv6_single: Number of single IPv6 addresses
        - ipv4_ranges_only: Number of IPv4 CIDR ranges
        - ipv6_ranges_only: Number of IPv6 CIDR ranges
    """
    ipv4_single, ipv4_ranges_list = separate_single_ips_and_ranges(all_ipv4)
    ipv6_single, ipv6_ranges_list = separate_single_ips_and_ranges(all_ipv6)

    return {
        'total': len(all_ips),
        'ipv4_ranges': len(all_ipv4),
        'ipv6_ranges': len(all_ipv6),
        'ipv4_count': calculate_total_ips(all_ipv4),
        'ipv4_single': len(ipv4_single),
        'ipv6_single': len(ipv6_single),
        'ipv4_ranges_only': len(ipv4_ranges_list),
        'ipv6_ranges_only': len(ipv6_ranges_list)
    }


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be used as a filename.
    Removes or replaces special characters.

    Args:
        name: Original name

    Returns:
        Sanitized filename-safe string
    """
    # Replace spaces and special characters
    name = name.lower()
    name = name.replace(' ', '_')
    name = name.replace('.', '_')
    name = ''.join(c for c in name if c.isalnum() or c in ['_', '-'])
    return name


def print_summary(provider_name: str, stats: Dict[str, any]) -> None:
    """
    Print a summary of processed IP ranges to console.

    Args:
        provider_name: Cloud provider name
        stats: Dictionary with statistics (total, ipv4_count, ipv6_count, etc.)
               Can include: ipv4_single, ipv6_single, ipv4_ranges_only, ipv6_ranges_only
    """
    logger.info("")
    logger.info("="*60)
    logger.info(f"{provider_name} IP Ranges Summary")
    logger.info("="*60)

    # Check if we have detailed breakdown
    if 'ipv4_single' in stats or 'ipv4_ranges_only' in stats:
        logger.info(f"Total IPs/ranges: {stats.get('total', 0):,}")

        # IPv4 breakdown
        ipv4_single = stats.get('ipv4_single', 0)
        ipv4_ranges = stats.get('ipv4_ranges_only', 0)
        if ipv4_single > 0:
            logger.info(f"IPv4 single IPs: {ipv4_single:,}")
        if ipv4_ranges > 0:
            logger.info(f"IPv4 ranges: {ipv4_ranges:,} ({stats.get('ipv4_count', 0):,} IPs)")

        # IPv6 breakdown
        ipv6_single = stats.get('ipv6_single', 0)
        ipv6_ranges = stats.get('ipv6_ranges_only', 0)
        if ipv6_single > 0:
            logger.info(f"IPv6 single IPs: {ipv6_single:,}")
        if ipv6_ranges > 0:
            logger.info(f"IPv6 ranges: {ipv6_ranges:,}")
    else:
        # Legacy format
        logger.info(f"Total IP ranges: {stats.get('total', 0):,}")
        logger.info(f"IPv4 ranges: {stats.get('ipv4_ranges', 0):,} ({stats.get('ipv4_count', 0):,} IPs)")
        logger.info(f"IPv6 ranges: {stats.get('ipv6_ranges', 0):,}")

    if 'services' in stats:
        logger.info(f"Services: {stats['services']}")

    if 'regions' in stats:
        logger.info(f"Regions: {stats['regions']}")

    logger.info(f"Output directory: {stats.get('output_dir', 'N/A')}")
    logger.info("="*60)
    logger.info("")
