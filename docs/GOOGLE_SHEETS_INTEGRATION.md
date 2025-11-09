# Google Sheets & Looker Studio Integration Guide

This guide shows how to connect Google Sheets and Looker Studio to the LibreLinkUp REST API.

## Prerequisites

- LibreLinkUp API service deployed and accessible
- API URL (from Cloud Run deployment)
- Google account with access to Google Sheets/Looker Studio

## API Endpoints Reference

Base URL: `https://your-service-url.run.app`

### Available Endpoints

1. **GET /health** - Health check
2. **GET /api/readings** - Query readings
   - Query params: `start_date`, `end_date`, `limit`, `offset`
3. **GET /api/readings/latest** - Get latest reading
4. **GET /api/readings/stats** - Get statistics
   - Query params: `start_date`, `end_date`

### Response Format

**Readings Response:**
```json
{
  "readings": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00",
      "value": 120,
      "trend": "FLAT",
      "is_high": false,
      "is_low": false,
      "created_at": "2024-01-15T10:30:05"
    }
  ],
  "count": 1,
  "limit": 100,
  "offset": 0
}
```

## Method 1: Google Sheets with IMPORTDATA (Simple)

**Limitation:** `IMPORTDATA` only works with CSV files, so this method requires the API to return CSV format. Since our API returns JSON, we'll use Apps Script instead.

## Method 2: Google Sheets with Apps Script (Recommended)

### Step 1: Create Google Apps Script

1. Open Google Sheets
2. Create a new sheet or open an existing one
3. Go to **Extensions** → **Apps Script**
4. Replace the default code with:

```javascript
// Configuration
const API_URL = 'https://your-service-url.run.app';

/**
 * Fetch latest glucose reading
 */
function getLatestReading() {
  try {
    const response = UrlFetchApp.fetch(`${API_URL}/api/readings/latest`);
    const data = JSON.parse(response.getContentText());
    
    return [
      data.timestamp,
      data.value,
      data.trend,
      data.is_high,
      data.is_low
    ];
  } catch (error) {
    return ['Error', error.toString(), '', '', ''];
  }
}

/**
 * Fetch recent readings
 * @param {number} limit - Number of readings to fetch (default: 100)
 * @param {string} startDate - Start date in ISO format (optional)
 * @param {string} endDate - End date in ISO format (optional)
 */
function getReadings(limit = 100, startDate = '', endDate = '') {
  try {
    let url = `${API_URL}/api/readings?limit=${limit}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    
    const response = UrlFetchApp.fetch(url);
    const data = JSON.parse(response.getContentText());
    
    // Return as 2D array for Google Sheets
    return data.readings.map(reading => [
      reading.timestamp,
      reading.value,
      reading.trend,
      reading.is_high,
      reading.is_low
    ]);
  } catch (error) {
    return [['Error', error.toString(), '', '', '']];
  }
}

/**
 * Get statistics for a date range
 * @param {string} startDate - Start date in ISO format (optional)
 * @param {string} endDate - End date in ISO format (optional)
 */
function getStats(startDate = '', endDate = '') {
  try {
    let url = `${API_URL}/api/readings/stats`;
    if (startDate) url += `?start_date=${startDate}`;
    if (endDate) {
      url += startDate ? `&end_date=${endDate}` : `?end_date=${endDate}`;
    }
    
    const response = UrlFetchApp.fetch(url);
    const data = JSON.parse(response.getContentText());
    
    return [
      ['Count', data.count],
      ['Average', data.avg_value || 'N/A'],
      ['Min', data.min_value || 'N/A'],
      ['Max', data.max_value || 'N/A']
    ];
  } catch (error) {
    return [['Error', error.toString()]];
  }
}
```

### Step 2: Use Functions in Sheets

In your Google Sheet, you can now use these functions:

**Get Latest Reading:**
```
=getLatestReading()
```

**Get Recent Readings (last 50):**
```
=getReadings(50)
```

**Get Readings for Date Range:**
```
=getReadings(100, "2024-01-01T00:00:00", "2024-01-31T23:59:59")
```

**Get Statistics:**
```
=getStats("2024-01-01T00:00:00", "2024-01-31T23:59:59")
```

### Step 3: Create a Dashboard Sheet

1. Create a new sheet called "Dashboard"
2. Set up cells like this:

```
A1: Latest Reading
A2: =getLatestReading()

