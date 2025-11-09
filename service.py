"""Main service entry point for LibreLinkUp Database Service

Supports two modes:
- API mode: Run REST API server (for Cloud Run service)
- Sync mode: Run one-time sync (for Cloud Run jobs)
"""

import os
import sys
import logging
import uvicorn
from libre_link_up_client.api import app
from libre_link_up_client.sync_service import sync_readings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_api_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the REST API server"""
    logger.info(f"Starting LibreLinkUp API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_sync():
    """Run a one-time sync"""
    logger.info("Running LibreLinkUp sync...")
    result = sync_readings()
    
    if result['error']:
        logger.error(f"Sync failed: {result['error']}")
        sys.exit(1)
    else:
        logger.info(
            f"Sync completed: {result['readings_inserted']} new readings inserted "
            f"out of {result['readings_fetched']} fetched"
        )
        sys.exit(0)


if __name__ == '__main__':
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == 'sync':
        # Sync mode
        run_sync()
    else:
        # API mode (default)
        port = int(os.getenv('PORT', '8080'))
        run_api_server(port=port)

