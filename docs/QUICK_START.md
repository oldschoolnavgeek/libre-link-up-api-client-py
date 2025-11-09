# Quick Start Guide

## Local Testing (5 minutes)

### 1. Set Up Configuration

```bash
cd libre-link-up-api-client-py
cp config.yaml.example config.yaml
# Edit config.yaml with your LibreLinkUp credentials
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Test API

```bash
# Health check
curl http://localhost:8080/health

# Latest reading (after sync)
curl http://localhost:8080/api/readings/latest

# List readings
curl "http://localhost:8080/api/readings?limit=10"
```

### 4. Run Sync

```bash
# Manual sync
docker-compose run sync

# Or trigger via API
curl -X POST http://localhost:8080/api/sync
```

### 5. View Logs

```bash
docker-compose logs -f api
```

## Cloud Deployment (30 minutes)

### Prerequisites

```bash
# Install gcloud CLI and authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Quick Deploy Script

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export INSTANCE_NAME="librelinkup-db"

# Run deployment (see DEPLOYMENT.md for details)
# 1. Create Cloud SQL
# 2. Create secrets
# 3. Build and deploy
# 4. Set up scheduler
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete instructions.

## Common Commands

### Local Development

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Run sync manually
docker-compose run sync

# Rebuild containers
docker-compose build
```

### Cloud Run

```bash
# Deploy API service
gcloud run deploy librelinkup-api --source .

# Deploy sync job
gcloud run jobs create librelinkup-sync --source .

# Execute sync manually
gcloud run jobs execute librelinkup-sync

# View logs
gcloud run services logs read librelinkup-api
```

## API Examples

### Get Latest Reading

```bash
curl https://your-api.run.app/api/readings/latest
```

### Get Readings for Date Range

```bash
curl "https://your-api.run.app/api/readings?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59&limit=100"
```

### Get Statistics

```bash
curl "https://your-api.run.app/api/readings/stats?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59"
```

### Trigger Sync

```bash
curl -X POST https://your-api.run.app/api/sync
```

## Next Steps

1. ✅ Test locally with Docker Compose
2. ✅ Deploy to Cloud Run (see [DEPLOYMENT.md](./DEPLOYMENT.md))
3. ✅ Set up Cloud Scheduler
4. ✅ Connect Google Sheets (see [GOOGLE_SHEETS_INTEGRATION.md](./GOOGLE_SHEETS_INTEGRATION.md))
5. ✅ Set up Looker Studio dashboard

## Troubleshooting

### "Connection refused" errors
- Check database is running: `docker-compose ps`
- Verify database credentials in config.yaml
- Check database logs: `docker-compose logs postgres`

### "Bad credentials" error
- Verify LibreLinkUp username/password
- Make sure you're using LibreLinkUp (not LibreLink) credentials
- Check credentials in config.yaml or environment variables

### API returns empty results
- Run sync first: `docker-compose run sync`
- Check sync logs for errors
- Verify database has data: `docker-compose exec postgres psql -U postgres -d librelinkup -c "SELECT COUNT(*) FROM readings;"`

