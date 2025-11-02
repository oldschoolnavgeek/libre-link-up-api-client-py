"""Example usage of LibreLinkUp API Client"""

import yaml
from pathlib import Path
from libre_link_up_client import LibreLinkUpClient

# Load configuration
config_path = Path(__file__).parent / 'config.yaml'
if not config_path.exists():
    print("❌ config.yaml not found!")
    print("   Please copy config.yaml.example to config.yaml and fill in your credentials")
    exit(1)

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

libre_config = config.get('libre_link_up', {})
username = libre_config.get('username')
password = libre_config.get('password')
client_version = libre_config.get('client_version', '4.12.0')
connection_identifier = libre_config.get('connection_identifier')

if not username or not password:
    print("❌ Please set username and password in config.yaml")
    exit(1)

# Initialize client
print("Initializing LibreLinkUp Client...")
client = LibreLinkUpClient(
    username=username,
    password=password,
    client_version=client_version,
    connection_identifier=connection_identifier
)

try:
    # Example 1: Read current glucose reading
    print("\n=== Reading current CGM data ===")
    data = client.read()
    current = data['current']
    history = data['history']
    
    print(f"\n📊 Current Reading:")
    print(f"  Value: {current.value} mg/dL")
    print(f"  Trend: {current.trend.value}")
    print(f"  High: {'⚠️ YES' if current.is_high else '✓ No'}")
    print(f"  Low: {'⚠️ YES' if current.is_low else '✓ No'}")
    print(f"  Date: {current.date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if history:
        print(f"\n📈 History: {len(history)} readings available")
        print("Last 5 readings:")
        for i, reading in enumerate(history[-5:], 1):
            print(f"  {i}. {reading}")
    
    # Example 2: Read raw data
    print("\n=== Reading raw data ===")
    raw_data = client.read_raw()
    connection = raw_data.get('connection', {})
    print(f"  Patient: {connection.get('firstName', '')} {connection.get('lastName', '')}")
    print(f"  Active sensors: {len(raw_data.get('activeSensors', []))}")
    print(f"  Graph data points: {len(raw_data.get('graphData', []))}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    
    error_msg = str(e)
    if 'Bad credentials' in error_msg:
        print("\n⚠️  Make sure you are using LibreLinkUp credentials,")
        print("   not LibreLink credentials. These are different accounts!")
    elif 'Additional action required' in error_msg:
        print("\n⚠️  Please login via the LibreLinkUp app first")
        print("   and complete any required authentication steps.")
    elif 'follow any patients' in error_msg:
        print("\n⚠️  You need to be following at least one patient")
        print("   in the LibreLinkUp app.")
    
    exit(1)

