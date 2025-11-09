# LibreLinkUp API Client & Database Service

This repository contains two components:

1. **LibreLinkUp API Client** - A Python client library for accessing Abbott's LibreLinkUp sharing service (can be used standalone)
2. **Database Service** - A production-ready service for automatically syncing LibreLinkUp CGM data to PostgreSQL with a REST API

## Standalone Client Usage

The LibreLinkUp API client can be used independently without deploying the database service:

```bash
# Install the package
pip install -e .

# Run example
python example_usage.py
```

See [example_usage.py](example_usage.py) for a complete standalone usage example.

## Database Service Features

- 🔄 **Automated Sync**: Regularly fetches glucose readings from LibreLinkUp API
- 🗄️ **PostgreSQL Storage**: Stores readings with deduplication and indexing
- 🌐 **REST API**: FastAPI-based API for querying glucose data
- 📊 **Observability**: Built-in sync logging and statistics
- ☁️ **Cloud Ready**: Deployed on Google Cloud Run with Cloud SQL
- 🐳 **Docker Support**: Containerized for easy deployment

## Quick Start

### Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure:**
```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your LibreLinkUp credentials
```

3. **Run with Docker Compose:**
```bash
docker-compose up
```

The API will be available at `http://localhost:8080`

### Cloud Deployment

For complete Google Cloud setup instructions, see [docs/SETUP.md](docs/SETUP.md).

Quick deployment:
```bash
# Configure .env file
cp .env.example .env
# Edit .env with your project settings

# Deploy
./deploy.sh deploy-all
```

## Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Get started locally
- **[Setup Guide](docs/SETUP.md)** - Complete Google Cloud setup
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Detailed deployment instructions
- **[API Documentation](docs/README_DATABASE_SERVICE.md)** - API endpoints and usage
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Configuration](docs/CONFIGURATION.md)** - Configuration options

See [docs/context_index.md](docs/context_index.md) for a complete documentation index.

## API Endpoints

- `GET /health` - Health check
- `GET /api/readings` - List glucose readings (with filters)
- `GET /api/readings/latest` - Get most recent reading
- `GET /api/readings/stats` - Get aggregated statistics
- `POST /api/sync` - Manually trigger sync
- `GET /api/sync-logs` - View sync operation history
- `GET /api/sync-stats` - View sync statistics

See [docs/README_DATABASE_SERVICE.md](docs/README_DATABASE_SERVICE.md) for detailed API documentation.

## Architecture

- **API Service** (Cloud Run): FastAPI service handling REST requests
- **Sync Job** (Cloud Run Jobs): Scheduled job fetching data from LibreLinkUp
- **PostgreSQL** (Cloud SQL): Managed database for glucose readings
- **Secret Manager**: Secure credential storage
- **Cloud Scheduler**: Automated sync scheduling

## Development

### Project Structure

```
libre-link-up-api-client-py/
├── libre_link_up_client/    # Main package
│   ├── api.py              # FastAPI endpoints (database service)
│   ├── database.py         # Database operations
│   ├── sync_service.py     # Sync logic
│   ├── client.py           # LibreLinkUp API client (standalone)
│   └── types.py            # Data models
├── service.py              # Database service entry point (API server/sync)
├── example_usage.py        # Standalone client usage example
├── setup.py                # Python package installation
├── docs/                   # Documentation
├── deploy.sh               # Deployment script
├── docker-compose.yml      # Local development
└── Dockerfile              # Container image
```

### Key Files

- **`setup.py`** - Python package configuration. Install with `pip install -e .`
- **`service.py`** - Database service entry point. Run API server (`python service.py`) or sync job (`python service.py sync`)
- **`example_usage.py`** - Standalone LibreLinkUp client usage example (no database required)

### Running Locally

**Standalone Client (no database):**
```bash
# Install package
pip install -e .

# Run example
python example_usage.py
```

**Database Service:**
```bash
# Start database
docker-compose up postgres

# Run API server
python service.py

# Run one-time sync
python service.py sync
```

## License

MIT License

## Credits

Based on the [libre-link-up-api-client](https://github.com/DiaKEM/libre-link-up-api-client) by DiaKEM.

## Disclaimer

This is an unofficial service and is not affiliated with or endorsed by Abbott. Use at your own risk.
