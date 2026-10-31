"""
Shared utility module for IP range processing across cloud providers.
Provides common functions for IP validation, sorting, file operations, and reporting.
"""

import os
import logging
import ipaddress
from typing import Collection, Iterable, List, Dict, Tuple, Optional
from datetime import datetime, timezone

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
                # For IPv6, count /64 subnets instead of individual IPs (at least one per prefix)
                total += max(1, network.num_addresses // (2 ** (128 - 64)))
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

def write_ip_group(base_path: str, ip_list: Iterable[str]) -> Tuple[List[str], List[str]]:
    """
    Write the all/ipv4/ipv6 files of one IP group (see write_separated_ip_files).

    Args:
        base_path: Base file path without extension (e.g., "azure/services/storage")
        ip_list: IP addresses and CIDR ranges of the group

    Returns:
        Tuple of (ipv4_list, ipv6_list)
    """
    ipv4, ipv6 = separate_ipv4_ipv6(list(ip_list))
    write_separated_ip_files(base_path, ipv4 + ipv6, "all")
    write_separated_ip_files(base_path, ipv4, "ipv4")
    write_separated_ip_files(base_path, ipv6, "ipv6")
    return ipv4, ipv6


def calculate_detailed_stats(all_ips: Collection[str], all_ipv4: List[str], all_ipv6: List[str]) -> Dict[str, int]:
    """
    Calculate statistics distinguishing single IPs from CIDR ranges.

    Args:
        all_ips: All IP addresses/ranges
        all_ipv4: IPv4 addresses/ranges
        all_ipv6: IPv6 addresses/ranges

    Returns:
        Dictionary with:
        - total: Number of IPs/ranges
        - ipv4_count: Number of IPv4 addresses covered
        - ipv6_count: Number of IPv6 /64 subnets covered
        - ipv4_single / ipv6_single: Number of single IPs (no CIDR)
        - ipv4_ranges / ipv6_ranges: Number of CIDR ranges
    """
    ipv4_single, ipv4_ranges = separate_single_ips_and_ranges(all_ipv4)
    ipv6_single, ipv6_ranges = separate_single_ips_and_ranges(all_ipv6)

    return {
        'total': len(all_ips),
        'ipv4_count': calculate_total_ips(all_ipv4),
        'ipv6_count': calculate_total_ips(all_ipv6),
        'ipv4_single': len(ipv4_single),
        'ipv6_single': len(ipv6_single),
        'ipv4_ranges': len(ipv4_ranges),
        'ipv6_ranges': len(ipv6_ranges)
    }


def generate_index_markdown(
    provider_name: str,
    stats: Dict[str, int],
    services: Optional[Dict[str, int]] = None,
    regions: Optional[Dict[str, int]] = None,
    last_updated: Optional[str] = None
) -> str:
    """
    Generate markdown content for index.md file.

    Args:
        provider_name: Cloud provider name (e.g., "Azure", "AWS")
        stats: Statistics from calculate_detailed_stats()
        services: Optional dict of service names to IP range counts
        regions: Optional dict of region names to IP range counts
        last_updated: Optional timestamp string (uses current time if None)

    Returns:
        Markdown formatted string
    """
    if last_updated is None:
        last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md = f"# {provider_name} IP Ranges\n\n"
    md += f"Last updated: {last_updated}\n\n"
    md += "## Summary Statistics\n\n"
    md += f"- **Total IPs/Ranges**: {stats['total']:,}\n"
    if stats['ipv4_single']:
        md += f"- **IPv4 single IPs**: {stats['ipv4_single']:,}\n"
    if stats['ipv4_ranges']:
        md += f"- **IPv4 ranges**: {stats['ipv4_ranges']:,} ({stats['ipv4_count']:,} addresses)\n"
    if stats['ipv6_single']:
        md += f"- **IPv6 single IPs**: {stats['ipv6_single']:,}\n"
    if stats['ipv6_ranges']:
        md += f"- **IPv6 ranges**: {stats['ipv6_ranges']:,} ({stats['ipv6_count']:,} /64 subnets)\n"
    md += "\n"

    for title, column, counts in (("Services", "Service", services), ("Regions", "Region", regions)):
        if counts:
            md += f"## {title} ({len(counts)})\n\n"
            md += f"| {column} | IP Ranges |\n"
            md += f"|{'-' * (len(column) + 2)}|----------:|\n"
            for name, count in sorted(counts.items()):
                md += f"| {name} | {count:,} |\n"
            md += "\n"

    return md


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


def print_summary(provider_name: str, stats: Dict[str, int], group_counts: Dict[str, int], output_dir: str) -> None:
    """
    Log a summary of processed IP ranges.

    Args:
        provider_name: Cloud provider name
        stats: Statistics from calculate_detailed_stats()
        group_counts: Group subdirectory (e.g. "services") -> number of groups
        output_dir: Output directory of the provider
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"{provider_name} IP Ranges Summary")
    logger.info("=" * 60)
    logger.info(f"Total IPs/ranges: {stats['total']:,}")
    if stats['ipv4_single']:
        logger.info(f"IPv4 single IPs: {stats['ipv4_single']:,}")
    if stats['ipv4_ranges']:
        logger.info(f"IPv4 ranges: {stats['ipv4_ranges']:,} ({stats['ipv4_count']:,} IPs)")
    if stats['ipv6_single']:
        logger.info(f"IPv6 single IPs: {stats['ipv6_single']:,}")
    if stats['ipv6_ranges']:
        logger.info(f"IPv6 ranges: {stats['ipv6_ranges']:,}")
    for group, count in group_counts.items():
        logger.info(f"{group.capitalize()}: {count}")
    logger.info(f"Output directory: {output_dir}")
    logger.info("=" * 60)
    logger.info("")
