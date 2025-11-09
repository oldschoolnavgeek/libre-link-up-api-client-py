#!/bin/bash
# Deployment script for LibreLinkUp Database Service
# This script sources .env file and provides helper functions for deployment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables from .env file
if [ -f .env ]; then
    echo -e "${GREEN}Loading configuration from .env file...${NC}"
    # Read .env file line by line and export variables
    # This handles special characters like * in cron schedules
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines and comments
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        # Skip lines that don't look like variable assignments (no = sign)
        [[ ! "$line" =~ = ]] && continue
        # Export the variable (only if it's a valid assignment)
        if [[ "$line" =~ ^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*= ]]; then
            export "$line" 2>/dev/null || true
        fi
    done < .env
else
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.example to .env and fill in your values."
    exit 1
fi

# Validate required variables
required_vars=("PROJECT_ID" "REGION" "INSTANCE_NAME" "DB_NAME" "DB_USER" "SECRET_LIBRE_USERNAME" "SECRET_LIBRE_PASSWORD" "SECRET_DB_PASSWORD")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing required variables in .env:${NC}"
    printf '%s\n' "${missing_vars[@]}"
    exit 1
fi

# Set derived variables
export CONNECTION_NAME="${PROJECT_ID}:${REGION}:${INSTANCE_NAME}"
export IMAGE_NAME="gcr.io/${PROJECT_ID}/librelinkup-service"

# Helper function to print configuration
print_config() {
    echo -e "${YELLOW}Current Configuration:${NC}"
    echo "  PROJECT_ID: ${PROJECT_ID}"
    echo "  REGION: ${REGION}"
    echo "  INSTANCE_NAME: ${INSTANCE_NAME}"
    echo "  CONNECTION_NAME: ${CONNECTION_NAME}"
    echo "  DB_NAME: ${DB_NAME}"
    echo "  DB_USER: ${DB_USER}"
    echo "  API_SERVICE_NAME: ${API_SERVICE_NAME:-librelinkup-api}"
    echo "  SYNC_JOB_NAME: ${SYNC_JOB_NAME:-librelinkup-sync}"
    echo "  IMAGE_NAME: ${IMAGE_NAME}"
    echo ""
}

# Set gcloud project (only if gcloud is available and authenticated)
set_gcloud_project() {
    if command -v gcloud &> /dev/null; then
        echo -e "${GREEN}Setting gcloud project to ${PROJECT_ID}...${NC}"
        gcloud config set project "${PROJECT_ID}" 2>/dev/null || {
            echo -e "${YELLOW}Warning: Could not set gcloud project. You may need to run 'gcloud auth login'${NC}"
        }
    fi
}

# Main menu
case "${1:-}" in
    config)
        print_config
        set_gcloud_project
        ;;
    build)
        set_gcloud_project
        echo -e "${GREEN}Building and pushing Docker image...${NC}"
        gcloud builds submit --tag "${IMAGE_NAME}"
        ;;
    deploy-api)
        set_gcloud_project
        echo -e "${GREEN}Deploying API service...${NC}"
        print_config
        gcloud run deploy "${API_SERVICE_NAME:-librelinkup-api}" \
            --image="${IMAGE_NAME}" \
            --platform=managed \
            --region="${REGION}" \
            --allow-unauthenticated \
            --port=8080 \
            --memory="${API_MEMORY:-512Mi}" \
            --cpu="${API_CPU:-1}" \
            --min-instances="${API_MIN_INSTANCES:-0}" \
            --max-instances="${API_MAX_INSTANCES:-10}" \
            --timeout="${API_TIMEOUT:-300}" \
            --set-env-vars="DB_HOST=${CONNECTION_NAME},DB_NAME=${DB_NAME},DB_USER=${DB_USER},LIBRE_CLIENT_VERSION=${LIBRE_CLIENT_VERSION:-4.16.0}" \
            --set-secrets="LIBRE_USERNAME=${SECRET_LIBRE_USERNAME}:latest,LIBRE_PASSWORD=${SECRET_LIBRE_PASSWORD}:latest,DB_PASSWORD=${SECRET_DB_PASSWORD}:latest" \
            --add-cloudsql-instances="${CONNECTION_NAME}" \
            --vpc-connector="${VPC_CONNECTOR_NAME}" \
            --vpc-egress=private-ranges-only
        ;;
    deploy-sync)
        set_gcloud_project
        echo -e "${GREEN}Deploying sync job...${NC}"
        print_config
        gcloud run jobs create "${SYNC_JOB_NAME:-librelinkup-sync}" \
            --image="${IMAGE_NAME}" \
            --region="${REGION}" \
            --memory="${SYNC_MEMORY:-512Mi}" \
            --cpu="${SYNC_CPU:-1}" \
            --task-timeout="${SYNC_TIMEOUT:-300}" \
            --set-env-vars="DB_HOST=${CONNECTION_NAME},DB_NAME=${DB_NAME},DB_USER=${DB_USER},LIBRE_CLIENT_VERSION=${LIBRE_CLIENT_VERSION:-4.16.0}" \
            --set-secrets="LIBRE_USERNAME=${SECRET_LIBRE_USERNAME}:latest,LIBRE_PASSWORD=${SECRET_LIBRE_PASSWORD}:latest,DB_PASSWORD=${SECRET_DB_PASSWORD}:latest" \
            --args="sync" \
            --set-cloudsql-instances="${CONNECTION_NAME}" \
            --vpc-connector="${VPC_CONNECTOR_NAME}" \
            --vpc-egress=private-ranges-only
        ;;
    deploy-all)
        echo -e "${GREEN}Deploying all services...${NC}"
        $0 build
        $0 deploy-api
        $0 deploy-sync
        ;;
    *)
        echo "Usage: $0 {config|build|deploy-api|deploy-sync|deploy-all}"
        echo ""
        echo "Commands:"
        echo "  config       - Show current configuration"
        echo "  build        - Build and push Docker image"
        echo "  deploy-api   - Deploy API service to Cloud Run"
        echo "  deploy-sync  - Deploy sync job to Cloud Run"
        echo "  deploy-all   - Build and deploy all services"
        echo ""
        echo "Make sure you have:"
        echo "  1. Created .env file from .env.example"
        echo "  2. Set up Cloud SQL instance"
        echo "  3. Created secrets in Secret Manager"
        echo "  4. Created VPC connector"
        exit 1
        ;;
esac