A4: Date Range Statistics
A5: =getStats("2024-01-01T00:00:00", "2024-01-31T23:59:59")

A8: Recent Readings (Last 20)
A9: =getReadings(20)
```

3. Format the data as needed

### Step 4: Set Up Automatic Refresh

1. In Apps Script, go to **Triggers** (clock icon)
2. Click **+ Add Trigger**
3. Configure:
   - Function: `getLatestReading` (or create a refresh function)
   - Event source: **Time-driven**
   - Type: **Minutes timer**
   - Interval: **Every 15 minutes**
4. Save

## Method 3: Google Sheets with QUERY Function (Advanced)

If you want to use the QUERY function, you'll need to convert JSON to a format QUERY can use:

```javascript
/**
 * Get readings as QUERY-compatible format
 */
function getReadingsForQuery(limit = 100) {
  try {
    const response = UrlFetchApp.fetch(`${API_URL}/api/readings?limit=${limit}`);
    const data = JSON.parse(response.getContentText());
    
    // Convert to QUERY format (header row + data rows)
    const header = [['Timestamp', 'Value', 'Trend', 'Is High', 'Is Low']];
    const rows = data.readings.map(r => [
      r.timestamp,
      r.value,
      r.trend,
      r.is_high,
      r.is_low
    ]);
    
    return header.concat(rows);
  } catch (error) {
    return [['Error', error.toString(), '', '', '']];
  }
}
```

Then use:
```
=QUERY(getReadingsForQuery(100), "SELECT * WHERE Col2 > 100 ORDER BY Col1 DESC")
```

## Method 4: Looker Studio Integration

### Option A: Apps Script Connector (Recommended)

1. **Create Apps Script Connector:**

```javascript
// Looker Studio Apps Script Connector
function getConfig() {
  return {
    configParams: [
      {
        type: 'TEXTINPUT',
        name: 'apiUrl',
        displayName: 'API URL',
        helpText: 'Your LibreLinkUp API URL',
        parameterControl: {
          allowOverride: true
        }
      },
      {
        type: 'TEXTINPUT',
        name: 'limit',
        displayName: 'Limit',
        helpText: 'Number of readings to fetch',
        parameterControl: {
          allowOverride: true
        }
      }
    ],
    dateRangeRequired: false
  };
}

function getSchema(request) {
  return {
    schema: [
      {
        name: 'timestamp',
        dataType: 'STRING',
        semantics: {
          conceptType: 'DIMENSION'
        }
      },
      {
        name: 'value',
        dataType: 'NUMBER',
        semantics: {
          conceptType: 'METRIC'
        }
      },
      {
        name: 'trend',
        dataType: 'STRING',
        semantics: {
          conceptType: 'DIMENSION'
        }
      },
      {
        name: 'is_high',
        dataType: 'BOOLEAN',
        semantics: {
          conceptType: 'DIMENSION'
        }
      },
      {
        name: 'is_low',
        dataType: 'BOOLEAN',
        semantics: {
          conceptType: 'DIMENSION'
        }
      }
    ]
  };
}

function getData(request) {
  const apiUrl = request.configParams.apiUrl || 'https://your-service-url.run.app';
  const limit = request.configParams.limit || 100;
  
  try {
    const url = `${apiUrl}/api/readings?limit=${limit}`;
    const response = UrlFetchApp.fetch(url);
    const data = JSON.parse(response.getContentText());
    
    const rows = data.readings.map(reading => ({
      values: [
        reading.timestamp,
        reading.value,
        reading.trend,
        reading.is_high,
        reading.is_low
      ]
    }));
    
    return {
      schema: getSchema(request).schema,
      rows: rows
    };
  } catch (error) {
    throw new Error('Failed to fetch data: ' + error.toString());
  }
}
```

2. **Deploy as Looker Studio Connector:**
   - In Apps Script, go to **Deploy** → **New deployment**
   - Type: **Looker Studio add-on**
   - Click **Deploy**
   - Copy the connector ID

3. **Use in Looker Studio:**
   - Open Looker Studio
   - Create new data source
   - Select **Community Connectors** → **Looker Studio Developer Connector**
   - Enter your connector ID
   - Configure API URL and other parameters
   - Connect

### Option B: Web Connector (Simple)

1. In Looker Studio, create a new data source
2. Select **Web Connector** (or **URL**)
3. Enter your API endpoint URL:
   ```
   https://your-service-url.run.app/api/readings?limit=1000
   ```
4. Looker Studio will attempt to parse the JSON
5. Map fields as needed

**Note:** This method may require JSON transformation depending on Looker Studio's parser.

## Method 5: Scheduled Data Import (Most Reliable)

For production use, consider setting up a scheduled import:

1. **Create a Google Apps Script** that runs on a schedule
2. **Fetch data from API** and write to a Google Sheet
3. **Use that sheet** as the data source for Looker Studio

```javascript
/**
 * Scheduled function to import readings to sheet
 */
