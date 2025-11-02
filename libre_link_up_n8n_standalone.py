"""
LibreLinkUp JSON Exporter - Standalone Script for n8n Cloud
Single-file script - no external module dependencies required

Usage:
    Set environment variables:
    - LIBRE_USERNAME: Your LibreLinkUp email
    - LIBRE_PASSWORD: Your LibreLinkUp password
    - LIBRE_NUM_READINGS: Number of readings (default: 1000)
    - LIBRE_CLIENT_VERSION: Client version (default: 4.16.0)
    - LIBRE_CONNECTION_IDENTIFIER: Patient name or null (optional)

Outputs JSON to stdout for n8n processing.
"""

import json
import sys
import os
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print(json.dumps({
        'error': 'Missing dependencies',
        'message': 'Please install: pip install requests urllib3',
        'success': False
    }))
    sys.exit(1)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class TrendType(str, Enum):
    """Glucose trend direction"""
    SINGLE_DOWN = 'SingleDown'
    FORTY_FIVE_DOWN = 'FortyFiveDown'
    FLAT = 'Flat'
    FORTY_FIVE_UP = 'FortyFiveUp'
    SINGLE_UP = 'SingleUp'
    NOT_COMPUTABLE = 'NotComputable'


@dataclass
class LibreCgmData:
    """Continuous Glucose Monitor data"""
    value: int
    is_high: bool
    is_low: bool
    trend: TrendType
    date: datetime


@dataclass
class GlucoseItem:
    """Raw glucose measurement from API"""
    FactoryTimestamp: str
    Timestamp: str
    type: int
    ValueInMgPerDl: int
    TrendArrow: Optional[int]
    TrendMessage: Optional[str]
    MeasurementColor: int
    GlucoseUnits: int
    Value: int
    isHigh: bool
    isLow: bool


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

TREND_MAP = [
    TrendType.NOT_COMPUTABLE,
    TrendType.SINGLE_DOWN,
    TrendType.FORTY_FIVE_DOWN,
    TrendType.FLAT,
    TrendType.FORTY_FIVE_UP,
    TrendType.SINGLE_UP,
    TrendType.NOT_COMPUTABLE,
]


def get_trend(trend: Optional[int], default_trend: TrendType = TrendType.FLAT) -> TrendType:
    """Convert numeric trend to TrendType enum"""
    if trend is not None and 0 <= trend < len(TREND_MAP):
        return TREND_MAP[trend]
    return default_trend


