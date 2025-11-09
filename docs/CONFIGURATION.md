# Configuration Management Guide

This guide explains how to manage configuration for the LibreLinkUp Database Service.

## Configuration Strategy

We use a **two-tier configuration approach**:

1. **`.env` file** - For deployment constants (PROJECT_ID, REGION, etc.)
2. **Environment variables** - For runtime configuration (credentials, database connection)
3. **Secret Manager** - For sensitive secrets (passwords)

## Configuration Files

### `.env` File (Deployment Constants)

**Purpose**: Store deployment configuration constants that don't change between deployments.

**Location**: Root directory (`.env`)

**Contents**:
- Google Cloud project settings (PROJECT_ID, REGION)
- Resource names (INSTANCE_NAME, SERVICE_NAME)
- Cloud SQL configuration
- Cloud Run resource settings
- Scheduler configuration

**Security**: Contains no secrets, but should not be committed to version control.

**Example**:
```bash
PROJECT_ID=my-project-id
REGION=us-central1
INSTANCE_NAME=librelinkup-db
DB_NAME=librelinkup
```

### `config.yaml` (Local Development)

**Purpose**: Store application configuration for local development.

**Location**: Root directory (`config.yaml`)

**Contents**:
- LibreLinkUp credentials (for local testing)
- Local database connection settings
- Service configuration

**Security**: Contains credentials - **never commit to version control**.

**Example**:
```yaml
libre_link_up:
  username: "your-email@example.com"
  password: "your-password"
database:
  host: "localhost"
  port: 5432
  name: "librelinkup"
```

## Configuration Priority

The application loads configuration in this order (highest priority first):

1. **Environment variables** (Cloud Run, docker-compose)
2. **config.yaml file** (local development fallback)

### For Application Config (Runtime)

```python
# Priority: Environment variables > config.yaml
LIBRE_USERNAME=email@example.com  # From env
# Falls back to config.yaml if not in env
```

### For Deployment Config (Build/Deploy Time)

```bash
# Load from .env file
source .env
# Or use deployment script
./deploy.sh config
```

## Setting Up Configuration

### 1. Create .env File

```bash
# Copy example
cp .env.example .env

# Edit with your values
nano .env  # or your preferred editor
```

### 2. Required Variables

**Minimum required for deployment:**

```bash
PROJECT_ID=your-project-id
REGION=us-central1
INSTANCE_NAME=librelinkup-db
DB_NAME=librelinkup
DB_USER=librelinkup
```

### 3. Optional Variables

All other variables have sensible defaults. See `.env.example` for full list.

## Using Configuration

### Local Development

**Option 1: Use config.yaml**
```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your credentials
docker-compose up
```

**Option 2: Use environment variables**
```bash
export LIBRE_USERNAME="your-email@example.com"
export LIBRE_PASSWORD="your-password"
export DB_HOST="localhost"
export DB_NAME="librelinkup"
docker-compose up
```

**Option 3: Use .env with docker-compose**
```bash
# docker-compose automatically loads .env file
# But you need to set application config separately
docker-compose up
```

### Cloud Deployment

**Step 1: Set up .env file**
```bash
cp .env.example .env
# Edit .env with your project details
```

**Step 2: Create secrets in Secret Manager**
```bash
source .env  # Load variables

# Create secrets (passwords)
echo -n "your-libre-password" | gcloud secrets create $SECRET_LIBRE_PASSWORD
echo -n "your-db-password" | gcloud secrets create $SECRET_DB_PASSWORD
```

**Step 3: Deploy using script**
```bash
./deploy.sh deploy-all
```

Or manually:
```bash
source .env
# Use variables in gcloud commands
gcloud run deploy $API_SERVICE_NAME --image=$IMAGE_NAME ...
```

## Configuration Variables Reference

### Deployment Variables (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ID` | GCP project ID | `my-project` |
| `REGION` | GCP region | `us-central1` |
| `INSTANCE_NAME` | Cloud SQL instance name | `librelinkup-db` |
| `DB_NAME` | Database name | `librelinkup` |
| `DB_USER` | Database user | `librelinkup` |
| `API_SERVICE_NAME` | Cloud Run service name | `librelinkup-api` |
| `SYNC_JOB_NAME` | Cloud Run job name | `librelinkup-sync` |
| `VPC_CONNECTOR_NAME` | VPC connector name | `librelinkup-connector` |

### Runtime Variables (Environment/Secret Manager)

| Variable | Description | Source |
|----------|-------------|--------|
| `LIBRE_USERNAME` | LibreLinkUp email | Env var or config.yaml |
| `LIBRE_PASSWORD` | LibreLinkUp password | Secret Manager |
| `DB_HOST` | Database host | Env var (Cloud SQL connection name) |
| `DB_NAME` | Database name | Env var |
| `DB_USER` | Database user | Env var |
| `DB_PASSWORD` | Database password | Secret Manager |

## Best Practices

### ✅ Do

- Use `.env` for deployment constants
- Use Secret Manager for passwords
- Keep `.env.example` in version control
- Document all configuration options
- Use the deployment script (`deploy.sh`)

### ❌ Don't

- Commit `.env` to version control
- Commit `config.yaml` to version control
- Put secrets in `.env` file
- Hardcode configuration values
- Share `.env` files with others

## Deployment Script

The `deploy.sh` script automatically loads `.env` and provides helper commands:

```bash
# Show current configuration
./deploy.sh config

# Build Docker image
./deploy.sh build

# Deploy API service
./deploy.sh deploy-api

# Deploy sync job
./deploy.sh deploy-sync

# Deploy everything
./deploy.sh deploy-all
```

## Troubleshooting

### "Variable not set" errors

```bash
# Make sure .env file exists
ls -la .env

# Load variables
source .env

# Verify variables are set
echo $PROJECT_ID
```

### Configuration not loading

```bash
# Check .env file syntax (no spaces around =)
PROJECT_ID=value  # ✅ Correct
PROJECT_ID = value  # ❌ Wrong

# Check for comments (lines starting with # are ignored)
# PROJECT_ID=old-value  # This is ignored
```

### Secrets not found

```bash
# Verify secrets exist
gcloud secrets list

# Check secret names match .env
echo $SECRET_LIBRE_PASSWORD
gcloud secrets describe $SECRET_LIBRE_PASSWORD
```

## Migration from Manual Configuration

If you've been using manual `export` commands:

1. **Create .env file** from your current exports
2. **Replace export commands** with `source .env`
3. **Use deployment script** instead of manual gcloud commands

**Before:**
```bash
export PROJECT_ID="my-project"
export REGION="us-central1"
gcloud run deploy librelinkup-api ...
```

**After:**
```bash
source .env  # or use deploy.sh
./deploy.sh deploy-api
```

## See Also

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Complete deployment guide
- [QUICK_START.md](./QUICK_START.md) - Quick setup guide
- `.env.example` - Example configuration file

