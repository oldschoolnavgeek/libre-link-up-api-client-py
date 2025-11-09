"""REST API endpoints for LibreLinkUp Database Service"""

import logging
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Request, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .database import (
    get_readings,
    get_latest,
    get_stats,
    get_sync_logs,
    get_sync_stats,
    init_db
)
from .sync_service import sync_readings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LibreLinkUp Database Service API",
    description="REST API for accessing LibreLinkUp glucose readings stored in PostgreSQL",
    version="1.0.0"
)


# Startup event - initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_db()
        logger.info("Database initialized on startup")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


# Response models
class HealthResponse(BaseModel):
    status: str
    database: str


class ReadingResponse(BaseModel):
    id: int
    timestamp: str
    value: float = Field(..., description="Glucose value in mg/dL (can be decimal)")
    trend: str
    is_high: bool
    is_low: bool
    created_at: str
    
    class Config:
        json_encoders = {
            float: lambda v: float(v)
        }


class ReadingsListResponse(BaseModel):
    readings: List[ReadingResponse]
    count: int
    limit: Optional[int] = None
    offset: int = 0


class StatsResponse(BaseModel):
    count: int
    avg_value: Optional[float] = Field(None, description="Average glucose value")
    min_value: Optional[float] = Field(None, description="Minimum glucose value (can be decimal)")
    max_value: Optional[float] = Field(None, description="Maximum glucose value (can be decimal)")
    
    class Config:
        json_encoders = {
            float: lambda v: float(v)
        }


class SyncResponse(BaseModel):
    success: bool
    readings_fetched: int
    readings_inserted: int
    error: Optional[str] = None
    sync_id: Optional[int] = None
    first_reading_timestamp: Optional[str] = None
    last_reading_timestamp: Optional[str] = None
    duration_seconds: Optional[float] = None


class SyncLogResponse(BaseModel):
    id: int
    sync_timestamp: str
    readings_fetched: int
    readings_inserted: int
    first_reading_timestamp: Optional[str] = None
    last_reading_timestamp: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: str


class SyncLogsListResponse(BaseModel):
    logs: List[SyncLogResponse]
    count: int


class SyncStatsResponse(BaseModel):
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    total_readings_fetched: int
    total_readings_inserted: int
    avg_duration_seconds: Optional[float] = None
    last_sync_timestamp: Optional[str] = None
    first_sync_timestamp: Optional[str] = None


# API endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Try to query the database
        get_readings(limit=1)
        return HealthResponse(status="healthy", database="connected")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(status="degraded", database="disconnected")


