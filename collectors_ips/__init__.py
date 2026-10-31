"""
Cloud provider IP modules.
"""

from .azure import AzureIP
from .aws import AWSIP
from .gcp import GCPIP
from .oci import OCIIP
from .ovh import OVHIP
from .scaleway import ScalewayIP
from .cloudflare import CloudflareIP
from .fastly import FastlyIP
from .linode import LinodeIP
from .digitalocean import DigitalOceanIP
from .starlink import StarlinkIP
from .vultr import VultrIP
from .zscaler import ZscalerIP
from .ibm_cloud import IBMCloudIP
from .exoscale import ExoscaleIP
from .googlebot import GooglebotIP
from .outscale import OutscaleIP
from .bingbot import BingbotIP
from .meta import MetaIP
from .openai import OpenAIIP
from .perplexity import PerplexityIP
from .github import GitHubIP
from .ahrefs import AhrefsIP
from .applebot import ApplebotIP
from .duckduckbot import DuckDuckBotIP
from .ccbot import CCBotIP
from .mistral import MistralIP

# Provider display name -> collector class. The output directory is the lowercased name.
COLLECTORS = {
    'Azure': AzureIP,
    'AWS': AWSIP,
    'GCP': GCPIP,
    'OCI': OCIIP,
    'OVH': OVHIP,
    'Scaleway': ScalewayIP,
    'Cloudflare': CloudflareIP,
    'Fastly': FastlyIP,
    'Linode': LinodeIP,
    'DigitalOcean': DigitalOceanIP,
    'Starlink': StarlinkIP,
    'Vultr': VultrIP,
    'Zscaler': ZscalerIP,
    'IBM_Cloud': IBMCloudIP,
    'Exoscale': ExoscaleIP,
    'Googlebot': GooglebotIP,
    'Outscale': OutscaleIP,
    'Bingbot': BingbotIP,
    'Meta': MetaIP,
    'OpenAI': OpenAIIP,
    'Perplexity': PerplexityIP,
    'GitHub': GitHubIP,
    'Ahrefs': AhrefsIP,
    'Applebot': ApplebotIP,
    'DuckDuckBot': DuckDuckBotIP,
    'CCBot': CCBotIP,
    'Mistral': MistralIP,
}

__all__ = ['COLLECTORS']
