# Deployment Guide: LibreLinkUp Database Service to Google Cloud Run

This guide walks you through deploying the LibreLinkUp Database Service to Google Cloud Run with Cloud SQL PostgreSQL.

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Docker** installed locally (for building images)
4. **LibreLinkUp credentials** (username and password)

## Architecture Overview

- **Cloud Run Service (API)**: Long-running service that handles REST API requests
- **Cloud Run Job (Sync)**: Scheduled job that fetches data from LibreLinkUp API
- **Cloud SQL PostgreSQL**: Managed PostgreSQL database
- **Cloud Scheduler**: Triggers sync job every 15 minutes
- **Secret Manager**: Stores sensitive credentials

## Step 0: Configuration Setup

### 0.1 Create .env File

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
# At minimum, set:
# - PROJECT_ID
# - REGION
# - INSTANCE_NAME
# - DB_NAME
# - DB_USER
```

The `.env` file stores all deployment configuration constants. **Never commit this file to version control** (it's already in `.gitignore`).

### 0.2 Load Configuration

```bash
# Source the .env file to load variables
source .env

# Or use the deployment script (recommended)
./deploy.sh config  # Shows current configuration
```

## Step 1: Set Up Cloud SQL PostgreSQL

### 1.1 Create Cloud SQL Instance

```bash
# Load configuration from .env
source .env

# Or use the deployment script
./deploy.sh config  # Verify configuration

# Set the project
gcloud config set project $PROJECT_ID

# Create Cloud SQL instance
gcloud sql instances create $INSTANCE_NAME \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --root-password=$DB_PASSWORD \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup-start-time=03:00 \
    --enable-bin-log
```

### 1.2 Create Database and User

```bash
# Create database
gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME

# Create user (if not using default postgres user)
gcloud sql users create $DB_USER \
    --instance=$INSTANCE_NAME \
    --password=$DB_PASSWORD
```

### 1.3 Get Connection Name

```bash
# Get the connection name (format: PROJECT_ID:REGION:INSTANCE_NAME)
gcloud sql instances describe $INSTANCE_NAME --format="value(connectionName)"
```

Save this connection name - you'll need it for Cloud Run configuration.

## Step 2: Set Up Secret Manager

### 2.1 Create Secrets

```bash
# Create secret for LibreLinkUp password
echo -n "your-libre-password" | gcloud secrets create libre-password \
    --data-file=- \
    --replication-policy="automatic"

# Create secret for database password
echo -n "$DB_PASSWORD" | gcloud secrets create db-password \
    --data-file=- \
    --replication-policy="automatic"
```

### 2.2 Grant Access to Secrets

```bash
# Get the default Cloud Run service account
export SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

# Grant secret accessor role
gcloud secrets add-iam-policy-binding libre-password \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding db-password \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

## Step 3: Set Up VPC Connector (for Private IP)

If you want to use private IP for Cloud SQL (recommended), create a VPC connector:

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create librelinkup-connector \
    --region=$REGION \
    --subnet=default \
    --subnet-project=$PROJECT_ID \
    --min-instances=2 \
    --max-instances=3
```

## Step 4: Build and Push Docker Image

### 4.1 Enable Required APIs

```bash
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com
```

### 4.2 Build and Push Image

```bash
# Set variables
export IMAGE_NAME="gcr.io/${PROJECT_ID}/librelinkup-service"
export CONNECTION_NAME="${PROJECT_ID}:${REGION}:${INSTANCE_NAME}"

# Build and push using Cloud Build
gcloud builds submit --tag $IMAGE_NAME
```

Or build locally and push:

```bash
# Build locally
docker build -t $IMAGE_NAME .

# Push to GCR
docker push $IMAGE_NAME
```

## Step 5: Deploy Cloud Run Service (API)

### 5.1 Deploy API Service

```bash
gcloud run deploy librelinkup-api \
    --image=$IMAGE_NAME \
    --platform=managed \
    --region=$REGION \
    --allow-unauthenticated \
    --port=8080 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300 \
    --set-env-vars="LIBRE_USERNAME=your-libre-username,DB_HOST=${CONNECTION_NAME},DB_NAME=${DB_NAME},DB_USER=${DB_USER},LIBRE_CLIENT_VERSION=4.16.0" \
    --set-secrets="LIBRE_PASSWORD=libre-password:latest,DB_PASSWORD=db-password:latest" \
    --add-cloudsql-instances=$CONNECTION_NAME \
    --vpc-connector=librelinkup-connector \
    --vpc-egress=private-ranges-only
