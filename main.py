#!/usr/bin/env python3
"""
Multi-Cloud IP - Orchestrator script for all cloud providers.

This script runs all cloud provider IP scripts in parallel and
generates a consolidated summary report.
"""

import os
import sys
import logging
import time
import threading
from typing import Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

# Custom formatter for cleaner logs
class CleanFormatter(logging.Formatter):
    """Custom formatter for cleaner output."""

    def format(self, record):
        # For collector-specific logs (e.g., collectors_ips.azure) - suppress them
        if '.' in record.name and record.name.startswith('collectors_ips.'):
            return None  # Suppress provider logs

        # For main orchestrator logs
        if record.name == 'root':
            return record.getMessage()

        # For errors, include level
        if record.levelname == 'ERROR':
            return f"[ERROR] {record.getMessage()}"

        return record.getMessage()

# Configure logging with custom formatter
handler = logging.StreamHandler()
handler.setFormatter(CleanFormatter())

# Filter to suppress None messages
class NonNoneFilter(logging.Filter):
    def filter(self, record):
        formatter = handler.formatter
        if formatter:
            result = formatter.format(record)
            return result is not None
        return True

handler.addFilter(NonNoneFilter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)

logger = logging.getLogger()

class ProgressMonitor:
    """Monitor and display progress of provider execution."""

    def __init__(self, total_providers: int):
        self.total_providers = total_providers
        self.completed: Set[str] = set()
        self.in_progress: Set[str] = set()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.start_time = time.time()

    def start_provider(self, provider_name: str):
        """Mark a provider as started."""
        with self.lock:
            self.in_progress.add(provider_name)

    def complete_provider(self, provider_name: str):
        """Mark a provider as completed."""
        with self.lock:
            if provider_name in self.in_progress:
                self.in_progress.remove(provider_name)
            self.completed.add(provider_name)

    def display_progress(self):
        """Display current progress."""
        with self.lock:
            elapsed = time.time() - self.start_time
            completed_count = len(self.completed)
            in_progress_count = len(self.in_progress)
            pending_count = self.total_providers - completed_count - in_progress_count

            status_line = f"[{elapsed:>6.1f}s] Progress: {completed_count}/{self.total_providers} completed"

            if self.in_progress:
                in_progress_list = ', '.join(sorted(self.in_progress))
                logger.info(f"{status_line} | In progress: {in_progress_list}")
            else:
                logger.info(status_line)

    def monitor_loop(self):
        """Monitor loop that displays progress every 3 seconds."""
        while not self.stop_event.is_set():
            self.stop_event.wait(3)  # Wait for 3 seconds or until stopped
            if not self.stop_event.is_set():
                self.display_progress()

    def stop(self):
        """Stop the monitoring loop."""
        self.stop_event.set()

