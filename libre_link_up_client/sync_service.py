"""Sync service for fetching and storing LibreLinkUp readings"""

import os
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime
import yaml
from pathlib import Path

from .client import LibreLinkUpClient
from .database import init_db, insert_readings, log_sync
from .types import LibreCgmData

logger = logging.getLogger(__name__)


def get_libre_config() -> dict:
    """Get LibreLinkUp configuration from environment variables or config file"""
    # Try environment variables first (for Cloud Run)
    username = os.getenv('LIBRE_USERNAME')
    password = os.getenv('LIBRE_PASSWORD')
    client_version = os.getenv('LIBRE_CLIENT_VERSION', '4.16.0')
    connection_identifier = os.getenv('LIBRE_CONNECTION_IDENTIFIER')
    
    # If not in env, try config file (for local development)
    if not username or not password:
        try:
            config_path = Path(__file__).parent.parent / 'config.yaml'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    libre_config = config.get('libre_link_up', {})
                    username = username or libre_config.get('username')
                    password = password or libre_config.get('password')
                    client_version = client_version or libre_config.get('client_version', '4.16.0')
                    connection_identifier = connection_identifier or libre_config.get('connection_identifier')
        except Exception as e:
            logger.warning(f"Could not load config file: {e}")
    
    if not username or not password:
        raise ValueError(
            "LibreLinkUp configuration not found. Set LIBRE_USERNAME and LIBRE_PASSWORD "
            "environment variables or configure in config.yaml"
        )
    
    return {
        'username': username,
        'password': password,
        'client_version': client_version,
        'connection_identifier': connection_identifier
    }


def sync_readings() -> Dict[str, Any]:
    """
    Main sync function: fetch readings from LibreLinkUp and store in database
    
    Returns:
        Dictionary with sync results including observability data
    """
    start_time = time.time()
    sync_id = None
    
    logger.info("Starting LibreLinkUp sync...")
    
    result = {
        'readings_fetched': 0,
        'readings_inserted': 0,
        'error': None,
        'sync_id': None,
        'first_reading_timestamp': None,
        'last_reading_timestamp': None,
        'duration_seconds': None
    }
    
    try:
        # Initialize database schema if needed
        init_db()
        logger.info("Database initialized")
        
        # Get configuration
        config = get_libre_config()
        logger.info(f"Connecting to LibreLinkUp for user: {config['username']}")
        
        # Initialize LibreLinkUp client
        client = LibreLinkUpClient(
            username=config['username'],
            password=config['password'],
            client_version=config['client_version'],
            connection_identifier=config.get('connection_identifier')
        )
        
        # Fetch data from LibreLinkUp
        logger.info("Fetching readings from LibreLinkUp API...")
        data = client.read()
        
        current = data['current']
        history = data['history']
        
        # Combine current and history
        all_readings = history + [current]
        
        # Remove duplicates (in case current is also in history)
        seen_timestamps = set()
        unique_readings = []
        for reading in all_readings:
            if reading.date not in seen_timestamps:
                seen_timestamps.add(reading.date)
                unique_readings.append(reading)
        
        result['readings_fetched'] = len(unique_readings)
        logger.info(f"Fetched {len(unique_readings)} readings from LibreLinkUp")
        
        # Determine first and last reading timestamps
        first_reading_timestamp = None
        last_reading_timestamp = None
        if unique_readings:
            timestamps = [r.date for r in unique_readings]
            first_reading_timestamp = min(timestamps)
            last_reading_timestamp = max(timestamps)
            result['first_reading_timestamp'] = first_reading_timestamp
            result['last_reading_timestamp'] = last_reading_timestamp
        
        # Log sync before inserting (to get sync_id)
        duration_so_far = time.time() - start_time
        sync_id = log_sync(
            readings_fetched=len(unique_readings),
            readings_inserted=0,  # Will update after insert
            first_reading_timestamp=first_reading_timestamp,
            last_reading_timestamp=last_reading_timestamp,
            success=True,
            duration_seconds=None  # Will update after insert
        )
        result['sync_id'] = sync_id
        
        # Insert readings into database (with deduplication and sync_id)
        if unique_readings:
            readings_inserted = insert_readings(unique_readings, sync_id=sync_id)
            result['readings_inserted'] = readings_inserted
            logger.info(f"Inserted {readings_inserted} new readings into database")
        else:
            logger.warning("No readings to insert")
        
        # Update sync log with final results
        final_duration = time.time() - start_time
        result['duration_seconds'] = final_duration
        
        # Update sync log with final inserted count and duration
        try:
            from .database import get_connection, return_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_logs 
                SET readings_inserted = %s, duration_seconds = %s
                WHERE id = %s
            """, (result['readings_inserted'], final_duration, sync_id))
            conn.commit()
            return_connection(conn)
        except Exception as e:
            logger.warning(f"Failed to update sync log: {e}")
        
        logger.info(f"Sync completed successfully (sync_id={sync_id}, duration={final_duration:.2f}s)")
        
    except Exception as e:
        error_msg = str(e)
        result['error'] = error_msg
        logger.error(f"Error during sync: {error_msg}", exc_info=True)
        
        duration = time.time() - start_time
        result['duration_seconds'] = duration
        
        # Log failed sync
        try:
            sync_id = log_sync(
                readings_fetched=result['readings_fetched'],
                readings_inserted=result['readings_inserted'],
                success=False,
                error_message=error_msg,
                duration_seconds=duration
            )
            result['sync_id'] = sync_id
        except Exception as log_error:
            logger.error(f"Failed to log sync error: {log_error}")
        
        # Provide helpful error messages
        if 'Bad credentials' in error_msg:
            logger.error("Invalid LibreLinkUp credentials. Please check your username and password.")
        elif 'Additional action required' in error_msg:
            logger.error("Please login via the LibreLinkUp app and complete required authentication steps.")
        elif 'follow any patients' in error_msg:
            logger.error("Your account does not follow any patients. Please start following a patient in the LibreLinkUp app.")
    
    return result


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run sync
    result = sync_readings()
    
    if result['error']:
        print(f"❌ Sync failed: {result['error']}")
        exit(1)
    else:
        print(f"✅ Sync completed: {result['readings_inserted']} new readings inserted out of {result['readings_fetched']} fetched")
        exit(0)