def to_date(date_string: str) -> datetime:
    """Convert timestamp string to datetime object"""
    try:
        if 'UTC' in date_string:
            cleaned = date_string.replace(' UTC', '').strip()
            
            # Try US format first (e.g., "10/31/2025 7:36:41 PM")
            try:
                # Try with AM/PM
                dt = datetime.strptime(cleaned, '%m/%d/%Y %I:%M:%S %p')
                dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                pass
            
            # Try US format without AM/PM (24-hour)
            try:
                dt = datetime.strptime(cleaned, '%m/%d/%Y %H:%M:%S')
                dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                pass
            
            # Try ISO format
            try:
                dt = datetime.fromisoformat(cleaned)
            except ValueError:
                # Try other common formats
                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                    try:
                        dt = datetime.strptime(cleaned, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f"Cannot parse date: {date_string}")
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        else:
            dt = datetime.fromisoformat(date_string)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except (ValueError, AttributeError) as e:
        # Last resort: try common formats
        for fmt in [
            '%m/%d/%Y %I:%M:%S %p',  # US with AM/PM
            '%m/%d/%Y %H:%M:%S',     # US 24-hour
            '%Y-%m-%dT%H:%M:%S',     # ISO
            '%Y-%m-%d %H:%M:%S',     # ISO-like
        ]:
            try:
                cleaned = date_string.replace(' UTC', '').strip()
                dt = datetime.strptime(cleaned, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        raise ValueError(f"Cannot parse date: {date_string}")


def map_data(glucose_item: GlucoseItem) -> LibreCgmData:
    """Map API GlucoseItem to LibreCgmData"""
    return LibreCgmData(
        value=glucose_item.Value,
        is_high=glucose_item.isHigh,
        is_low=glucose_item.isLow,
        trend=get_trend(glucose_item.TrendArrow),
        date=to_date(f"{glucose_item.FactoryTimestamp} UTC")
    )


def convert_to_gmt3(dt: datetime) -> datetime:
    """Convert datetime from GMT/UTC to GMT+3"""
    if dt.tzinfo is not None:
        gmt3 = timezone(timedelta(hours=3))
        return dt.astimezone(gmt3)
    else:
        utc_dt = dt.replace(tzinfo=timezone.utc)
        gmt3 = timezone(timedelta(hours=3))
        return utc_dt.astimezone(gmt3)


# ============================================================================
# LIBRE LINK UP CLIENT
# ============================================================================

LIBRE_LINK_SERVER = 'https://api.libreview.ru'  # Russia/EU endpoint

URL_MAP = {
    'login': '/llu/auth/login',
    'connections': '/llu/connections',
    'countries': '/llu/config/country?country=RU',
}


class LibreLinkUpClient:
    """Client for accessing LibreLinkUp API"""
    
    def __init__(
        self,
        username: str,
        password: str,
        client_version: str = '4.16.0',
        connection_identifier: Optional[str] = None
    ):
        self.username = username
        self.password = password
        self.client_version = client_version
        self.connection_identifier = connection_identifier
        
        self.jwt_token: Optional[str] = None
        self.account_id: Optional[str] = None
        self.connection_id: Optional[str] = None
        self.base_url = LIBRE_LINK_SERVER
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'accept-encoding': 'gzip',
            'cache-control': 'no-cache',
            'connection': 'Keep-Alive',
            'content-type': 'application/json',
            'product': 'llu.android',
            'version': self.client_version,
            'account-id': '',
        })
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {}
        if self.jwt_token and self.account_id:
            headers['authorization'] = f'Bearer {self.jwt_token}'
            headers['account-id'] = hashlib.sha256(self.account_id.encode()).hexdigest()
        return headers
    
    def login(self) -> Dict[str, Any]:
        """Login to LibreLinkUp service"""
        login_data = {
            'email': self.username,
            'password': self.password,
        }
        
        response = self.session.post(
            f"{self.base_url}{URL_MAP['login']}",
            json=login_data,
            headers=self._get_headers()
        )
        
        if response.status_code != 200:
            raise Exception(f"Login failed with status code: {response.status_code}")
        
        login_response = response.json()
        
        if login_response.get('status') == 2:
            raise Exception(
                'Bad credentials. Please ensure that you have entered the credentials '
                'of your LibreLinkUp account (and not of your LibreLink account).'
            )
        
        if login_response.get('status') == 4:
            step_data = login_response.get('data', {})
            component_name = step_data.get('step', {}).get('componentName', 'unknown')
            raise Exception(
                f'Additional action required for your account: {component_name}. '
                'Please login via app and perform required steps and try again.'
            )
        
        # Handle regional redirect
        if isinstance(login_response.get('data'), dict):
            data = login_response['data']
            if data.get('redirect'):
                region = data.get('region')
                country_response = self.session.get(f"{self.base_url}{URL_MAP['countries']}")
                if country_response.status_code == 200:
                    country_data = country_response.json()
                    regional_map = country_data.get('data', {}).get('regionalMap', {})
                    if region in regional_map:
                        self.base_url = regional_map[region]['lslApi']
                        return self.login()
                    else:
                        available_regions = ', '.join(regional_map.keys())
                        raise Exception(
                            f"Unable to find region '{region}'. "
                            f"Available nodes are {available_regions}."
                        )
        
        # Extract token and account ID
        data = login_response.get('data', {})
        if isinstance(data, dict) and 'authTicket' in data:
            self.jwt_token = data['authTicket']['token']
            self.account_id = data['user']['id']
        elif 'authTicket' in login_response.get('data', {}):
            auth_data = login_response.get('data', {})
            self.jwt_token = auth_data.get('authTicket', {}).get('token')
            self.account_id = auth_data.get('user', {}).get('id')
        
        return login_response
    
    def _ensure_logged_in(self):
        """Ensure user is logged in, login if not"""
        if not self.jwt_token:
            self.login()
    
    def get_connections(self) -> List[Dict[str, Any]]:
        """Get list of connections (patients being followed)"""
        self._ensure_logged_in()
        
        response = self.session.get(
            f"{self.base_url}{URL_MAP['connections']}",
            headers=self._get_headers()
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get connections: {response.status_code}")
        
        connections_response = response.json()
        return connections_response.get('data', [])
    
    def _get_connection_id(self, connections: List[Dict[str, Any]]) -> str:
        """Get connection ID from connections list"""
        if not connections:
            raise Exception(
                'Your account does not follow any patients. '
                'Please start following and try again.'
            )
        
        if isinstance(self.connection_identifier, str):
            full_name = self.connection_identifier.lower()
            for conn in connections:
                conn_name = f"{conn.get('firstName', '')} {conn.get('lastName', '')}".lower()
                if conn_name == full_name:
                    return conn['patientId']
            raise Exception(
                f"Unable to identify connection by given name '{self.connection_identifier}'."
            )
        
        # Default: use first connection
        return connections[0]['patientId']
    
    def read_raw(self) -> Dict[str, Any]:
        """Read raw data from LibreLinkUp API"""
        self._ensure_logged_in()
        
        if not self.connection_id:
            connections = self.get_connections()
            self.connection_id = self._get_connection_id(connections)
        
        response = self.session.get(
            f"{self.base_url}{URL_MAP['connections']}/{self.connection_id}/graph",
            headers=self._get_headers()
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to read data: {response.status_code}")
        
        graph_data = response.json()
        return graph_data.get('data', {})
    
    def read(self) -> Dict[str, Any]:
        """Read processed CGM data"""
        raw_data = self.read_raw()
        
        glucose_measurement = raw_data.get('connection', {}).get('glucoseMeasurement', {})
        if not glucose_measurement:
            raise Exception("No glucose measurement data available")
        
        # Convert dict to GlucoseItem
        glucose_item = GlucoseItem(
            FactoryTimestamp=glucose_measurement.get('FactoryTimestamp', ''),
            Timestamp=glucose_measurement.get('Timestamp', ''),
            type=glucose_measurement.get('type', 0),
            ValueInMgPerDl=glucose_measurement.get('ValueInMgPerDl', 0),
            TrendArrow=glucose_measurement.get('TrendArrow'),
            TrendMessage=glucose_measurement.get('TrendMessage'),
            MeasurementColor=glucose_measurement.get('MeasurementColor', 0),
            GlucoseUnits=glucose_measurement.get('GlucoseUnits', 0),
            Value=glucose_measurement.get('Value', 0),
            isHigh=glucose_measurement.get('isHigh', False),
            isLow=glucose_measurement.get('isLow', False),
        )
        current = map_data(glucose_item)
        
        # Map history
        graph_data = raw_data.get('graphData', [])
        history = []
        for item in graph_data:
            glucose_item = GlucoseItem(
                FactoryTimestamp=item.get('FactoryTimestamp', ''),
                Timestamp=item.get('Timestamp', ''),
                type=item.get('type', 0),
                ValueInMgPerDl=item.get('ValueInMgPerDl', 0),
                TrendArrow=item.get('TrendArrow'),
                TrendMessage=item.get('TrendMessage'),
                MeasurementColor=item.get('MeasurementColor', 0),
                GlucoseUnits=item.get('GlucoseUnits', 0),
                Value=item.get('Value', 0),
                isHigh=item.get('isHigh', False),
                isLow=item.get('isLow', False),
            )
            history.append(map_data(glucose_item))
        
        return {
            'current': current,
            'history': history
        }


# ============================================================================
# MAIN SCRIPT
# ============================================================================

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


def main():
    """Main function - outputs JSON for n8n"""
    # Load configuration from environment variables
    username = os.getenv('LIBRE_USERNAME')
    password = os.getenv('LIBRE_PASSWORD')
    client_version = os.getenv('LIBRE_CLIENT_VERSION', '4.16.0')
    
    num_readings = 1000
    try:
        num_readings_env = os.getenv('LIBRE_NUM_READINGS')
        if num_readings_env:
            num_readings = int(num_readings_env)
    except ValueError:
        pass
    
    connection_identifier = os.getenv('LIBRE_CONNECTION_IDENTIFIER')
    if connection_identifier and connection_identifier.lower() == 'null':
        connection_identifier = None
    
    # Validate credentials
    if not username or not password:
        output = json.dumps({
            'error': 'Missing credentials',
            'message': 'Please set environment variables: LIBRE_USERNAME and LIBRE_PASSWORD',
            'success': False
        }, indent=2)
        print(output)
        sys.exit(1)
    
    # Execute
    try:
        client = LibreLinkUpClient(
            username=username,
            password=password,
            client_version=client_version,
            connection_identifier=connection_identifier
        )
        
        readings = get_readings_json(client, num_readings=num_readings)
        
        # Output format for n8n
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


if __name__ == '__main__':
    main()

