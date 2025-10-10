# Campsite Checker - Lambda Version

## 🏕️ Overview

This is a serverless AWS Lambda function that automatically monitors recreation.gov campsites and sends notifications via Pushover when sites become available. The Lambda version is designed for scheduled, hands-off campsite monitoring.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   EventBridge   │───▶│    Lambda    │───▶│    Pushover     │
│   (Schedule)    │    │  (Campbot)   │    │ (Notifications) │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │      S3      │
                       │   (Config)   │
                       └──────────────┘
```

## 📋 How It Works

1. **EventBridge** triggers Lambda on schedule (e.g., every 30 minutes)
2. **Lambda** loads search configurations from S3
3. **Lambda** calls recreation.gov API for each enabled search
4. **Lambda** sends Pushover notifications **only when campsites are found**
5. **Lambda** returns execution summary with results

## ⚙️ Configuration

### Search Configuration File (`campsite_searches.json`)

Store your search criteria in S3 as a JSON file:

```json
{
  "version": "1.0",
  "description": "Campsite monitoring configuration",
  "notification_settings": {
    "only_notify_on_availability": true,
    "include_search_name_in_notification": true
  },
  "searches": [
    {
      "name": "Yosemite Valley 4th of July Weekend",
      "enabled": true,
      "parks": ["232448"],
      "start_date": "2025-07-04",
      "end_date": "2025-07-06",
      "campsite_type": null,
      "campsite_ids": [],
      "nights": 2,
      "weekends_only": false,
      "priority": "high"
    },
    {
      "name": "Joshua Tree October",
      "enabled": true,
      "parks": ["232472"],
      "start_date": "2025-10-14",
      "end_date": "2025-10-16",
      "campsite_type": "STANDARD NONELECTRIC",
      "campsite_ids": [3511, 3512, 3513],
      "nights": 2,
      "weekends_only": false,
      "priority": "normal"
    },
    {
      "name": "Multiple Parks Labor Day",
      "enabled": true,
      "parks": ["232448", "232449", "232472"],
      "start_date": "2025-09-01",
      "end_date": "2025-09-03",
      "campsite_type": null,
      "campsite_ids": [],
      "nights": 2,
      "weekends_only": false,
      "priority": "high"
    }
  ]
}
```

### Search Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Descriptive name for the search (appears in notifications) |
| `enabled` | boolean | ✅ | Whether to process this search |
| `parks` | array[string] | ✅ | List of recreation.gov park IDs to check |
| `start_date` | string | ✅ | Start date in YYYY-MM-DD format |
| `end_date` | string | ✅ | End date in YYYY-MM-DD format |
| `campsite_type` | string | ❌ | Filter by specific campsite type (e.g., "STANDARD NONELECTRIC") |
| `campsite_ids` | array[int] | ❌ | Filter by specific campsite IDs |
| `nights` | int | ❌ | Required consecutive nights (defaults to date range) |
| `weekends_only` | boolean | ❌ | Only check weekend dates |
| `priority` | string | ❌ | "high" or "normal" - affects notification priority |

## 🔍 Finding Park IDs

Park IDs can be found in recreation.gov URLs:
- Yosemite Valley: `https://www.recreation.gov/camping/campgrounds/232448` → ID: `232448`
- Joshua Tree Indian Cove: `https://www.recreation.gov/camping/campgrounds/232472` → ID: `232472`

## 📱 Notification System

### When Notifications Are Sent

The Lambda function **only sends notifications when**:
- ✅ Campsites become available matching your criteria
- ❌ Errors occur during execution
- 🚨 Critical system failures

**No notifications are sent** when no campsites are available (silent operation).

### Notification Format

**Success Notification:**
```
🎉 FOUND: Yosemite Valley 4th of July Weekend

there are campsites available from 2025-07-04 to 2025-07-06!!! 🏕🏕🏕

12 site(s) available in Yosemite Valley Campground

🏕 Book now! 🏕
```

**Error Notification:**
```
🚨 Error checking 'Joshua Tree October': 
Recreation.gov API temporarily unavailable
```

### Notification Priority

- **High Priority** (`priority: "high"`): Immediate notification with sound
- **Normal Priority** (`priority: "normal"`): Standard notification
- **Error Priority**: Always high priority

## 🎛️ Lambda Event Structure

The Lambda function accepts these event parameters:

### Scheduled Execution (Normal)
```json
{}
```
*Uses S3 configuration file for all searches*

### Custom Message
```json
{
  "message": "Test notification from campbot!"
}
```

### Single Search Override
```json
{
  "check_camping": true,
  "parks": ["232472"],
  "start_date": "2025-10-14",
  "end_date": "2025-10-15"
}
```

## 📊 Execution Response

