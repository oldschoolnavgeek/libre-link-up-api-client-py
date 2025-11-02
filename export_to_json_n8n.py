"""
LibreLinkUp JSON Exporter for n8n Code Node

This script outputs JSON formatted data that n8n can easily process.
Supports multiple input methods:
1. Environment variables (best for n8n Execute Command)
2. JSON input from stdin (best for n8n Code node)
3. config.yaml file (fallback for local testing)
"""

import json
import sys
import os
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from libre_link_up_client import LibreLinkUpClient

def convert_to_gmt3(dt: datetime) -> datetime:
    """Convert datetime from GMT/UTC to GMT+3"""
    if dt.tzinfo is not None:
        gmt3 = timezone(timedelta(hours=3))
        return dt.astimezone(gmt3)
    else:
        utc_dt = dt.replace(tzinfo=timezone.utc)
        gmt3 = timezone(timedelta(hours=3))
        return utc_dt.astimezone(gmt3)

def get_readings_json(client: LibreLinkUpClient, num_readings: int = 1000):
    """Get glucose readings in JSON format"""
    data = client.read()
    history = data['history']
    current = data['current']
    
    all_readings = history + [current]
    all_readings.sort(key=lambda x: x.date)
    last_readings = all_readings[-num_readings:] if len(all_readings) > num_readings else all_readings
    
    readings_json = []
    for reading in last_readings:
        dt_gmt3 = convert_to_gmt3(reading.date)
        readings_json.append({
            'datetime': dt_gmt3.strftime('%Y-%m-%d %H:%M:%S'),
            'date': dt_gmt3.strftime('%Y-%m-%d'),
            'time': dt_gmt3.strftime('%H:%M:%S'),
            'timestamp': int(dt_gmt3.timestamp()),
            'value': reading.value,
            'value_mgdl': reading.value,
            'trend': reading.trend.value,
            'is_high': reading.is_high,
            'is_low': reading.is_low,
            'gmt_datetime': reading.date.strftime('%Y-%m-%d %H:%M:%S UTC'),
        })
    
    return readings_json

def load_config():
    """Load configuration from multiple sources (priority order):
    1. Environment variables (best for n8n)
    2. JSON from stdin (for n8n Code node)
    3. config.yaml file (fallback)
    """
    config = {
        'username': None,
        'password': None,
        'client_version': '4.16.0',
        'connection_identifier': None,
        'num_readings': 1000
    }
    
    # Method 1: Environment variables (highest priority for n8n)
    config['username'] = os.getenv('LIBRE_USERNAME') or config['username']
    config['password'] = os.getenv('LIBRE_PASSWORD') or config['password']
    config['client_version'] = os.getenv('LIBRE_CLIENT_VERSION', config['client_version'])
    
    num_readings_env = os.getenv('LIBRE_NUM_READINGS')
    if num_readings_env:
        try:
            config['num_readings'] = int(num_readings_env)
        except ValueError:
            pass
    
    connection_id_env = os.getenv('LIBRE_CONNECTION_IDENTIFIER')
    if connection_id_env:
        config['connection_identifier'] = connection_id_env if connection_id_env.lower() != 'null' else None
    
    # Method 2: JSON input from stdin (for n8n Code node)
    if not sys.stdin.isatty():  # Check if there's input from stdin
        try:
            stdin_input = sys.stdin.read()
            if stdin_input.strip():
                stdin_config = json.loads(stdin_input)
                # Allow credentials to come from n8n input
                if 'username' in stdin_config and not config['username']:
                    config['username'] = stdin_config['username']
                if 'password' in stdin_config and not config['password']:
                    config['password'] = stdin_config['password']
                if 'client_version' in stdin_config:
                    config['client_version'] = stdin_config['client_version']
                if 'num_readings' in stdin_config:
                    config['num_readings'] = int(stdin_config['num_readings'])
                if 'connection_identifier' in stdin_config:
                    conn_id = stdin_config['connection_identifier']
                    config['connection_identifier'] = conn_id if conn_id and conn_id.lower() != 'null' else None
        except (json.JSONDecodeError, ValueError):
            pass  # Ignore if stdin is not valid JSON
    
    # Method 3: config.yaml file (fallback for local testing)
    if not config['username'] or not config['password']:
        config_path = Path(__file__).parent / 'config.yaml'
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    yaml_config = yaml.safe_load(f)
                    libre_config = yaml_config.get('libre_link_up', {})
                    
                    if not config['username']:
                        config['username'] = libre_config.get('username')
                    if not config['password']:
                        config['password'] = libre_config.get('password')
                    if config['client_version'] == '4.16.0':  # Only override if not set
                        config['client_version'] = libre_config.get('client_version', config['client_version'])
                    if 'connection_identifier' in libre_config:
                        conn_id = libre_config.get('connection_identifier')
                        config['connection_identifier'] = conn_id if conn_id and (isinstance(conn_id, str) or conn_id) else None
                    if 'num_readings' in libre_config:
                        config['num_readings'] = int(libre_config.get('num_readings', config['num_readings']))
            except Exception:
                pass
    
    return config

# Load configuration
config = load_config()

# Validate credentials
if not config['username'] or not config['password']:
    output = json.dumps({
        'error': 'Missing credentials',
        'message': 'Please provide credentials via:\n'
                   '  - Environment variables: LIBRE_USERNAME, LIBRE_PASSWORD\n'
                   '  - JSON input from stdin\n'
                   '  - config.yaml file',
        'success': False
    }, indent=2)
    print(output)
    sys.exit(1)

# Execute
try:
    client = LibreLinkUpClient(
        username=config['username'],
        password=config['password'],
        client_version=config['client_version'],
        connection_identifier=config['connection_identifier']
    )
    
    readings = get_readings_json(client, num_readings=config['num_readings'])
    
    # Output format optimized for n8n
    output = {
        'success': True,
        'count': len(readings),
        'readings': readings,
        'metadata': {
            'first_reading': readings[0]['datetime'] if readings else None,
            'last_reading': readings[-1]['datetime'] if readings else None,
            'timezone': 'GMT+3',
            'export_time': datetime.now(timezone(timedelta(hours=3))).strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    
    # Print JSON - n8n will capture this as output
    print(json.dumps(output, indent=2, ensure_ascii=False))
    
except Exception as e:
    output = {
        'error': str(e),
        'success': False
    }
    print(json.dumps(output, indent=2))
    sys.exit(1)
