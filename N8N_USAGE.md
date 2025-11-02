# Using LibreLinkUp JSON Exporter in n8n

## Overview

The `export_to_json_n8n.py` script outputs JSON data that n8n can easily process.
**No need for config.yaml in n8n!** The script supports multiple configuration methods.

## Configuration Methods (Priority Order)

### 1. Environment Variables (Recommended for n8n)

Set these environment variables in n8n:

- `LIBRE_USERNAME` - Your LibreLinkUp email
- `LIBRE_PASSWORD` - Your LibreLinkUp password
- `LIBRE_CLIENT_VERSION` - Optional (default: "4.16.0")
- `LIBRE_NUM_READINGS` - Optional (default: 1000)
- `LIBRE_CONNECTION_IDENTIFIER` - Optional (null or patient name)

### 2. JSON Input from stdin (For Code Node)

Pass JSON via stdin with credentials.

### 3. config.yaml File (Fallback)

Only used if environment variables or JSON input are not provided (for local testing).

## Usage in n8n

### Method 1: Execute Command Node (Recommended)

**Step 1:** Add an **Execute Command** node

**Step 2:** Set environment variables in the node:
- Go to **Options** → **Environment Variables**
- Add:
  ```
  LIBRE_USERNAME = your-email@example.com
  LIBRE_PASSWORD = your-password
  LIBRE_NUM_READINGS = 1000
  ```

**Step 3:** Set command:
```bash
cd /path/to/libre-link-up-api-client-py && source venv/bin/activate && python export_to_json_n8n.py
```

**Step 4:** The JSON output will be in `$output.stdout`

### Method 2: Code Node with Environment Variables

**Step 1:** Add a **Set** node before Code node to set environment variables:
```json
{
  "LIBRE_USERNAME": "your-email@example.com",
  "LIBRE_PASSWORD": "your-password",
  "LIBRE_NUM_READINGS": "1000"
}
```

**Step 2:** Add **Execute Command** node (or **Code** node with subprocess)

### Method 3: Code Node with Direct Input

You can also pass credentials directly in a Code node:

```python
import subprocess
import json
import os

# Set environment variables from n8n workflow variables
os.environ['LIBRE_USERNAME'] = '{{ $env.LIBRE_USERNAME }}'
os.environ['LIBRE_PASSWORD'] = '{{ $env.LIBRE_PASSWORD }}'
os.environ['LIBRE_NUM_READINGS'] = '1000'

# Execute script
result = subprocess.run(
    ['python', '/path/to/export_to_json_n8n.py'],
    capture_output=True,
    text=True,
    cwd='/path/to/libre-link-up-api-client-py'
)

# Parse and return
data = json.loads(result.stdout)

# Return items - one per reading
items = []
for reading in data.get('readings', []):
    items.append({'json': reading})

return items
```

### Method 4: Using n8n Workflow Variables

In n8n workflow settings, add:
- `LIBRE_USERNAME`
- `LIBRE_PASSWORD`

These will be available as environment variables automatically.

## Output Format

```json
{
  "success": true,
  "count": 48,
  "readings": [
    {
      "datetime": "2025-10-31 10:37:13",
      "date": "2025-10-31",
      "time": "10:37:13",
      "timestamp": 1761896233,
      "value": 8.3,
      "value_mgdl": 8.3,
      "trend": "Flat",
      "is_high": false,
      "is_low": false,
      "gmt_datetime": "2025-10-31 07:37:13 UTC"
    }
  ],
  "metadata": {
    "first_reading": "2025-10-31 10:37:13",
    "last_reading": "2025-10-31 22:08:33",
    "timezone": "GMT+3",
    "export_time": "2025-10-31 22:15:00"
  }
}
```

## Security Notes

✅ **DO:** Use n8n workflow variables or environment variables for credentials
❌ **DON'T:** Hardcode credentials in the script
✅ **DO:** Use n8n's credential management features

## Data Fields

Each reading contains:

- `datetime`: Full datetime string in GMT+3 (YYYY-MM-DD HH:MM:SS)
- `date`: Date only in GMT+3 (YYYY-MM-DD)
- `time`: Time only in GMT+3 (HH:MM:SS)
- `timestamp`: Unix timestamp (seconds since epoch)
- `value`: Glucose value in mg/dL
- `value_mgdl`: Same as value (alias)
- `trend`: Trend direction (Flat, SingleUp, SingleDown, etc.)
- `is_high`: Boolean - is value above normal range?
- `is_low`: Boolean - is value below normal range?
- `gmt_datetime`: Original GMT time for reference

## Example n8n Workflow

1. **Schedule Trigger** - Run every 15 minutes
2. **Set Node** - Set environment variables (or use workflow variables)
3. **Execute Command Node** - Run the script
4. **Code Node** - Parse JSON and process readings
5. **HTTP Request** - Send to your database/API

## Testing Locally

For local testing, you can still use `config.yaml`:

```yaml
libre_link_up:
  username: "your-email@example.com"
  password: "your-password"
  client_version: "4.16.0"
  connection_identifier: null
  num_readings: 1000
```

The script will use it if environment variables are not set.
