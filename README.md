# CloudIPAtlas

Automated collector for cloud provider IP ranges. Syncs daily with 17+ providers including AWS, Azure, GCP, and more.

Aggregates, organizes, and maintains up-to-date IP ranges from major cloud providers, CDNs, and network services. Perfect for firewall rules, security policies, and network automation.

**Note:** CloudIPAtlas uses official provider sources directly, not ASN databases. This ensures accuracy and includes provider-specific metadata (services, regions) that ASN databases don't provide.

## Supported cloud providers


| Provider | Description | Data |
|----------|-------------|------|
| **Amazon Web Services** | AWS IP ranges (services + regions) | [View](cloud_ips/aws/) |
| **Microsoft Azure** | Azure Service Tags (95+ services, regional data) | [View](cloud_ips/azure/) |
| **Cloudflare** | Cloudflare CDN and network IP ranges | [View](cloud_ips/cloudflare/) |
| **DigitalOcean** | DigitalOcean IP ranges by region | [View](cloud_ips/digitalocean/) |
| **Fastly** | Fastly CDN IP ranges | [View](cloud_ips/fastly/) |
| **Google Cloud Platform** | GCP IP ranges (services + scopes) | [View](cloud_ips/gcp/) |
| **IBM Cloud** | IBM Cloud infrastructure IP ranges | [View](cloud_ips/ibm_cloud/) |
| **Linode** | Linode/Akamai IP ranges by region | [View](cloud_ips/linode/) |
| **Oracle Cloud Infrastructure** | OCI IP ranges (regions + tags) | [View](cloud_ips/oci/) |
| **OVHcloud** | OVH IP ranges (web hosting clusters) | [View](cloud_ips/ovh/) |
| **Scaleway** | Scaleway infrastructure IP ranges | [View](cloud_ips/scaleway/) |
| **Starlink** | Starlink satellite internet IP ranges | [View](cloud_ips/starlink/) |
| **Vultr** | Vultr cloud computing IP ranges | [View](cloud_ips/vultr/) |
| **Zscaler** | Zscaler security cloud IP ranges | [View](cloud_ips/zscaler/) |

