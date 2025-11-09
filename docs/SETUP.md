# Google Cloud Setup Guide

This guide covers the complete setup process for deploying the LibreLinkUp Database Service to Google Cloud Platform.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated
- Docker installed (for local testing)
- LibreLinkUp account credentials

## Step 1: Enable Required APIs

Enable all necessary Google Cloud APIs:

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable APIs
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    vpcaccess.googleapis.com \
    servicenetworking.googleapis.com \
    cloudscheduler.googleapis.com
```

## Step 2: Configure Deployment Settings

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```bash
# Required: Project and region
PROJECT_ID=your-project-id
REGION=us-central1

# Required: Database configuration
INSTANCE_NAME=librelinkup-db
DB_NAME=librelinkup
DB_USER=librelinkup

# Required: Secret Manager secret names
SECRET_LIBRE_USERNAME=libre-username
SECRET_LIBRE_PASSWORD=libre-password
SECRET_DB_PASSWORD=db-password

# Optional: Service names (defaults shown)
API_SERVICE_NAME=librelinkup-api
SYNC_JOB_NAME=librelinkup-sync
VPC_CONNECTOR_NAME=librelinkup-connector

# Optional: Resource configuration
API_MEMORY=512Mi
API_CPU=1
SYNC_MEMORY=512Mi
SYNC_CPU=1
```

## Step 3: Create Cloud SQL PostgreSQL Instance

```bash
# Load configuration
source .env

# Create Cloud SQL instance
gcloud sql instances create $INSTANCE_NAME \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup-start-time=03:00

# Create database
gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME

# Create database user
gcloud sql users create $DB_USER \
    --instance=$INSTANCE_NAME \
    --password="your-secure-password-here"
```

**Note:** Save the database password - you'll need it for Secret Manager in the next step.

## Step 4: Set Up Secret Manager

### 4.1 Create Secrets

```bash
# Load configuration
source .env

# Create LibreLinkUp username secret
echo -n "your-libre-username@example.com" | \
    gcloud secrets create $SECRET_LIBRE_USERNAME --data-file=-

# Create LibreLinkUp password secret
echo -n "your-libre-password" | \
    gcloud secrets create $SECRET_LIBRE_PASSWORD --data-file=-

# Create database password secret
echo -n "your-db-password" | \
    gcloud secrets create $SECRET_DB_PASSWORD --data-file=-
```

### 4.2 Grant Service Account Access

The Cloud Run service account needs access to secrets:

```bash
# Get the default compute service account
SERVICE_ACCOUNT="${PROJECT_ID}-compute@developer.gserviceaccount.com"

# Grant access to secrets
gcloud secrets add-iam-policy-binding $SECRET_LIBRE_USERNAME \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding $SECRET_LIBRE_PASSWORD \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding $SECRET_DB_PASSWORD \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

## Step 5: Create VPC Connector

The VPC connector allows Cloud Run to connect to Cloud SQL via private IP.

### 5.1 Create Subnet for VPC Connector

```bash
# Create a dedicated subnet with /28 netmask (required for VPC connectors)
gcloud compute networks subnets create vpc-connector-subnet \
    --network=default \
    --range=10.8.0.0/28 \
    --region=$REGION
```

### 5.2 Create VPC Connector

```bash
# Load configuration
source .env

# Create VPC connector
gcloud compute networks vpc-access connectors create $VPC_CONNECTOR_NAME \
    --region=$REGION \
    --subnet=vpc-connector-subnet \
    --subnet-project=$PROJECT_ID \
    --min-instances=2 \
    --max-instances=3 \
    --machine-type=e2-micro
```

## Step 6: Set Up IAM Permissions

Grant necessary permissions to your user account:

```bash
# Get your current account
YOUR_EMAIL=$(gcloud config get-value account)

# Grant Cloud Build permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:${YOUR_EMAIL}" \
    --role="roles/cloudbuild.builds.editor"

# Grant Service Account User role (for Cloud Run)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:${YOUR_EMAIL}" \
    --role="roles/iam.serviceAccountUser"
```

## Step 7: Deploy Services

Use the deployment script to build and deploy:

```bash
# Build Docker image
./deploy.sh build

# Deploy API service
./deploy.sh deploy-api

# Deploy sync job
./deploy.sh deploy-sync

# Or deploy everything at once
./deploy.sh deploy-all
```

## Step 8: Set Up Cloud Scheduler (Optional)

Automatically trigger the sync job on a schedule:

```bash
# Load configuration
source .env

# Get the sync job URL
JOB_URL=$(gcloud run jobs describe $SYNC_JOB_NAME \
    --region=$REGION \
    --format="value(status.url)")

# Create Cloud Scheduler job (runs every 15 minutes)
gcloud scheduler jobs create http librelinkup-sync-scheduler \
    --location=$REGION \
    --schedule="*/15 * * * *" \
    --uri="$JOB_URL" \
    --http-method=POST \
    --oidc-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com"
```

## Step 9: Verify Deployment

### 9.1 Check Service Status

```bash
# Check API service
gcloud run services describe $API_SERVICE_NAME --region=$REGION

# Check sync job
gcloud run jobs describe $SYNC_JOB_NAME --region=$REGION
```

### 9.2 Test API Endpoints

```bash
# Get API URL
API_URL=$(gcloud run services describe $API_SERVICE_NAME \
    --region=$REGION \
    --format="value(status.url)")

# Health check
curl "$API_URL/health"

# Trigger manual sync
curl -X POST "$API_URL/api/sync"

# View sync logs
curl "$API_URL/api/sync-logs?limit=5"

# View sync statistics
curl "$API_URL/api/sync-stats"
```

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   - Ensure all IAM roles are granted (Step 6)
   - Verify service account has Secret Manager access (Step 4.2)

2. **VPC Connector Errors**
   - Ensure subnet has /28 netmask
   - Check that VPC connector is in the same region as Cloud Run

3. **Database Connection Errors**
   - Verify Cloud SQL instance is running
   - Check that Cloud Run has Cloud SQL connection configured
   - Ensure database credentials in Secret Manager are correct

4. **Secret Access Errors**
   - Verify secrets exist: `gcloud secrets list`
   - Check IAM bindings: `gcloud secrets get-iam-policy SECRET_NAME`

For more detailed troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## Next Steps

- Configure monitoring and alerts (see [DEPLOYMENT.md](./DEPLOYMENT.md))
- Set up integration with Google Sheets (see [GOOGLE_SHEETS_INTEGRATION.md](./GOOGLE_SHEETS_INTEGRATION.md))
- Review API documentation and endpoints

## Cost Estimation

Approximate monthly costs (varies by usage):

- **Cloud SQL (db-f1-micro)**: ~$7-10/month
- **Cloud Run (API)**: ~$0-5/month (pay per request)
- **Cloud Run (Sync Job)**: ~$0-2/month (runs every 15 minutes)
- **VPC Connector**: ~$10/month (minimum 2 instances)
- **Cloud Scheduler**: Free tier (3 jobs)
- **Secret Manager**: Free tier (first 6 secrets)

**Total**: ~$17-27/month for minimal usage

