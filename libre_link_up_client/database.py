"""Database operations for LibreLinkUp readings"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from psycopg2.pool import SimpleConnectionPool

from .types import LibreCgmData

logger = logging.getLogger(__name__)

# Connection pool (initialized on first use)
_connection_pool: Optional[SimpleConnectionPool] = None


def get_db_config() -> Dict[str, Any]:
    """Get database configuration from environment variables or config file"""
    # Try environment variables first (for Cloud Run)
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    
    # If not in env, try config file (for local development)
    if not all([db_host, db_name, db_user, db_password]):
        try:
            import yaml
            from pathlib import Path
            config_path = Path(__file__).parent.parent / 'config.yaml'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    db_config = config.get('database', {})
                    db_host = db_host or db_config.get('host')
                    db_port = db_port or str(db_config.get('port', 5432))
                    db_name = db_name or db_config.get('name')
                    db_user = db_user or db_config.get('user')
                    db_password = db_password or db_config.get('password')
        except Exception as e:
            logger.warning(f"Could not load config file: {e}")
    
    if not all([db_host, db_name, db_user, db_password]):
        raise ValueError(
            "Database configuration not found. Set DB_HOST, DB_NAME, DB_USER, DB_PASSWORD "
            "environment variables or configure in config.yaml"
        )
    
    return {
        'host': db_host,
        'port': int(db_port),
        'database': db_name,
        'user': db_user,
        'password': db_password
    }


def get_connection_pool() -> SimpleConnectionPool:
    """Get or create database connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        config = get_db_config()
        
        # For Cloud SQL, use Unix socket if connection name is provided
        # Format: PROJECT_ID:REGION:INSTANCE_NAME
        # Cloud SQL connection via Unix socket doesn't use port
        if ':' in config['host'] and '/' not in config['host']:
            # Cloud SQL connection name - convert to Unix socket path
            cloud_sql_connection_name = config['host']
            config['host'] = f"/cloudsql/{cloud_sql_connection_name}"
            # Remove port for Unix socket connection
            config.pop('port', None)
        
        _connection_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            **config
        )
    
    return _connection_pool


def get_connection():
    """Get a database connection from the pool"""
    pool = get_connection_pool()
    return pool.getconn()


def return_connection(conn):
    """Return a connection to the pool"""
    pool = get_connection_pool()
    pool.putconn(conn)


