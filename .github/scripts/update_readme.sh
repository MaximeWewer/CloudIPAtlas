#!/bin/bash
set -e

# Function to get provider display name and description
get_provider_info() {
    local provider_id="$1"

    case "$provider_id" in
        azure)
            name="Microsoft Azure"
            desc="Azure Service Tags (95+ services, regional data)"
            ;;
        aws)
            name="Amazon Web Services"
            desc="AWS IP ranges (services + regions)"
            ;;
        gcp)
            name="Google Cloud Platform"
            desc="GCP IP ranges (services + scopes)"
            ;;
        oci)
            name="Oracle Cloud Infrastructure"
            desc="OCI IP ranges (regions + tags)"
            ;;
        ovh)
            name="OVHcloud"
            desc="OVH IP ranges (web hosting clusters)"
            ;;
        scaleway)
            name="Scaleway"
            desc="Scaleway infrastructure IP ranges"
            ;;
        cloudflare)
            name="Cloudflare"
            desc="Cloudflare CDN and network IP ranges"
            ;;
        fastly)
            name="Fastly"
            desc="Fastly CDN IP ranges"
            ;;
        linode)
            name="Linode"
            desc="Linode/Akamai IP ranges by region"
            ;;
        digitalocean)
            name="DigitalOcean"
            desc="DigitalOcean IP ranges by region"
            ;;
        starlink)
            name="Starlink"
            desc="Starlink satellite internet IP ranges"
            ;;
        vultr)
            name="Vultr"
            desc="Vultr cloud computing IP ranges"
            ;;
        zscaler)
            name="Zscaler"
            desc="Zscaler security cloud IP ranges"
            ;;
        ibm_cloud)
            name="IBM Cloud"
            desc="IBM Cloud infrastructure IP ranges"
            ;;
        exoscale)
            name="Exoscale"
            desc="Exoscale European cloud IP ranges"
            ;;
        googlebot)
            name="Googlebot"
            desc="Google crawler IP ranges"
            ;;
        *)
            # Fallback: capitalize provider_id
            name=$(echo "$provider_id" | sed 's/_/ /g' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')
            desc="${name} IP ranges"
            ;;
    esac

    echo "${name}|${desc}"
}

echo "Generating providers table for README..."

# Check if cloud_ips directory exists
if [ ! -d "cloud_ips" ]; then
    echo "Error: cloud_ips directory not found"
    exit 1
fi

# Generate table content
table_content="\n"
table_content+="| Provider | Description | Data |\n"
table_content+="|----------|-------------|------|\n"

# Get list of providers from cloud_ips directory
provider_count=0
for provider in $(ls -1 cloud_ips/ | sort); do
    # Skip if not a directory
    if [ ! -d "cloud_ips/$provider" ]; then
        continue
    fi

    # Get provider info
    info=$(get_provider_info "$provider")
    name=$(echo "$info" | cut -d'|' -f1)
    desc=$(echo "$info" | cut -d'|' -f2)

    # Generate row
    table_content+="| **${name}** | ${desc} | [View](cloud_ips/${provider}/) |\n"
    provider_count=$((provider_count + 1))
done

# Create new README content
{
    # Part 1: Everything before the section (including the header)
    sed -n '1,/^## Supported cloud providers$/p' README.md

    # Part 2: New table
    echo ""
    echo -e "$table_content"

    # Part 3: Everything after the table (skip old table content until next ## or EOF)
    sed -n '/^## Supported cloud providers$/,$ {
        /^## Supported cloud providers$/d
        /^$/d
        /^|/d
        /^##/,$p
    }' README.md
} > README.md.tmp

# Replace original README
mv README.md.tmp README.md

echo "README.md updated successfully with $provider_count providers"
