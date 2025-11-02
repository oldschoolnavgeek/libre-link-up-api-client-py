"""Script to export LibreLinkUp readings to CSV file"""

import csv
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
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

def export_readings_to_csv(client: LibreLinkUpClient, filename: Optional[str] = None, num_readings: int = 1000):
    """
    Export glucose readings to CSV file
    
    Args:
        client: LibreLinkUpClient instance
        filename: Output CSV filename (optional, will auto-generate with timestamp if not provided)
        num_readings: Number of readings to export (default: 1000)
    """
    # Generate filename with timestamp if not provided
    if filename is None:
        timestamp = datetime.now(timezone(timedelta(hours=3))).strftime('%Y%m%d_%H%M%S')
        filename = f'libre_readings_{timestamp}.csv'
    
    print(f"Fetching glucose readings...")
    
    # Get data
    data = client.read()
    history = data['history']
    current = data['current']
    
    # Combine current and history, sort by date (oldest first)
    all_readings = history + [current]
    all_readings.sort(key=lambda x: x.date)
    
    # Get last N readings (most recent)
    last_readings = all_readings[-num_readings:] if len(all_readings) > num_readings else all_readings
    
    print(f"✓ Found {len(all_readings)} total readings")
    print(f"✓ Exporting last {len(last_readings)} readings to {filename}")
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Date (GMT+3)', 'Time (GMT+3)', 'Value (mg/dL)', 'Trend', 'Is High', 'Is Low', 'Original GMT Date']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for reading in last_readings:
            # Convert to GMT+3
            dt_gmt3 = convert_to_gmt3(reading.date)
            
            # Format date and time separately
            date_str = dt_gmt3.strftime('%Y-%m-%d')
            time_str = dt_gmt3.strftime('%H:%M:%S')
            
            # Original GMT date for reference
            original_gmt = reading.date.strftime('%Y-%m-%d %H:%M:%S UTC')
            
            writer.writerow({
                'Date (GMT+3)': date_str,
                'Time (GMT+3)': time_str,
                'Value (mg/dL)': reading.value,
                'Trend': reading.trend.value,
                'Is High': 'Yes' if reading.is_high else 'No',
                'Is Low': 'Yes' if reading.is_low else 'No',
                'Original GMT Date': original_gmt
            })
    
    print(f"✓ Successfully exported {len(last_readings)} readings to {filename}")
    print(f"\nFirst reading: {last_readings[0].date} (GMT) → {convert_to_gmt3(last_readings[0].date)} (GMT+3)")
    print(f"Last reading:  {last_readings[-1].date} (GMT) → {convert_to_gmt3(last_readings[-1].date)} (GMT+3)")

def main():
    """Main function"""
    print("=" * 60)
    print("LibreLinkUp CSV Exporter")
    print("=" * 60)
    
    # Load configuration
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        print("❌ config.yaml not found!")
        print("   Please copy config.yaml.example to config.yaml and fill in your credentials")
        return 1
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    libre_config = config.get('libre_link_up', {})
    username = libre_config.get('username')
    password = libre_config.get('password')
    client_version = libre_config.get('client_version', '4.16.0')
    connection_identifier = libre_config.get('connection_identifier')
    
    if not username or not password:
        print("❌ Please set username and password in config.yaml")
        return 1
    
    try:
        # Initialize client
        print("\nInitializing LibreLinkUp Client...")
        client = LibreLinkUpClient(
            username=username,
            password=password,
            client_version=client_version,
            connection_identifier=connection_identifier
        )
        print("✓ Client initialized")
        
        # Export to CSV
        print("\nExporting readings...")
        export_readings_to_csv(client, num_readings=1000)
        
        print("\n" + "=" * 60)
        print("✅ Export completed successfully!")
        print("=" * 60)
        
        return 0
        
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
        
        return 1

if __name__ == '__main__':
    exit(main())

