"""Main LibreLinkUp API Client"""

import hashlib
import threading
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .types import LibreCgmData, TrendType, Connection, ActiveSensor, GlucoseItem
from .utils import map_data


LIBRE_LINK_SERVER = 'https://api.libreview.ru'  # EU region (covers Russia, CIS, EU countries)
# Alternative endpoints:
# US: 'https://api-us.libreview.io'
# EU2: 'https://api-eu2.libreview.io' 
# AP: 'https://api-ap.libreview.io'
# The client will auto-redirect if your account requires a different region

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
        client_version: str = '4.12.0',
        connection_identifier: Optional[str | Callable] = None
    ):
        """
        Initialize LibreLinkUp client
        
        Args:
            username: LibreLinkUp email address
            password: LibreLinkUp password
            client_version: Client version string (default: '4.12.0')
            connection_identifier: Optional connection identifier:
                - String: Full name of patient (e.g., "John Doe")
                - Callable: Function that takes connections list and returns patient_id
        """
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
        """
        Login to LibreLinkUp service
        
        Returns:
            Login response data
            
        Raises:
            Exception: If login fails
        """
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
        
        # Check for bad credentials
        if login_response.get('status') == 2:
            raise Exception(
                'Bad credentials. Please ensure that you have entered the credentials '
                'of your LibreLinkUp account (and not of your LibreLink account).'
            )
        
        # Check for additional action required
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
                # Get country nodes to find regional endpoint
                country_response = self.session.get(
                    f"{self.base_url}{URL_MAP['countries']}"
                )
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
            # Handle case where data might be nested differently
            auth_data = login_response.get('data', {})
            self.jwt_token = auth_data.get('authTicket', {}).get('token')
            self.account_id = auth_data.get('user', {}).get('id')
        
        return login_response
    
    def _ensure_logged_in(self):
        """Ensure user is logged in, login if not"""
        if not self.jwt_token:
            self.login()
    
    def get_connections(self) -> List[Dict[str, Any]]:
        """
        Get list of connections (patients being followed)
        
        Returns:
            List of connection data dictionaries
        """
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
            # Find by full name
            full_name = self.connection_identifier.lower()
            for conn in connections:
                conn_name = f"{conn.get('firstName', '')} {conn.get('lastName', '')}".lower()
                if conn_name == full_name:
                    return conn['patientId']
            raise Exception(
                f"Unable to identify connection by given name '{self.connection_identifier}'."
            )
        
        if callable(self.connection_identifier):
            # Use function to find connection
            patient_id = self.connection_identifier(connections)
            if not patient_id:
                raise Exception("Unable to identify connection by given function")
            return patient_id
        
        # Default: use first connection
        return connections[0]['patientId']
    
    def read_raw(self) -> Dict[str, Any]:
        """
        Read raw data from LibreLinkUp API
        
        Returns:
            Dictionary containing connection, activeSensors, and graphData
        """
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
    
    def read(self) -> Dict[str, LibreCgmData | List[LibreCgmData]]:
        """
        Read processed CGM data
        
        Returns:
            Dictionary with 'current' (LibreCgmData) and 'history' (List[LibreCgmData])
        """
        raw_data = self.read_raw()
        
        # Map glucose measurement
        glucose_measurement = raw_data.get('connection', {}).get('glucoseMeasurement', {})
        if not glucose_measurement:
            raise Exception("No glucose measurement data available")
        
        # Convert dict to GlucoseItem, handling optional fields
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
    
    def read_averaged(
        self,
        amount: int,
        callback: Callable[[LibreCgmData, List[LibreCgmData], List[LibreCgmData]], None],
        interval: int = 15000
    ) -> Callable:
        """
        Read averaged data over multiple readings
        
        Args:
            amount: Number of readings to collect before calculating average
            callback: Function called when average is calculated.
                     Receives (average, memory, history)
            interval: Interval between readings in milliseconds (default: 15000)
        
        Returns:
            Function to stop the averaging process
        """
        mem: Dict[str, LibreCgmData] = {}
        stop_event = threading.Event()
        timer = None
        
        def collect_data():
            nonlocal mem, timer
            if stop_event.is_set():
                return
            
            try:
                data = self.read()
                current = data['current']
                history = data['history']
                
                mem[current.date.isoformat()] = current
                
                if len(mem) >= amount:
                    mem_values = list(mem.values())
                    
                    # Calculate average value
                    average_value = round(
                        sum(item.value for item in mem_values) / len(mem_values)
                    )
                    
                    # Calculate average trend
                    from .utils import TREND_MAP
                    trend_values = []
                    for item in mem_values:
                        try:
                            idx = list(TrendType).index(item.trend)
                            trend_values.append(idx)
                        except ValueError:
                            trend_values.append(3)  # Default to FLAT
                    
                    avg_trend_index = round(sum(trend_values) / len(trend_values))
                    avg_trend_index = max(0, min(avg_trend_index, len(TREND_MAP) - 1))
                    average_trend = TREND_MAP[avg_trend_index]
                    
                    # Create average data
                    average = LibreCgmData(
                        value=average_value,
                        is_high=current.is_high,
                        is_low=current.is_low,
                        trend=average_trend,
                        date=current.date
                    )
                    
                    # Reset memory
                    mem = {}
                    
                    # Call callback
                    callback(average, mem_values, history)
                
                # Schedule next reading
                if not stop_event.is_set():
                    timer = threading.Timer(interval / 1000.0, collect_data)
                    timer.start()
            except Exception as e:
                print(f"Error in read_averaged: {e}")
                if not stop_event.is_set():
                    timer = threading.Timer(interval / 1000.0, collect_data)
                    timer.start()
        
        def stop():
            """Stop the averaging process"""
            stop_event.set()
            if timer:
                timer.cancel()
        
        # Start collecting
        collect_data()
        
        return stop

