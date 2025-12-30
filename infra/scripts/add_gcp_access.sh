#!/bin/bash
# Script to add GCS and BigQuery access to team members
# Usage: ./add_gcp_access.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMAILS_FILE="${SCRIPT_DIR}/emails.txt"
PROJECT_ID="${GCP_PROJECT_ID:-job-match-v0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  GCP Access Management - JobMatch"
echo "=========================================="
echo ""
echo "Project ID: ${PROJECT_ID}"
echo "Emails file: ${EMAILS_FILE}"
echo ""

# Check if emails file exists
if [[ ! -f "${EMAILS_FILE}" ]]; then
    echo -e "${RED}Error: ${EMAILS_FILE} not found${NC}"
    echo "Create it with one email per line"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not installed${NC}"
    echo "Install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}Error: Not authenticated to gcloud${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi

# Read emails (skip comments and empty lines)
EMAILS=$(grep -v '^#' "${EMAILS_FILE}" | grep -v '^[[:space:]]*$' || true)

if [[ -z "${EMAILS}" ]]; then
    echo -e "${YELLOW}Warning: No emails found in ${EMAILS_FILE}${NC}"
    echo "Add emails (one per line, lines starting with # are ignored)"
    exit 1
fi

echo "Emails to process:"
echo "${EMAILS}" | while read -r email; do
    echo "  - ${email}"
done
echo ""

# Confirm
read -p "Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""

# Process each email
echo "${EMAILS}" | while read -r email; do
    if [[ -z "${email}" ]]; then
        continue
    fi

    echo -e "${YELLOW}Processing: ${email}${NC}"

    # BigQuery Data Editor
    echo "  Adding roles/bigquery.dataEditor..."
    if gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="user:${email}" \
        --role="roles/bigquery.dataEditor" \
        --quiet > /dev/null 2>&1; then
        echo -e "  ${GREEN}OK${NC} bigquery.dataEditor"
    else
        echo -e "  ${RED}FAILED${NC} bigquery.dataEditor"
    fi

    # BigQuery Job User (to run queries)
    echo "  Adding roles/bigquery.jobUser..."
    if gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="user:${email}" \
        --role="roles/bigquery.jobUser" \
        --quiet > /dev/null 2>&1; then
        echo -e "  ${GREEN}OK${NC} bigquery.jobUser"
    else
        echo -e "  ${RED}FAILED${NC} bigquery.jobUser"
    fi

    # GCS Object Admin
    echo "  Adding roles/storage.objectAdmin..."
    if gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="user:${email}" \
        --role="roles/storage.objectAdmin" \
        --quiet > /dev/null 2>&1; then
        echo -e "  ${GREEN}OK${NC} storage.objectAdmin"
    else
        echo -e "  ${RED}FAILED${NC} storage.objectAdmin"
    fi

    echo ""
done

echo -e "${GREEN}Done!${NC}"
echo ""
echo "Roles granted:"
echo "  - bigquery.dataEditor  : Read/write BigQuery tables"
echo "  - bigquery.jobUser     : Execute BigQuery queries"
echo "  - storage.objectAdmin  : Read/write/delete GCS objects"