@app.get("/api/readings", response_model=ReadingsListResponse)
async def list_readings(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of readings to return"),
    offset: int = Query(0, ge=0, description="Number of readings to skip")
):
    """
    Get a list of glucose readings with optional filtering
    
    - **start_date**: Filter readings from this date onwards (inclusive)
    - **end_date**: Filter readings up to this date (inclusive)
    - **limit**: Maximum number of readings to return (1-1000)
    - **offset**: Number of readings to skip (for pagination)
    """
    try:
        # Parse date strings if provided
        start = None
        end = None
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        readings = get_readings(start_date=start, end_date=end, limit=limit, offset=offset)
        
        # Convert to response format
        reading_responses = [
            ReadingResponse(
                id=r['id'],
                timestamp=r['timestamp'].isoformat() if isinstance(r['timestamp'], datetime) else r['timestamp'],
                value=float(r['value']),
                trend=r['trend'],
                is_high=r['is_high'],
                is_low=r['is_low'],
                created_at=r['created_at'].isoformat() if isinstance(r['created_at'], datetime) else r['created_at']
            )
            for r in readings
        ]
        
        return ReadingsListResponse(
            readings=reading_responses,
            count=len(reading_responses),
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error fetching readings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching readings: {str(e)}")


@app.get("/api/readings/latest", response_model=ReadingResponse)
async def get_latest_reading():
    """Get the most recent glucose reading"""
    try:
        reading = get_latest()
        if not reading:
            raise HTTPException(status_code=404, detail="No readings found")
        
        return ReadingResponse(
            id=reading['id'],
            timestamp=reading['timestamp'].isoformat() if isinstance(reading['timestamp'], datetime) else reading['timestamp'],
            value=float(reading['value']),
            trend=reading['trend'],
            is_high=reading['is_high'],
            is_low=reading['is_low'],
            created_at=reading['created_at'].isoformat() if isinstance(reading['created_at'], datetime) else reading['created_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest reading: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching latest reading: {str(e)}")


@app.get("/api/readings/stats", response_model=StatsResponse)
async def get_statistics(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)")
):
    """
    Get aggregated statistics for glucose readings
    
    Returns count, average, minimum, and maximum values for readings in the specified date range.
    """
    try:
        start = None
        end = None
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        stats = get_stats(start_date=start, end_date=end)
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@app.post("/api/migrate")
async def migrate_schema():
    """Migrate database schema - change value column to NUMERIC"""
    try:
        from .database import get_connection, return_connection
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'readings' AND column_name = 'value'
            """)
            result = cursor.fetchone()
            if result and result[0] == 'integer':
                logger.info("Migrating value column to NUMERIC(5,1)...")
                cursor.execute("""
                    ALTER TABLE readings 
                    ALTER COLUMN value TYPE NUMERIC(5,1) USING value::NUMERIC(5,1)
                """)
                conn.commit()
                logger.info("✅ Migration complete")
                return {"success": True, "message": "Schema migrated successfully"}
            else:
                return {"success": True, "message": f"Column already has type: {result[0] if result else 'unknown'}"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration error: {e}")
            raise
        finally:
            return_connection(conn)
    except Exception as e:
        logger.error(f"Error during migration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error during migration: {str(e)}")


@app.post("/api/sync", response_model=SyncResponse)
async def trigger_sync():
    """
    Manually trigger a sync with LibreLinkUp API
    
    This endpoint fetches the latest readings from LibreLinkUp and stores them in the database.
    Typically called by Cloud Scheduler, but can also be triggered manually.
    """
    try:
        result = sync_readings()
        
        # Convert datetime objects to ISO format strings
        first_ts = result.get('first_reading_timestamp')
        if first_ts and isinstance(first_ts, datetime):
            first_ts = first_ts.isoformat()
        elif first_ts:
            first_ts = str(first_ts)
        
        last_ts = result.get('last_reading_timestamp')
        if last_ts and isinstance(last_ts, datetime):
            last_ts = last_ts.isoformat()
        elif last_ts:
            last_ts = str(last_ts)
        
        return SyncResponse(
            success=result['error'] is None,
            readings_fetched=result['readings_fetched'],
            readings_inserted=result['readings_inserted'],
            error=result.get('error'),
            sync_id=result.get('sync_id'),
            first_reading_timestamp=first_ts,
            last_reading_timestamp=last_ts,
            duration_seconds=result.get('duration_seconds')
        )
    except Exception as e:
        logger.error(f"Error during sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error during sync: {str(e)}")


@app.get("/api/sync-logs", response_model=SyncLogsListResponse)
async def list_sync_logs(
    limit: Optional[int] = Query(50, ge=1, le=1000, description="Maximum number of sync logs to return")
):
    """
    Get history of sync operations
    
    Returns a list of all sync operations with their results and metadata.
    """
    try:
        logs = get_sync_logs(limit=limit)
        
        log_responses = [
            SyncLogResponse(
                id=log['id'],
                sync_timestamp=log['sync_timestamp'].isoformat() if isinstance(log['sync_timestamp'], datetime) else log['sync_timestamp'],
                readings_fetched=log['readings_fetched'],
                readings_inserted=log['readings_inserted'],
                first_reading_timestamp=log['first_reading_timestamp'].isoformat() if log['first_reading_timestamp'] and isinstance(log['first_reading_timestamp'], datetime) else log['first_reading_timestamp'],
                last_reading_timestamp=log['last_reading_timestamp'].isoformat() if log['last_reading_timestamp'] and isinstance(log['last_reading_timestamp'], datetime) else log['last_reading_timestamp'],
                success=log['success'],
                error_message=log.get('error_message'),
                duration_seconds=float(log['duration_seconds']) if log['duration_seconds'] else None,
                created_at=log['created_at'].isoformat() if isinstance(log['created_at'], datetime) else log['created_at']
            )
            for log in logs
        ]
        
        return SyncLogsListResponse(
            logs=log_responses,
            count=len(log_responses)
        )
    except Exception as e:
        logger.error(f"Error fetching sync logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching sync logs: {str(e)}")


@app.get("/api/sync-stats", response_model=SyncStatsResponse)
async def get_sync_statistics():
    """
    Get aggregated statistics about sync operations
    
    Returns overall statistics about all sync operations including success rate,
    total readings processed, and timing information.
    """
    try:
        stats = get_sync_stats()
        return SyncStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error fetching sync statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching sync statistics: {str(e)}")


@app.post("/api/import-csv", 
          summary="Import CSV data",
          description="Import CSV readings into the database. Send CSV content as raw text in request body.")
async def import_csv_endpoint(request: Request):
    """
    Import CSV data into the database
    
    Accepts CSV content as request body (text/plain) and imports readings.
    CSV format should match libre_readings*.csv files.
    """
    # Get CSV data from request body
    body = await request.body()
    csv_data = body.decode('utf-8')
    
    if not csv_data or len(csv_data.strip()) == 0:
        raise HTTPException(status_code=400, detail="CSV data is required in request body")
    try:
        import csv
        from io import StringIO
        from .database import get_connection, return_connection
        from .types import LibreCgmData, TrendType
        from datetime import datetime
        
        conn = get_connection()
        cursor = conn.cursor()
        
        imported = 0
        errors = 0
        
        try:
            reader = csv.DictReader(StringIO(csv_data))
            for row in reader:
                try:
                    date_str = row['Date (GMT+3)']
                    time_str = row['Time (GMT+3)']
                    timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                    value = float(row['Value (mg/dL)'])
                    trend = row['Trend']
                    is_high = row['Is High'].lower() == 'yes'
                    is_low = row['Is Low'].lower() == 'yes'
                    
                    cursor.execute("""
                        INSERT INTO readings (timestamp, value, trend, is_high, is_low)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (timestamp) DO NOTHING
                    """, (timestamp, value, trend, is_high, is_low))
                    
                    if cursor.rowcount > 0:
                        imported += 1
                except Exception as e:
                    errors += 1
                    logger.warning(f"Error importing row: {e}")
                    continue
            
            conn.commit()
            return {
                "success": True,
                "imported": imported,
                "errors": errors
            }
        except Exception as e:
            conn.rollback()
            raise
        finally:
            return_connection(conn)
    except Exception as e:
        logger.error(f"Error importing CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error importing CSV: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