### Success Response
```json
{
  "statusCode": 200,
  "body": {
    "message": "Campsite monitoring completed",
    "total_searches": 3,
    "availabilities_found": 1,
    "notifications_sent": 1,
    "results": [
      {
        "search_name": "Yosemite Valley 4th of July Weekend",
        "has_availabilities": false,
        "parks": ["232448"],
        "date_range": "2025-07-04 to 2025-07-06"
      },
      {
        "search_name": "Joshua Tree October", 
        "has_availabilities": true,
        "notification_sent": true,
        "parks": ["232472"],
        "date_range": "2025-10-14 to 2025-10-16",
        "pushover_response": {"status": 1, "request": "abc123"}
      }
    ]
  }
}
```

### Error Response
```json
{
  "statusCode": 500,
  "body": {
    "error": "Failed to load search configuration from S3",
    "message": "Critical lambda failure"
  }
}
```

## 🚨 Error Handling

### Configuration Errors
- **Missing S3 file**: Sends error notification, returns 500
- **Invalid JSON**: Sends error notification, returns 500
- **Missing required fields**: Skips invalid searches, continues with valid ones

### API Errors
- **Recreation.gov timeout**: Retries once, then reports error
- **Invalid park ID**: Skips park, continues with other parks
- **Rate limiting**: Waits and retries

### System Errors
- **Lambda timeout**: Partial results returned, remaining searches skipped
- **Memory limit**: Critical error notification sent
- **Network issues**: Error notification with details

## 📈 Performance & Limits

### Execution Times
- **Simple notification**: ~1 second
- **Single park check**: ~3-5 seconds  
- **Multiple parks**: ~10-15 seconds
- **Complex searches**: ~20-30 seconds

### Recommended Limits
- **Max parks per search**: 5 parks
- **Max total searches**: 10 searches
- **Check frequency**: Every 15-30 minutes
- **Lambda timeout**: 60 seconds
- **Lambda memory**: 256 MB

## 🔧 Configuration Management

### Updating Searches
1. Edit `campsite_searches.json` locally
2. Upload to S3: `aws s3 cp campsite_searches.json s3://your-bucket/`
3. Changes take effect on next scheduled run (no Lambda redeployment needed)

### Environment Variables
- `PUSHOVER_USER_KEY`: Your Pushover user key
- `PUSHOVER_API_TOKEN`: Your Pushover app token  
- `CONFIG_BUCKET`: S3 bucket name containing configuration

### Schedule Management
EventBridge rules control when Lambda runs:
- `rate(30 minutes)` - Every 30 minutes
- `rate(1 hour)` - Every hour
- `cron(0 8,20 * * ? *)` - 8am and 8pm daily

## 🔍 Monitoring & Debugging

### CloudWatch Logs
All execution details are logged to `/aws/lambda/campbot`:
```
Processing search: Yosemite Valley 4th of July Weekend
Checking park 1/1 (232448) with 45000ms remaining
Real camping check result: No availability found
No notification sent for: Yosemite Valley 4th of July Weekend
```

### Common Log Messages
- `"Processing search: [name]"` - Starting a search
- `"Found availability: true/false"` - Search results
- `"Notification sent: [title]"` - Pushover notification sent
- `"Skipping remaining parks due to time limit"` - Lambda timeout protection

### Troubleshooting
1. **No notifications**: Check search criteria and date ranges
2. **Timeout errors**: Reduce number of parks or increase Lambda timeout
3. **S3 errors**: Verify bucket permissions and file exists
4. **API errors**: Check recreation.gov status and park IDs

## 💰 Cost Estimation

**Monthly costs** (30-minute checks):
- Lambda executions: ~$0.50
- S3 storage: ~$0.01  
- EventBridge: ~$0.10
- Pushover: Free (500 notifications/month)
- **Total**: ~$0.61/month

## 🎯 Best Practices

### Search Strategy
- ✅ **Specific dates**: Better than broad date ranges
- ✅ **Popular parks**: Check more frequently (every 15 minutes)
- ✅ **Backup dates**: Include multiple date options
- ✅ **Flexible criteria**: Don't over-constrain campsite types

### Configuration Tips
- 🔧 **Disable unused searches**: Set `"enabled": false`
- 🔧 **Descriptive names**: Help identify notifications
- 🔧 **High priority sparingly**: Only for must-have trips
- 🔧 **Test before deploying**: Use custom messages first

### Monitoring Tips
- 📊 **Check CloudWatch logs** weekly
- 📊 **Monitor notification frequency** 
- 📊 **Verify searches run successfully**
- 📊 **Update date ranges** as trips approach

## 🔗 Related Files

- `lambda_function_production.py` - Main Lambda function code
- `campsite_searches.json` - Search configuration template
- `DEPLOYMENT_GUIDE.md` - AWS deployment instructions
- `LOCAL_TESTING.md` - Local development guide
