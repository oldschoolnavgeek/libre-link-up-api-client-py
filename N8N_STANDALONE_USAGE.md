# Using Standalone Script in n8n Cloud

## File: `libre_link_up_n8n_standalone.py`

This is a **single, self-contained Python file** - no external modules needed except `requests` and `urllib3` (which are typically available in n8n).

## Required Dependencies

The script only needs:
- `requests` - HTTP client library
- `urllib3` - Used by requests

These are usually pre-installed in n8n's Python environment, but if not, you can add them in n8n's code node.

## Configuration

Set these **environment variables** in n8n (no config files needed!):

### Required:
- `LIBRE_USERNAME` - Your LibreLinkUp email address
- `LIBRE_PASSWORD` - Your LibreLinkUp password

### Optional:
- `LIBRE_NUM_READINGS` - Number of readings to export (default: 1000)
- `LIBRE_CLIENT_VERSION` - Client version (default: "4.16.0")
- `LIBRE_CONNECTION_IDENTIFIER` - Patient name or "null" (default: null = use first connection)

## Usage in n8n Cloud

### Method 1: Code Node (Recommended for n8n Cloud)

1. **Add a Code node** (Python)
2. **Copy the entire contents** of `libre_link_up_n8n_standalone.py` into the code editor
3. **Set environment variables** in n8n workflow settings or use workflow variables
4. **Run** - The script will output JSON to stdout, which n8n captures

Example Code node setup:
```python
# The entire script content goes here
# ... (copy all code from libre_link_up_n8n_standalone.py)

# The script will automatically read from environment variables
# and output JSON
```

### Method 2: Execute Command Node (If Python available)

1. **Upload the file** to your n8n server or use inline script
2. **Set environment variables** in the Execute Command node options
3. **Command:**
   ```bash
   python /path/to/libre_link_up_n8n_standalone.py
   ```
4. **Capture output** from `$output.stdout`

### Method 3: Inline Script in Code Node

You can also set variables directly in the code:

```python
import os
import json

# Set credentials (or use workflow variables)
os.environ['LIBRE_USERNAME'] = '{{ $env.LIBRE_USERNAME }}'
os.environ['LIBRE_PASSWORD'] = '{{ $env.LIBRE_PASSWORD }}'
os.environ['LIBRE_NUM_READINGS'] = '1000'

# Then copy the entire script code here
# ... (all code from libre_link_up_n8n_standalone.py)
```

## Output Format

The script outputs JSON with this structure:

```json
{
  "success": true,
  "count": 5,
  "readings": [
    {
      "datetime": "2025-10-31 22:36:41",
      "date": "2025-10-31",
      "time": "22:36:41",
      "timestamp": 1761939401,
      "value": 12.8,
      "value_mgdl": 12.8,
      "trend": "Flat",
      "is_high": false,
      "is_low": false,
      "gmt_datetime": "2025-10-31 19:36:41 UTC"
    }
  ],
  "metadata": {
    "first_reading": "2025-10-31 21:25:24",
    "last_reading": "2025-10-31 22:36:41",
    "timezone": "GMT+3",
    "export_time": "2025-10-31 22:37:08"
  }
}
```

## Key Features

✅ **Single file** - No module imports needed
✅ **Environment variables** - No config files
✅ **GMT+3 conversion** - All datetimes converted automatically
✅ **Error handling** - Returns JSON error messages
✅ **Self-contained** - All code in one file

## Data Fields

Each reading contains:
- `datetime`: Full datetime in GMT+3 (YYYY-MM-DD HH:MM:SS)
- `date`: Date only (YYYY-MM-DD)
- `time`: Time only (HH:MM:SS)
- `timestamp`: Unix timestamp
- `value`: Glucose value in mg/dL
- `value_mgdl`: Same as value
- `trend`: Trend direction (Flat, SingleUp, etc.)
- `is_high`: Boolean
- `is_low`: Boolean
- `gmt_datetime`: Original GMT time for reference

## Testing Locally

```bash
export LIBRE_USERNAME="your-email@example.com"
export LIBRE_PASSWORD="your-password"
export LIBRE_NUM_READINGS="10"
python libre_link_up_n8n_standalone.py
```

## Notes

- All datetime values are converted from GMT to GMT+3
- The script uses the Russian endpoint (`api.libreview.ru`) by default
- If your account requires a different region, it will auto-redirect
- No external dependencies except `requests` and `urllib3`