function importReadingsToSheet() {
  const API_URL = 'https://your-service-url.run.app';
  const SHEET_NAME = 'Readings Data';
  
  try {
    // Get or create sheet
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(SHEET_NAME);
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
      // Add headers
      sheet.getRange(1, 1, 1, 5).setValues([['Timestamp', 'Value', 'Trend', 'Is High', 'Is Low']]);
    }
    
    // Fetch data
    const response = UrlFetchApp.fetch(`${API_URL}/api/readings?limit=1000`);
    const data = JSON.parse(response.getContentText());
    
    // Convert to 2D array
    const rows = data.readings.map(r => [
      r.timestamp,
      r.value,
      r.trend,
      r.is_high,
      r.is_low
    ]);
    
    // Clear old data (keep headers)
    const lastRow = sheet.getLastRow();
    if (lastRow > 1) {
      sheet.getRange(2, 1, lastRow - 1, 5).clear();
    }
    
    // Write new data
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, 5).setValues(rows);
    }
    
    Logger.log(`Imported ${rows.length} readings`);
  } catch (error) {
    Logger.log('Error importing readings: ' + error.toString());
  }
}
```

Set up a trigger to run this every 15 minutes.

## Security Considerations

### Add API Authentication (Optional)

If you want to secure your API:

1. **Enable authentication in Cloud Run:**
   ```bash
   gcloud run services update librelinkup-api \
       --region=$REGION \
       --no-allow-unauthenticated
   ```

2. **Use service account in Apps Script:**
   ```javascript
   function getAuthToken() {
     // Use OAuth2 or service account
     // This requires additional setup
   }
   ```

3. **Add API key authentication:**
   - Add API key validation in your API
   - Pass API key in headers from Apps Script

## Example: Complete Dashboard Setup

### Google Sheet Structure

**Sheet 1: Dashboard**
- Latest reading with formatting
- Statistics summary
- Trend indicators

**Sheet 2: Readings Data**
- Full readings table (populated by scheduled script)
- Can be used as Looker Studio data source

**Sheet 3: Charts**
- Time series chart of glucose values
- Trend analysis
- High/Low alerts

### Apps Script Functions

```javascript
// Complete example with error handling and caching
const API_URL = 'https://your-service-url.run.app';
const CACHE_DURATION = 60; // seconds

function getCachedData(cacheKey, fetchFunction) {
  const cache = CacheService.getScriptCache();
  const cached = cache.get(cacheKey);
  
  if (cached) {
    return JSON.parse(cached);
  }
  
  const data = fetchFunction();
  cache.put(cacheKey, JSON.stringify(data), CACHE_DURATION);
  return data;
}

function getLatestReading() {
  return getCachedData('latest', () => {
    const response = UrlFetchApp.fetch(`${API_URL}/api/readings/latest`);
    return JSON.parse(response.getContentText());
  });
}
```

## Troubleshooting

### Common Issues

1. **"Script function not found"**
   - Make sure function name matches exactly
   - Check that Apps Script is saved

2. **"Request failed"**
   - Verify API URL is correct
   - Check that API is accessible (test in browser)
   - Verify no authentication required

3. **"Execution timeout"**
   - Reduce limit parameter
   - Add caching (see example above)
   - Use scheduled import instead of real-time

4. **"Data not updating"**
   - Check trigger is set up correctly
   - Verify API is returning new data
   - Clear cache if using caching

## Next Steps

- Set up automated alerts for high/low glucose
- Create custom charts and visualizations
- Export data to other formats
- Set up data retention policies

