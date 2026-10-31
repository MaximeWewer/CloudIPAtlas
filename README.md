# CloudIPAtlas

Automated collector for cloud provider IP ranges. Syncs daily with 20+ providers including AWS, Azure, GCP, and more.

Aggregates, organizes, and maintains up-to-date IP ranges from major cloud providers, crawlers, CDNs, and network services. Perfect for firewall rules, security policies, and network automation.

**Note:** CloudIPAtlas uses official provider sources directly, not ASN databases. This ensures accuracy and includes provider-specific metadata (services, regions) that ASN databases don't provide.

## Supported cloud providers


| Provider | Description | Data |
|----------|-------------|------|
| **Ahrefs** | Ahrefs SEO crawler IP addresses | [View](cloud_ips/ahrefs/) |
| **Amazonbot** | Amazon crawler (Amazonbot) IP ranges | [View](cloud_ips/amazonbot/) |
| **Applebot** | Apple crawler IP ranges | [View](cloud_ips/applebot/) |
| **Amazon Web Services** | AWS IP ranges (services + regions) | [View](cloud_ips/aws/) |
| **Microsoft Azure** | Azure Service Tags (95+ services, regional data) | [View](cloud_ips/azure/) |
| **Bingbot** | Bing crawler IP ranges | [View](cloud_ips/bingbot/) |
| **Bunny CDN** | Bunny CDN edge server IP addresses | [View](cloud_ips/bunnycdn/) |
| **Common Crawl** | Common Crawl crawler (CCBot) IP ranges | [View](cloud_ips/ccbot/) |
| **Cloudflare** | Cloudflare CDN and network IP ranges | [View](cloud_ips/cloudflare/) |
| **DigitalOcean** | DigitalOcean IP ranges by region | [View](cloud_ips/digitalocean/) |
| **DuckDuckBot** | DuckDuckGo crawler IP ranges | [View](cloud_ips/duckduckbot/) |
| **Exoscale** | Exoscale European cloud IP ranges | [View](cloud_ips/exoscale/) |
| **Fastly** | Fastly CDN IP ranges | [View](cloud_ips/fastly/) |
| **Gcore** | Gcore CDN IP ranges | [View](cloud_ips/gcore/) |
| **Google Cloud Platform** | GCP IP ranges (services + scopes) | [View](cloud_ips/gcp/) |
| **GitHub** | GitHub services IP ranges (actions, pages, hooks, api, etc.) | [View](cloud_ips/github/) |
| **Googlebot** | Google crawlers and user-triggered fetchers IP ranges | [View](cloud_ips/googlebot/) |
| **Hetzner** | Hetzner IPv4 ranges by city | [View](cloud_ips/hetzner/) |
| **IBM Cloud** | IBM Cloud infrastructure IP ranges | [View](cloud_ips/ibm_cloud/) |
| **Linode** | Linode/Akamai IP ranges by region | [View](cloud_ips/linode/) |
| **Meta** | Meta/Facebook crawler IP ranges | [View](cloud_ips/meta/) |
| **Mistral AI** | Mistral AI user-triggered fetcher IP ranges | [View](cloud_ips/mistral/) |
| **Oracle Cloud Infrastructure** | OCI IP ranges (regions + tags) | [View](cloud_ips/oci/) |
| **OpenAI** | OpenAI ChatGPT-User, GPTBot and OAI-SearchBot IP ranges | [View](cloud_ips/openai/) |
| **Outscale** | Outscale cloud IP ranges | [View](cloud_ips/outscale/) |
| **OVHcloud** | OVH IP ranges (web hosting clusters) | [View](cloud_ips/ovh/) |
| **Perplexity** | Perplexity AI crawler IP ranges | [View](cloud_ips/perplexity/) |
| **Scaleway** | Scaleway infrastructure IP ranges | [View](cloud_ips/scaleway/) |
| **Starlink** | Starlink satellite internet IP ranges | [View](cloud_ips/starlink/) |
| **Vultr** | Vultr cloud computing IP ranges | [View](cloud_ips/vultr/) |
| **Yandex** | Yandex network IP ranges (incl. YandexBot) | [View](cloud_ips/yandex/) |
| **Zscaler** | Zscaler security cloud IP ranges | [View](cloud_ips/zscaler/) |