```

**Note:** Replace `your-libre-username` with your actual LibreLinkUp email.

### 5.2 Get Service URL

```bash
# Get the service URL
gcloud run services describe librelinkup-api \
    --region=$REGION \
    --format="value(status.url)"
```

Save this URL - you'll use it for Google Sheets/Looker Studio.

## Step 6: Deploy Cloud Run Job (Sync)

### 6.1 Deploy Sync Job

```bash
gcloud run jobs create librelinkup-sync \
    --image=$IMAGE_NAME \
    --region=$REGION \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300 \
    --set-env-vars="LIBRE_USERNAME=your-libre-username,DB_HOST=${CONNECTION_NAME},DB_NAME=${DB_NAME},DB_USER=${DB_USER},LIBRE_CLIENT_VERSION=4.16.0" \
    --set-secrets="LIBRE_PASSWORD=libre-password:latest,DB_PASSWORD=db-password:latest" \
    --set-args="sync" \
    --add-cloudsql-instances=$CONNECTION_NAME \
    --vpc-connector=librelinkup-connector \
    --vpc-egress=private-ranges-only
```

### 6.2 Test Sync Job Manually

```bash
# Execute the job manually to test
gcloud run jobs execute librelinkup-sync --region=$REGION
```

## Step 7: Set Up Cloud Scheduler

### 7.1 Create Scheduler Job

```bash
# Create scheduler job to run every 15 minutes
gcloud scheduler jobs create http librelinkup-sync-schedule \
    --location=$REGION \
    --schedule="*/15 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/librelinkup-sync:run" \
    --http-method=POST \
    --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --time-zone="UTC"
```

**Alternative (simpler) approach using Cloud Run Jobs API:**

```bash
# Get the job name
export JOB_NAME="librelinkup-sync"

# Create scheduler job
gcloud scheduler jobs create http librelinkup-sync-schedule \
    --location=$REGION \
    --schedule="*/15 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --time-zone="UTC"
```

### 7.2 Test Scheduler

```bash
# Manually trigger the scheduler job
gcloud scheduler jobs run librelinkup-sync-schedule --location=$REGION
```

## Step 8: Verify Deployment

### 8.1 Test API Endpoints

```bash
# Get service URL
export API_URL=$(gcloud run services describe librelinkup-api \
    --region=$REGION \
    --format="value(status.url)")

# Test health endpoint
curl ${API_URL}/health

# Test latest reading
curl ${API_URL}/api/readings/latest

# Test readings list
curl "${API_URL}/api/readings?limit=10"
```

### 8.2 Check Logs

```bash
# View API service logs
gcloud run services logs read librelinkup-api --region=$REGION

# View sync job logs
gcloud run jobs executions list --job=librelinkup-sync --region=$REGION
```

## Step 9: Initialize Database Schema

The database schema is automatically created on first API request or sync. However, you can manually trigger it:

```bash
# Trigger a sync to initialize the database
gcloud run jobs execute librelinkup-sync --region=$REGION
```

## Troubleshooting

### Common Issues

1. **Connection refused to Cloud SQL**
   - Verify VPC connector is created and working
   - Check that Cloud SQL instance has private IP enabled
   - Ensure Cloud Run service has `--add-cloudsql-instances` flag

2. **Secret access denied**
   - Verify service account has `secretmanager.secretAccessor` role
   - Check secret names match exactly

3. **Database connection timeout**
   - Verify connection name format: `PROJECT_ID:REGION:INSTANCE_NAME`
   - Check VPC connector is in the same region as Cloud Run

### View Logs

```bash
# API service logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=librelinkup-api" --limit=50

# Sync job logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=librelinkup-sync" --limit=50
```

## Cost Estimation

- **Cloud SQL (db-f1-micro)**: ~$7-10/month
- **Cloud Run (API)**: Pay per request, ~$0-5/month for low traffic
- **Cloud Run (Sync Job)**: ~$0.10-0.50/month (runs 96 times/day)
- **Cloud Scheduler**: Free tier covers this usage
- **Secret Manager**: Free tier covers this usage
- **VPC Connector**: ~$10-15/month (min 2 instances)

**Total estimated cost: ~$20-30/month**

## Next Steps

- Set up authentication for the API (if needed)
- Configure custom domain
- Set up monitoring and alerts
- See [GOOGLE_SHEETS_INTEGRATION.md](./GOOGLE_SHEETS_INTEGRATION.md) for connecting Google Sheets/Looker Studio


