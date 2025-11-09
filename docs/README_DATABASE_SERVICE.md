# LibreLinkUp Database Service

A production-ready service that periodically fetches glucose readings from LibreLinkUp API and stores them in a PostgreSQL database, with a REST API for accessing the data.

## Features

- 🔄 **Automatic Sync**: Periodically fetches readings from LibreLinkUp API
- 💾 **PostgreSQL Storage**: Stores readings in a managed database
- 🔍 **Deduplication**: Prevents duplicate readings automatically
- 🌐 **REST API**: FastAPI-based REST API for querying data
- ☁️ **Cloud Ready**: Designed for Google Cloud Run deployment
- 📊 **External Access**: Easy integration with Google Sheets and Looker Studio

## Architecture

```
┌─────────────────┐
│  LibreLinkUp    │
│      API        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  Sync Service   │─────▶│  PostgreSQL  │
│ (Cloud Run Job) │      │  (Cloud SQL) │
└─────────────────┘      └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  REST API    │
                         │ (Cloud Run)  │
                         └──────┬───────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
         Google Sheets   Looker Studio    Other Tools
```

## Quick Start

### Local Development

1. **Prerequisites:**
   ```bash
   # Install Docker and Docker Compose
   docker --version
   docker-compose --version
   ```

2. **Configure:**
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your LibreLinkUp credentials
   ```

3. **Start Services:**
   ```bash
   docker-compose up
   ```

4. **Access API:**
   - API: http://localhost:8080
   - Health: http://localhost:8080/health
   - Latest: http://localhost:8080/api/readings/latest

5. **Run Sync Manually:**
   ```bash
   docker-compose run sync
   ```

### Production Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed Cloud Run deployment instructions.

## API Endpoints

### Health Check
```
GET /health
```

### Get Latest Reading
```
GET /api/readings/latest
```

### Query Readings
```
GET /api/readings?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59&limit=100&offset=0
```

### Get Statistics
```
GET /api/readings/stats?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59
```

### Manual Sync
```
POST /api/sync
```

## Database Schema

```sql
CREATE TABLE readings (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL UNIQUE,
    value INTEGER NOT NULL,
    trend VARCHAR(20) NOT NULL,
    is_high BOOLEAN NOT NULL,
    is_low BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Configuration

### Environment Variables (Cloud Run)

- `LIBRE_USERNAME` - LibreLinkUp email
- `LIBRE_PASSWORD` - LibreLinkUp password (from Secret Manager)
- `LIBRE_CLIENT_VERSION` - Client version (default: 4.16.0)
- `LIBRE_CONNECTION_IDENTIFIER` - Patient name (optional)
- `DB_HOST` - Database host (Cloud SQL connection name)
- `DB_PORT` - Database port (default: 5432)
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password (from Secret Manager)
- `PORT` - API server port (default: 8080)

### Config File (Local Development)

See `config.yaml.example` for local configuration format.

## Integration

### Google Sheets

See [GOOGLE_SHEETS_INTEGRATION.md](./GOOGLE_SHEETS_INTEGRATION.md) for detailed instructions.

Quick example:
```javascript
// In Google Apps Script
function getLatestReading() {
  const response = UrlFetchApp.fetch('https://your-api.run.app/api/readings/latest');
  const data = JSON.parse(response.getContentText());
  return [data.timestamp, data.value, data.trend];
}
```

### Looker Studio

Use the Apps Script connector (see integration guide) or connect directly to the REST API.

## Project Structure

```
libre-link-up-api-client-py/
├── libre_link_up_client/
│   ├── api.py              # REST API endpoints
│   ├── database.py         # Database operations
│   ├── sync_service.py     # Sync service
│   ├── client.py           # LibreLinkUp API client
│   └── types.py            # Data types
├── service.py              # Main entry point
├── Dockerfile              # Container definition
├── docker-compose.yml      # Local development
├── requirements.txt        # Python dependencies
└── config.yaml.example     # Configuration template
```

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables or use config.yaml
export LIBRE_USERNAME="your-email@example.com"
export LIBRE_PASSWORD="your-password"
export DB_HOST="localhost"
export DB_NAME="librelinkup"
export DB_USER="postgres"
export DB_PASSWORD="postgres"

# Run API server
python service.py

# Or run sync
python service.py sync
```

### Testing

```bash
# Test API endpoints
curl http://localhost:8080/health
curl http://localhost:8080/api/readings/latest
curl "http://localhost:8080/api/readings?limit=10"
```

## Monitoring

### View Logs

**Cloud Run API Service:**
```bash
gcloud run services logs read librelinkup-api --region=us-central1
```

**Cloud Run Sync Job:**
```bash
gcloud run jobs executions list --job=librelinkup-sync --region=us-central1
```

### Health Checks

The `/health` endpoint checks:
- API service status
- Database connectivity

## Troubleshooting

### Database Connection Issues

1. Verify Cloud SQL instance is running
2. Check connection name format: `PROJECT_ID:REGION:INSTANCE_NAME`
3. Verify VPC connector is configured
4. Check service account permissions

### Sync Not Running

1. Verify Cloud Scheduler job is created
2. Check job execution logs
3. Verify LibreLinkUp credentials in Secret Manager
4. Test sync manually: `gcloud run jobs execute librelinkup-sync`

### API Not Accessible

1. Check service is deployed: `gcloud run services list`
2. Verify service URL is correct
3. Check authentication settings
4. View service logs for errors

## Cost Estimation

- **Cloud SQL (db-f1-micro)**: ~$7-10/month
- **Cloud Run (API)**: Pay per request, ~$0-5/month
- **Cloud Run (Sync Job)**: ~$0.10-0.50/month
- **Cloud Scheduler**: Free
- **Secret Manager**: Free tier
- **VPC Connector**: ~$10-15/month

**Total: ~$20-30/month**

## License

MIT License - Same as the original LibreLinkUp API client

## Support

For issues related to:
- **LibreLinkUp API**: Check the original [libre-link-up-api-client](https://github.com/DiaKEM/libre-link-up-api-client)
- **This Service**: Open an issue in this repository
- **Deployment**: See [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Integration**: See [GOOGLE_SHEETS_INTEGRATION.md](./GOOGLE_SHEETS_INTEGRATION.md)

