# Troubleshooting Guide

Common issues and solutions for the LibreLinkUp Database Service.

## Cloud Build Permission Errors

### Error: `PERMISSION_DENIED: The caller does not have permission`

**Problem**: Your Google Cloud account doesn't have the necessary permissions to use Cloud Build.

**Solutions**:

#### Option 1: Grant Required IAM Roles (Recommended)

The account needs the **Cloud Build Editor** or **Cloud Build Service Account** role:

```bash
# Get your project ID
source .env
echo "Project: $PROJECT_ID"

# Grant Cloud Build Editor role to your account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$(gcloud config get-value account)" \
    --role="roles/cloudbuild.builds.editor"

# Also grant Service Account User role (needed to use service accounts)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$(gcloud config get-value account)" \
    --role="roles/iam.serviceAccountUser"
```

**Alternative**: Use the **Owner** or **Editor** role (has all permissions):
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$(gcloud config get-value account)" \
    --role="roles/owner"
```

#### Option 2: Use Service Account (For CI/CD)

If you're setting up automated deployments, create a service account:

```bash
# Create service account
gcloud iam service-accounts create cloud-build-sa \
    --display-name="Cloud Build Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-build-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudbuild.builds.editor"

# Create and download key
gcloud iam service-accounts keys create ~/cloud-build-key.json \
    --iam-account=cloud-build-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Use the key
gcloud auth activate-service-account --key-file=~/cloud-build-key.json
```

#### Option 3: Enable Required APIs

Make sure Cloud Build API is enabled:

```bash
gcloud services enable cloudbuild.googleapis.com
```

#### Option 4: Check Project Billing

Cloud Build requires billing to be enabled:

```bash
# Check billing status
gcloud billing projects describe $PROJECT_ID

# If not linked, link a billing account
gcloud billing projects link $PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
```

### Verify Permissions

After granting permissions, verify:

```bash
# Check your current permissions
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:user:$(gcloud config get-value account)"
```

## Common Issues

### 1. "Project not found" or "Project does not exist"

**Solution**:
```bash
# List available projects
gcloud projects list

# Set the correct project
gcloud config set project YOUR_PROJECT_ID

# Or update .env file
# PROJECT_ID=your-actual-project-id
```

### 2. "API not enabled"

**Solution**:
```bash
source .env

# Enable all required APIs
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com \
    compute.googleapis.com
```

### 3. "Service account does not have access to secret"

**Solution**:
```bash
source .env
export SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

# Grant secret accessor role
gcloud secrets add-iam-policy-binding $SECRET_LIBRE_PASSWORD \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding $SECRET_DB_PASSWORD \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

### 4. "VPC connector not found"

**Solution**:
```bash
source .env

# Create VPC connector
gcloud compute networks vpc-access connectors create $VPC_CONNECTOR_NAME \
    --region=$REGION \
    --subnet=default \
    --subnet-project=$PROJECT_ID \
    --min-instances=2 \
    --max-instances=3
```

### 5. "Cloud SQL instance connection failed"

**Solutions**:

**Check instance exists**:
```bash
gcloud sql instances list
```

**Verify connection name format**:
```bash
# Should be: PROJECT_ID:REGION:INSTANCE_NAME
echo "${PROJECT_ID}:${REGION}:${INSTANCE_NAME}"
```

**Check VPC connector**:
```bash
gcloud compute networks vpc-access connectors list --region=$REGION
```

**Verify private IP is enabled**:
```bash
gcloud sql instances describe $INSTANCE_NAME --format="value(ipAddresses)"
```

### 6. "Docker build fails"

**Common causes**:
- Missing files in Docker context
- Syntax errors in Dockerfile
- Network issues

**Solution**:
```bash
# Build locally first to see detailed errors
docker build -t test-image .

# Check .dockerignore isn't excluding needed files
cat .dockerignore
```

### 7. "Sync job not running"

**Check scheduler**:
```bash
# List scheduler jobs
gcloud scheduler jobs list --location=$REGION

# Check job status
gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$REGION

# Manually trigger
gcloud scheduler jobs run $SCHEDULER_JOB_NAME --location=$REGION
```

**Check job executions**:
```bash
gcloud run jobs executions list --job=$SYNC_JOB_NAME --region=$REGION
```

### 8. "API returns 404 or not accessible"

**Check service status**:
```bash
gcloud run services list --region=$REGION

# Get service URL
gcloud run services describe $API_SERVICE_NAME \
    --region=$REGION \
    --format="value(status.url)"
```

**Check authentication**:
```bash
# If service requires authentication
gcloud run services add-iam-policy-binding $API_SERVICE_NAME \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/run.invoker"
```

## Debugging Commands

### Check Current Configuration
```bash
./deploy.sh config
```

### View Logs
```bash
# API service logs
gcloud run services logs read $API_SERVICE_NAME --region=$REGION

# Sync job logs
gcloud run jobs executions logs read EXECUTION_NAME \
    --job=$SYNC_JOB_NAME \
    --region=$REGION

# Cloud Build logs
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

### Verify Environment Variables
```bash
source .env
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Instance: $INSTANCE_NAME"
echo "Connection: ${PROJECT_ID}:${REGION}:${INSTANCE_NAME}"
```

### Test Database Connection
```bash
# From Cloud Run (if you have shell access)
# Or use Cloud SQL Proxy locally
cloud_sql_proxy -instances=${PROJECT_ID}:${REGION}:${INSTANCE_NAME}=tcp:5432

# Then test connection
psql -h 127.0.0.1 -U $DB_USER -d $DB_NAME
```

## Getting Help

1. **Check logs first**: Most issues show up in logs
2. **Verify permissions**: Use `gcloud projects get-iam-policy`
3. **Test locally**: Use docker-compose to isolate cloud issues
4. **Check documentation**: See `docs/DEPLOYMENT.md` for step-by-step guide

## Quick Fix Checklist

- [ ] Project ID is correct in `.env`
- [ ] Billing is enabled for the project
- [ ] Required APIs are enabled
- [ ] Account has necessary IAM roles
- [ ] Service account has secret access
- [ ] VPC connector exists and is active
- [ ] Cloud SQL instance is running
- [ ] Connection name format is correct