def run_provider(provider_name: str, monitor: ProgressMonitor = None) -> Dict:
    """
    Run a provider script and capture results.

    Args:
        provider_name: Name of cloud provider
        monitor: Progress monitor instance

    Returns:
        Dict with success status and stats
    """
    if monitor:
        monitor.start_provider(provider_name)

    start_time = time.time()

    try:
        # Import and run the collector module
        if provider_name == "Azure":
            from collectors_ips.azure import AzureIP
            collector = AzureIP()
        elif provider_name == "AWS":
            from collectors_ips.aws import AWSIP
            collector = AWSIP()
        elif provider_name == "GCP":
            from collectors_ips.gcp import GCPIP
            collector = GCPIP()
        elif provider_name == "OCI":
            from collectors_ips.oci import OCIIP
            collector = OCIIP()
        elif provider_name == "OVH":
            from collectors_ips.ovh import OVHIP
            collector = OVHIP()
        elif provider_name == "Scaleway":
            from collectors_ips.scaleway import ScalewayIP
            collector = ScalewayIP()
        elif provider_name == "Cloudflare":
            from collectors_ips.cloudflare import CloudflareIP
            collector = CloudflareIP()
        elif provider_name == "Fastly":
            from collectors_ips.fastly import FastlyIP
            collector = FastlyIP()
        elif provider_name == "Linode":
            from collectors_ips.linode import LinodeIP
            collector = LinodeIP()
        elif provider_name == "DigitalOcean":
            from collectors_ips.digitalocean import DigitalOceanIP
            collector = DigitalOceanIP()
        elif provider_name == "Starlink":
            from collectors_ips.starlink import StarlinkIP
            collector = StarlinkIP()
        elif provider_name == "Vultr":
            from collectors_ips.vultr import VultrIP
            collector = VultrIP()
        elif provider_name == "Zscaler":
            from collectors_ips.zscaler import ZscalerIP
            collector = ZscalerIP()
        elif provider_name == "IBM_Cloud":
            from collectors_ips.ibm_cloud import IBMCloudIP
            collector = IBMCloudIP()
        elif provider_name == "Exoscale":
            from collectors_ips.exoscale import ExoscaleIP
            collector = ExoscaleIP()
        elif provider_name == "Googlebot":
            from collectors_ips.googlebot import GooglebotIP
            collector = GooglebotIP()
        elif provider_name == "Outscale":
            from collectors_ips.outscale import OutscaleIP
            collector = OutscaleIP()
        elif provider_name == "Bingbot":
            from collectors_ips.bingbot import BingbotIP
            collector = BingbotIP()
        elif provider_name == "Meta":
            from collectors_ips.meta import MetaIP
            collector = MetaIP()
        elif provider_name == "OpenAI":
            from collectors_ips.openai import OpenAIIP
            collector = OpenAIIP()
        elif provider_name == "Perplexity":
            from collectors_ips.perplexity import PerplexityIP
            collector = PerplexityIP()
        elif provider_name == "GitHub":
            from collectors_ips.github import GitHubIP
            collector = GitHubIP()
        elif provider_name == "Ahrefs":
            from collectors_ips.ahrefs import AhrefsIP
            collector = AhrefsIP()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Generate files
        collector.generate_files()

        elapsed_time = time.time() - start_time

        if monitor:
            monitor.complete_provider(provider_name)

        return {
            'success': True,
            'error': None,
            'elapsed_time': elapsed_time
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Failed to process {provider_name}: {e}", exc_info=True)

        if monitor:
            monitor.complete_provider(provider_name)

        return {
            'success': False,
            'error': str(e),
            'elapsed_time': elapsed_time
        }


def count_files_in_directory(directory: str) -> int:
    """Count number of files in a directory recursively."""
    if not os.path.exists(directory):
        return 0

    count = 0
    for root, dirs, files in os.walk(directory):
        count += len(files)
    return count


def generate_summary_report(results: Dict[str, Dict], total_elapsed_time: float) -> None:
    """
    Generate and log a summary report of all operations.

    Args:
        results: Dictionary mapping provider names to their results
        total_elapsed_time: Total elapsed time for all operations
    """
    successful = sum(1 for r in results.values() if r['success'])
    failed = len(results) - successful

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("EXECUTION SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Total duration: {total_elapsed_time:.2f}s | Providers: {len(results)} | Success: {successful} | Failed: {failed}")

    if failed > 0:
        logger.info(f"\n{'='*70}")
        logger.info("FAILED PROVIDERS")
        logger.info(f"{'='*70}")
        for provider_name, result in results.items():
            if not result['success']:
                logger.error(f"{provider_name}: {result['error']}")

    # Sort results by completion time
    sorted_results = sorted(results.items(), key=lambda x: x[1]['elapsed_time'])

    logger.info(f"\n{'='*70}")
    logger.info("PROVIDER DETAILS (sorted by duration)")
    logger.info(f"{'='*70}")
    for provider_name, result in sorted_results:
        provider_dir = os.path.join("cloud_ips", provider_name.lower())
        file_count = count_files_in_directory(provider_dir) if os.path.exists(provider_dir) else 0
        status = "OK" if result['success'] else "FAILED"
        logger.info(f"{provider_name:<20} [{status:<6}] {result['elapsed_time']:>6.2f}s | {file_count:>3} files")

    logger.info(f"{'='*70}\n")


def main():
    """Main entry point for the orchestrator script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-cloud IP ranges orchestrator"
    )
    parser.add_argument(
        "-p", "--providers",
        nargs='+',
        choices=['azure', 'aws', 'gcp', 'oci', 'ovh', 'scaleway',
                 'cloudflare', 'fastly', 'linode', 'digitalocean',
                 'starlink', 'vultr', 'zscaler', 'ibm-cloud', 'exoscale', 'googlebot', 'outscale', 'bingbot', 'meta', 'openai', 'perplexity', 'github', 'ahrefs', 'all'],
        default=['all'],
        help="Specific providers to process (default: all)"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    # Check if config exists
    if not os.path.exists(args.config):
        logger.error(f"Error: Configuration file '{args.config}' not found!")
        sys.exit(1)

    # Define all available providers
    all_providers = [
        'Azure', 'AWS', 'GCP', 'OCI', 'OVH', 'Scaleway',
        'Cloudflare', 'Fastly', 'Linode', 'DigitalOcean',
        'Starlink', 'Vultr', 'Zscaler', 'IBM_Cloud', 'Exoscale', 'Googlebot', 'Outscale', 'Bingbot', 'Meta', 'OpenAI', 'Perplexity', 'GitHub', 'Ahrefs'
    ]

    # Filter providers based on arguments
    if 'all' in args.providers:
        providers_to_process = all_providers
    else:
        providers_to_process = [
            name for name in all_providers
            if name.lower().replace('_', '') in [p.replace('-', '').replace('_', '') for p in args.providers]
        ]

    logger.info(f"\n{'='*70}")
    logger.info("MULTI-CLOUD IP RANGES COLLECTOR")
    logger.info(f"{'='*70}")
    logger.info(f"Configuration: {args.config}")
    logger.info(f"Providers: {len(providers_to_process)} ({', '.join(providers_to_process)})")
    logger.info(f"{'='*70}\n")

    # Start global timer
    global_start_time = time.time()

    # Create progress monitor
    monitor = ProgressMonitor(len(providers_to_process))

    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor.monitor_loop, daemon=True)
    monitor_thread.start()

    # Run each provider in parallel
    results = {}
    max_workers = os.cpu_count()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all providers to the thread pool
        future_to_provider = {
            executor.submit(run_provider, provider_name, monitor): provider_name
            for provider_name in providers_to_process
        }

        # Collect results as they complete
        for future in as_completed(future_to_provider):
            provider_name = future_to_provider[future]
            try:
                results[provider_name] = future.result()
            except Exception as exc:
                logger.error(f"Provider {provider_name} generated an exception: {exc}")
                results[provider_name] = {
                    'success': False,
                    'error': str(exc),
                    'elapsed_time': 0
                }
                monitor.complete_provider(provider_name)

    # Stop monitoring thread
    monitor.stop()
    monitor_thread.join(timeout=1)

    # Calculate total elapsed time
    total_elapsed_time = time.time() - global_start_time

    # Generate and display summary report
    generate_summary_report(results, total_elapsed_time)

    # Exit with error code if any provider failed
    if any(not r['success'] for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