def init_db():
    """Initialize database schema if it doesn't exist"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create sync_logs table for observability
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_logs (
                id SERIAL PRIMARY KEY,
                sync_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                readings_fetched INTEGER NOT NULL DEFAULT 0,
                readings_inserted INTEGER NOT NULL DEFAULT 0,
                first_reading_timestamp TIMESTAMP,
                last_reading_timestamp TIMESTAMP,
                success BOOLEAN NOT NULL DEFAULT true,
                error_message TEXT,
                duration_seconds NUMERIC(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on sync_timestamp for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_logs_timestamp 
            ON sync_logs(sync_timestamp DESC)
        """)
        
        # Check if readings table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'readings'
            )
        """)
        readings_table_exists = cursor.fetchone()[0]
        
        # Create readings table (without sync_id for compatibility)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL UNIQUE,
                value NUMERIC(5,1) NOT NULL,
                trend VARCHAR(20) NOT NULL,
                is_high BOOLEAN NOT NULL,
                is_low BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migrate existing readings table to add sync_id column if it doesn't exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'readings' AND column_name = 'sync_id'
        """)
        if not cursor.fetchone():
            logger.info("Adding sync_id column to readings table...")
            try:
                # Add column without foreign key constraint first (safer for migration)
                cursor.execute("""
                    ALTER TABLE readings 
                    ADD COLUMN sync_id INTEGER
                """)
                logger.info("Added sync_id column to readings table")
                
                # Add foreign key constraint if sync_logs table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'sync_logs'
                    )
                """)
                sync_logs_exists = cursor.fetchone()[0]
                
                if sync_logs_exists:
                    try:
                        cursor.execute("""
                            ALTER TABLE readings 
                            ADD CONSTRAINT fk_readings_sync_id 
                            FOREIGN KEY (sync_id) REFERENCES sync_logs(id)
                        """)
                        logger.info("Added foreign key constraint for sync_id")
                    except Exception as fk_error:
                        logger.warning(f"Could not add foreign key constraint (may already exist): {fk_error}")
            except Exception as e:
                # Column might already exist
                if 'already exists' not in str(e).lower():
                    logger.warning(f"Could not add sync_id column: {e}")
        
        # Create index on timestamp for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
            ON readings(timestamp DESC)
        """)
        
        # Create index on sync_id for linking readings to sync calls (only if column exists)
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'readings' AND column_name = 'sync_id'
        """)
        if cursor.fetchone():
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_readings_sync_id 
                ON readings(sync_id)
            """)
        
        conn.commit()
        logger.info("Database schema initialized successfully")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def insert_reading(reading: LibreCgmData, sync_id: Optional[int] = None) -> bool:
    """
    Insert a single reading into the database with deduplication
    
    Returns:
        True if inserted, False if already exists
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO readings (timestamp, value, trend, is_high, is_low, sync_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp) DO NOTHING
        """, (
            reading.date,
            reading.value,
            reading.trend.value,
            reading.is_high,
            reading.is_low,
            sync_id
        ))
        
        inserted = cursor.rowcount > 0
        conn.commit()
        
        if inserted:
            logger.debug(f"Inserted reading: {reading.date} - {reading.value} mg/dL")
        else:
            logger.debug(f"Reading already exists: {reading.date}")
        
        return inserted
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error inserting reading: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def log_sync(
    readings_fetched: int,
    readings_inserted: int,
    first_reading_timestamp: Optional[datetime] = None,
    last_reading_timestamp: Optional[datetime] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    duration_seconds: Optional[float] = None
) -> int:
    """
    Log a sync operation to the database
    
    Returns:
        The ID of the created sync log entry
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sync_logs (
                readings_fetched, readings_inserted,
                first_reading_timestamp, last_reading_timestamp,
                success, error_message, duration_seconds
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            readings_fetched,
            readings_inserted,
            first_reading_timestamp,
            last_reading_timestamp,
            success,
            error_message,
            duration_seconds
        ))
        
        sync_id = cursor.fetchone()[0]
        conn.commit()
        
        logger.info(f"Logged sync operation: ID={sync_id}, fetched={readings_fetched}, inserted={readings_inserted}")
        
        return sync_id
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error logging sync: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def insert_readings(readings: List[LibreCgmData], sync_id: Optional[int] = None) -> int:
    """
    Insert multiple readings into the database with deduplication
    
    Args:
        readings: List of LibreCgmData objects to insert
        sync_id: Optional sync log ID to link readings to a sync operation
    
    Returns:
        Number of readings actually inserted (excluding duplicates)
    """
    if not readings:
        return 0
    
    conn = None
    inserted_count = 0
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Use executemany for batch insert
        values = [
            (
                reading.date,
                reading.value,
                reading.trend.value,
                reading.is_high,
                reading.is_low,
                sync_id
            )
            for reading in readings
        ]
        
        cursor.executemany("""
            INSERT INTO readings (timestamp, value, trend, is_high, is_low, sync_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp) DO NOTHING
        """, values)
        
        inserted_count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Inserted {inserted_count} new readings out of {len(readings)} total")
        
        return inserted_count
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error inserting readings: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def get_readings(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Query readings from the database
    
    Args:
        start_date: Start date for filtering (inclusive)
        end_date: End date for filtering (inclusive)
        limit: Maximum number of readings to return
        offset: Number of readings to skip
    
    Returns:
        List of reading dictionaries
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM readings WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        if offset:
            query += " OFFSET %s"
            params.append(offset)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Convert to list of dicts
        readings = [dict(row) for row in results]
        
        logger.debug(f"Retrieved {len(readings)} readings from database")
        
        return readings
        
    except Exception as e:
        logger.error(f"Error querying readings: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def get_latest() -> Optional[Dict[str, Any]]:
    """Get the most recent reading"""
    readings = get_readings(limit=1)
    return readings[0] if readings else None


def get_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get statistics for readings in a date range
    
    Returns:
        Dictionary with avg, min, max, count
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                COUNT(*) as count,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value
            FROM readings
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        if result and result['count']:
            return {
                'count': result['count'],
                'avg_value': float(result['avg_value']) if result['avg_value'] else None,
                'min_value': result['min_value'],
                'max_value': result['max_value']
            }
        else:
            return {
                'count': 0,
                'avg_value': None,
                'min_value': None,
                'max_value': None
            }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def get_sync_logs(limit: Optional[int] = 50) -> List[Dict[str, Any]]:
    """
    Get sync log history
    
    Args:
        limit: Maximum number of sync logs to return
    
    Returns:
        List of sync log dictionaries
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                id,
                sync_timestamp,
                readings_fetched,
                readings_inserted,
                first_reading_timestamp,
                last_reading_timestamp,
                success,
                error_message,
                duration_seconds,
                created_at
            FROM sync_logs
            ORDER BY sync_timestamp DESC
        """
        
        if limit:
            query += " LIMIT %s"
            cursor.execute(query, (limit,))
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        logs = [dict(row) for row in results]
        
        logger.debug(f"Retrieved {len(logs)} sync logs")
        
        return logs
        
    except Exception as e:
        logger.error(f"Error querying sync logs: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def get_sync_stats() -> Dict[str, Any]:
    """
    Get statistics about sync operations
    
    Returns:
        Dictionary with sync statistics
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_syncs,
                COUNT(*) FILTER (WHERE success = true) as successful_syncs,
                COUNT(*) FILTER (WHERE success = false) as failed_syncs,
                SUM(readings_fetched) as total_readings_fetched,
                SUM(readings_inserted) as total_readings_inserted,
                AVG(duration_seconds) as avg_duration_seconds,
                MAX(sync_timestamp) as last_sync_timestamp,
                MIN(sync_timestamp) as first_sync_timestamp
            FROM sync_logs
        """)
        
        result = cursor.fetchone()
        
        if result:
            return {
                'total_syncs': result['total_syncs'] or 0,
                'successful_syncs': result['successful_syncs'] or 0,
                'failed_syncs': result['failed_syncs'] or 0,
                'total_readings_fetched': result['total_readings_fetched'] or 0,
                'total_readings_inserted': result['total_readings_inserted'] or 0,
                'avg_duration_seconds': float(result['avg_duration_seconds']) if result['avg_duration_seconds'] else None,
                'last_sync_timestamp': result['last_sync_timestamp'].isoformat() if result['last_sync_timestamp'] else None,
                'first_sync_timestamp': result['first_sync_timestamp'].isoformat() if result['first_sync_timestamp'] else None
            }
        else:
            return {
                'total_syncs': 0,
                'successful_syncs': 0,
                'failed_syncs': 0,
                'total_readings_fetched': 0,
                'total_readings_inserted': 0,
                'avg_duration_seconds': None,
                'last_sync_timestamp': None,
                'first_sync_timestamp': None
            }
        
    except Exception as e:
        logger.error(f"Error getting sync statistics: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)

