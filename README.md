# LibreLinkUp API Client (Python)

Python client for accessing Abbott's LibreLinkUp sharing service to retrieve Continuous Glucose Monitor (CGM) data.

This is a Python port of the [libre-link-up-api-client](https://github.com/DiaKEM/libre-link-up-api-client) library.

## Features

- 🔐 Automatic authentication and session management
- 📊 Read current glucose readings
- 📈 Access historical glucose data
- 🔄 Support for multiple connections/patients
- ⚙️ Configurable via YAML configuration file
- 🎯 Type-safe with dataclasses and enums

## Prerequisites

- Python 3.8 or higher
- LibreLinkUp account credentials (not LibreLink!)

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example configuration file:
```bash
cp config.yaml.example config.yaml
```

2. Edit `config.yaml` with your credentials:
```yaml
libre_link_up:
  username: "your-email@example.com"
  password: "your-password"
  client_version: "4.12.0"  # Optional
  connection_identifier: null  # Optional: patient name or null for first
```

## Usage

### Basic Example

```python
from libre_link_up_client import LibreLinkUpClient

# Initialize client
client = LibreLinkUpClient(
    username="your-email@example.com",
    password="your-password"
)

# Read current reading and history
data = client.read()
current = data['current']
history = data['history']

print(f"Current: {current.value} mg/dL")
print(f"Trend: {current.trend.value}")
print(f"History: {len(history)} readings")
```

### Using Configuration File

```python
import yaml
from libre_link_up_client import LibreLinkUpClient

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

libre_config = config['libre_link_up']
client = LibreLinkUpClient(
    username=libre_config['username'],
    password=libre_config['password']
)

data = client.read()
```

### Run Example Script

```bash
python example_usage.py
```

## API Methods

### `read()`

Get current reading and history:

```python
data = client.read()
current = data['current']      # LibreCgmData object
history = data['history']      # List of LibreCgmData objects
```

### `read_raw()`

Get raw API response:

```python
raw_data = client.read_raw()
# Returns dict with:
# - connection: Patient/connection information
# - activeSensors: List of active sensors
# - graphData: List of raw glucose measurements
```

### `read_averaged()`

Collect multiple readings and calculate average:

```python
def callback(average, memory, history):
    print(f"Average: {average.value} mg/dL")
    print(f"Based on {len(memory)} readings")

stop = client.read_averaged(
    amount=5,           # Number of readings to collect
    callback=callback,  # Function called when average is calculated
    interval=15000      # Interval in milliseconds (default: 15000)
)

# Later, to stop:
stop()
```

## Data Structures

### LibreCgmData

```python
@dataclass
class LibreCgmData:
    value: int           # Glucose value in mg/dL
    is_high: bool        # Is value above normal range?
    is_low: bool         # Is value below normal range?
    trend: TrendType    # Trend direction (enum)
    date: datetime       # Timestamp of the reading
```

### TrendType

Enum values:
- `SINGLE_DOWN`
- `FORTY_FIVE_DOWN`
- `FLAT`
- `FORTY_FIVE_UP`
- `SINGLE_UP`
- `NOT_COMPUTABLE`

## Multiple Connections

If you follow multiple patients, specify which one to use:

```python
# By name
client = LibreLinkUpClient(
    username="email@example.com",
    password="password",
    connection_identifier="John Doe"
)

# Or use a function
def select_connection(connections):
    for conn in connections:
        if conn['firstName'] == 'John':
            return conn['patientId']
    return None

client = LibreLinkUpClient(
    username="email@example.com",
    password="password",
    connection_identifier=select_connection
)
```

## Error Handling

The client will raise exceptions for various error conditions:

- **Bad credentials**: Wrong username/password
- **Additional action required**: Need to complete steps in LibreLinkUp app
- **No patients followed**: Account doesn't follow any patients
- **HTTP errors**: Network or API issues

## Notes

- The client automatically handles login and session management
- If your session expires, the client will automatically re-authenticate
- The API uses regional endpoints - the client will automatically redirect if needed
- Be respectful of the API and don't poll too frequently

## License

MIT License - Same as the original TypeScript implementation

## Credits

Based on the [libre-link-up-api-client](https://github.com/DiaKEM/libre-link-up-api-client) by DiaKEM.

## Disclaimer

This is an unofficial client and is not affiliated with or endorsed by Abbott. Use at your own risk.

