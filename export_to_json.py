"""Script to export LibreLinkUp readings to JSON format for n8n code node"""

import json
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from libre_link_up_client import LibreLinkUpClient

def convert_to_gmt3(dt: datetime) -> datetime:
    """Convert datetime from GMT/UTC to GMT+3"""
    # If datetime is timezone-aware, convert to GMT+3
    if dt.tzinfo is not None:
        # Convert to GMT+3 (UTC+3)
        gmt3 = timezone(timedelta(hours=3))
        return dt.astimezone(gmt3)
    else:
        # Assume UTC if timezone-naive, then convert to GMT+3
        utc_dt = dt.replace(tzinfo=timezone.utc)
        gmt3 = timezone(timedelta(hours=3))
        return utc_dt.astimezone(gmt3)

def get_readings_json(client: LibreLinkUpClient, num_readings: int = 1000):
    """
    Get glucose readings in JSON format for n8n
    
    Args:
        client: LibreLinkUpClient instance
        num_readings: Number of readings to retrieve (default: 1000)
    
    Returns:
        List of dictionaries with reading data
    """
    # Get data
    data = client.read()
    history = data['history']
    current = data['current']
    
    # Combine current and history, sort by date (oldest first)
    all_readings = history + [current]
    all_readings.sort(key=lambda x: x.date)
    
    # Get last N readings (most recent)
    last_readings = all_readings[-num_readings:] if len(all_readings) > num_readings else all_readings
    
    # Convert to JSON-serializable format
    readings_json = []
    for reading in last_readings:
        # Convert to GMT+3
        dt_gmt3 = convert_to_gmt3(reading.date)
        
        readings_json.append({
            'datetime': dt_gmt3.strftime('%Y-%m-%d %H:%M:%S'),
            'date': dt_gmt3.strftime('%Y-%m-%d'),
            'time': dt_gmt3.strftime('%H:%M:%S'),
            'timestamp': int(dt_gmt3.timestamp()),
            'value': reading.value,
            'value_mgdl': reading.value,  # Alias for clarity
            'trend': reading.trend.value,
            'is_high': reading.is_high,
            'is_low': reading.is_low,
            'gmt_datetime': reading.date.strftime('%Y-%m-%d %H:%M:%S UTC'),  # Original GMT time
        })
    
    return readings_json

def main():
    """Main function - outputs JSON for n8n"""
    # Load configuration
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        result = {
            'error': 'config.yaml not found',
            'message': 'Please copy config.yaml.example to config.yaml and fill in your credentials'
        }
        print(json.dumps(result, indent=2))
        return
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    libre_config = config.get('libre_link_up', {})
    username = libre_config.get('username')
    password = libre_config.get('password')
    client_version = libre_config.get('client_version', '4.16.0')
    connection_identifier = libre_config.get('connection_identifier')
    num_readings = libre_config.get('num_readings', 1000)  # Allow config override
    
    if not username or not password:
        result = {
            'error': 'Missing credentials',
            'message': 'Please set username and password in config.yaml'
        }
        print(json.dumps(result, indent=2))
        return
    
    try:
        # Initialize client
        client = LibreLinkUpClient(
            username=username,
            password=password,
            client_version=client_version,
            connection_identifier=connection_identifier
        )
        
        # Get readings
        readings = get_readings_json(client, num_readings=num_readings)
        
        # Output JSON for n8n
        # n8n expects an array of items, where each item becomes a separate execution
        result = {
            'success': True,
            'count': len(readings),
            'readings': readings,
            'metadata': {
                'first_reading': readings[0]['datetime'] if readings else None,
                'last_reading': readings[-1]['datetime'] if readings else None,
                'timezone': 'GMT+3'
            }
        }
        
        # Print JSON (n8n will capture this)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        result = {
            'error': str(e),
            'success': False
        }
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()

