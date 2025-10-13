# Campsite Checker - Multi-User Lambda System

## 🏕️ Overview

This is a serverless AWS Lambda system with **two separate functions** that automatically monitors recreation.gov campsites for multiple users and sends notifications via Telegram. The system supports individual user configurations and multi-user management through a Telegram bot interface.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   EventBridge   │───▶│ Campsite Checker │───▶│     Telegram        │
│   (Schedule)    │    │     Lambda       │    │   (Notifications)   │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                                │                          ▲
                                ▼                          │
                       ┌──────────────┐           ┌──────────┴───────┐
                       │      S3      │           │ Telegram Bot     │
                       │ Per-User     │◀──────────│    Lambda        │
                       │  Configs     │           │  (User Commands) │
                       └──────────────┘           └──────────────────┘
                                                           ▲
                                                           │
                                                  ┌──────────────┐
                                                  │   Telegram   │
                                                  │   Webhook    │
                                                  └──────────────┘
```

## 📋 How It Works

### Two-Lambda System

#### Campsite Checker Lambda (Scheduled)
1. **EventBridge** triggers the Campsite Checker Lambda on schedule (e.g., every 30 minutes)
2. **Lambda** loads all user configurations from S3 (`users/telegram_{user_id}.json`)
3. **Lambda** processes each user's enabled searches, calling recreation.gov API
4. **Lambda** sends Telegram notifications **only when campsites are found** or errors occur
5. **Lambda** returns execution summary with results across all users

#### Telegram Bot Lambda (On-Demand)
1. **Telegram webhook** triggers the Telegram Bot Lambda when users send commands
2. **Lambda** processes user commands (`/add`, `/list`, `/check`, etc.)
3. **Lambda** manages per-user configurations in S3
4. **Lambda** can invoke the Campsite Checker Lambda for manual checks
5. **Lambda** responds to users with command results via Telegram

## ⚙️ Configuration

### Per-User Configuration System

Each Telegram user has their own configuration file stored in S3 at `users/telegram_{user_id}.json`. Users manage their searches through Telegram bot commands rather than manually editing JSON files.

#### User Configuration Structure
```json
{
  "version": "1.0",
  "user_id": "123456789",
  "notification_settings": {
    "telegram_enabled": true,
    "pushover_enabled": false,
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
      "priority": "high",
      "created_at": "2025-01-15T10:30:00"
    }
  ]
}
```

### Legacy Single-User Configuration (Optional)

For backward compatibility, the system still supports a global `campsite_searches.json` configuration file when running in legacy mode:

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

## 🤖 Telegram Bot Commands

### User Management Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome message and help | `/start` |
| `/help` | Show available commands | `/help` |
| `/add` | Add new campsite search | `/add "Yosemite Trip" 2025-07-04 2025-07-06 232448` |
| `/list` | Show your active searches | `/list` |
| `/toggle` | Enable/disable a search | `/toggle Yosemite Trip` |
| `/delete` | Remove a search | `/delete Yosemite Trip` |
| `/check` | Manually check all searches | `/check` |

### Adding Searches via Telegram

**Format:** `/add "Search Name" start_date end_date park`

**Examples:**
- `/add "Yosemite Valley July" 2025-07-04 2025-07-06 232448`
- `/add "Joshua Tree Weekend" 2025-10-15 2025-10-17 joshua tree`
- `/add "Grand Canyon" 2025-08-01 2025-08-03 https://www.recreation.gov/camping/campgrounds/232266`

**Popular Parks:**
- Yosemite Valley: `232448` or `yosemite`
- Joshua Tree Indian Cove: `232472` or `joshua tree`
- Grand Canyon Mather: `232266` or `grand canyon`

### Automatic Configuration Creation

When a new user starts using the bot:
1. **User sends `/start`** to the Telegram bot
2. **Bot creates** a new S3 configuration file at `users/telegram_{user_id}.json`
3. **Default settings** are applied (Telegram notifications enabled)
4. **User can immediately** start adding searches with `/add`

## 📱 Notification System

### Multi-User Telegram Notifications

The system **sends notifications via Telegram** to each user individually when:
- ✅ Campsites become available matching their criteria
- ❌ Errors occur during their search execution
- 🚨 System failures affecting their monitoring

**No notifications are sent** when no campsites are available (silent operation).

### Notification Format

**Success Notification (Telegram):**
```
🎉 FOUND: Yosemite Valley 4th of July Weekend

there are campsites available from 2025-07-04 to 2025-07-06!!! 🏕🏕🏕

12 site(s) available in Yosemite Valley Campground

🏕 Book now! 🏕
```

**Manual Check Summary:**
```
✅ Manual Check Complete!

🎉 Found availability in 1 of 3 searches!

Detailed results were sent above. 🏕️
```

**Error Notification:**
```
🚨 Error checking 'Joshua Tree October': 
Recreation.gov API temporarily unavailable
```

### Legacy Pushover Support

The system maintains backward compatibility with Pushover notifications for users who enable it in their notification settings.

## 🎛️ Lambda Event Structures

### Campsite Checker Lambda Events

#### Scheduled Multi-User Monitoring (Normal)
```json
{
  "multi_user_mode": true,
  "config_bucket": "your-campbot-config-bucket"
}
```
*Processes all user configurations automatically*

#### Manual Check Request (from Telegram Bot)
```json
{
  "manual_check": true,
  "user_id": "123456789",
  "telegram_chat_id": "123456789",
  "telegram_bot_token": "bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
}
```

#### Legacy Single-User Mode
```json
{
  "multi_user_mode": false,
  "config_bucket": "your-config-bucket",
  "config_key": "campsite_searches.json"
}
```

### Telegram Bot Lambda Events

#### Webhook Message (from Telegram)
```json
{
  "body": "{\"update_id\":123,\"message\":{\"message_id\":456,\"from\":{\"id\":123456789,\"first_name\":\"John\"},\"chat\":{\"id\":123456789},\"text\":\"/add \\\"Yosemite Trip\\\" 2025-07-04 2025-07-06 232448\"}}"
}
```

#### Direct Command (for testing)
```json
{
  "message": "Test notification from campbot!"
}
```

## 📊 Execution Responses

### Campsite Checker Lambda Responses

#### Multi-User Success Response
```json
{
  "statusCode": 200,
  "body": {
    "message": "Campsite monitoring completed",
    "mode": "multi-user",
    "users_processed": 3,
    "total_searches": 7,
    "availabilities_found": 1,
    "notifications_sent": 1,
    "results": [
      {
        "search_name": "Yosemite Valley 4th of July Weekend",
        "user_id": "123456789",
        "has_availabilities": false,
        "parks": ["232448"],
        "date_range": "2025-07-04 to 2025-07-06"
      },
      {
        "search_name": "Joshua Tree October", 
        "user_id": "987654321",
        "has_availabilities": true,
        "telegram_notification_sent": true,
        "parks": ["232472"],
        "date_range": "2025-10-14 to 2025-10-16"
      }
    ]
  }
}
```

#### Manual Check Response
```json
{
  "statusCode": 200,
  "body": {
    "message": "Manual check completed",
    "availabilities_found": 1,
    "total_searches": 3,
    "errors": 0,
    "results": [...]
  }
}
```

### Telegram Bot Lambda Responses

#### Successful Command Response
```json
{
  "statusCode": 200,
  "body": "OK"
}
```

#### Error Response
```json
{
  "statusCode": 500,
  "body": {
    "error": "TELEGRAM_BOT_TOKEN not set"
  }
}
```

## 🚨 Error Handling

### Campsite Checker Lambda Errors
#### Configuration Errors
- **Missing user configs**: Continues processing other users, logs warning
- **Invalid user JSON**: Skips user, logs error, continues with others
- **Missing required search fields**: Skips invalid searches, continues with valid ones

#### API Errors
- **Recreation.gov timeout**: Retries once, then reports error to user via Telegram
- **Invalid park ID**: Skips park, continues with other parks in search
- **Rate limiting**: Waits and retries automatically

#### System Errors
- **Lambda timeout**: Partial results returned, remaining users skipped
- **Memory limit**: Critical error notification sent to all affected users
- **Network issues**: Error notification with details sent to affected users

### Telegram Bot Lambda Errors
#### User Command Errors
- **Invalid date format**: Sends help message with correct format
- **Unknown park**: Suggests using park ID or popular park names
- **Duplicate search name**: Asks user to choose different name
- **Missing required parameters**: Shows command usage examples

#### System Errors
- **S3 access denied**: Sends error message, logs for admin attention
- **Campsite Checker Lambda unavailable**: Informs user to try again later
- **Malformed webhook**: Logs error, returns 400

### Multi-User Error Isolation

**Isolated Failures**: Each user's processing is independent. If one user's configuration is corrupted or causes errors, it doesn't affect other users' campsite monitoring.

**Graceful Degradation**: The system continues operating even if some users encounter errors, ensuring maximum availability for all users.

## 📈 Performance & Limits

### Execution Times
#### Campsite Checker Lambda
- **Single user check**: ~3-5 seconds  
- **Multi-user monitoring (10 users)**: ~15-30 seconds
- **Manual check request**: ~5-10 seconds
- **Large user base (50+ users)**: ~60-120 seconds

#### Telegram Bot Lambda
- **Command processing**: ~0.5-2 seconds
- **Configuration updates**: ~1-3 seconds
- **Manual check trigger**: ~1 second (plus Campsite Checker execution time)

### Recommended Limits
#### Per-User Limits
- **Max searches per user**: 10 searches
- **Max parks per search**: 5 parks
- **Date range**: Up to 30 days per search

#### System Limits
- **Total active users**: 100+ users supported
- **Check frequency**: Every 15-30 minutes
- **Campsite Checker timeout**: 300 seconds (5 minutes)
- **Telegram Bot timeout**: 30 seconds
- **Lambda memory**: 512 MB (Campsite Checker), 256 MB (Telegram Bot)

### Scalability Considerations
- **S3 storage**: Scales automatically with user count
- **Lambda concurrency**: Configure based on user base size
- **Cost optimization**: Inactive users (no searches) consume no processing resources

## 🔧 Configuration Management

### User Configuration Management (via Telegram)

**Users manage their own configurations** through Telegram bot commands:
1. **Add searches**: `/add "Search Name" start_date end_date park`
2. **List searches**: `/list` to see all active searches
3. **Toggle searches**: `/toggle Search Name` to enable/disable
4. **Delete searches**: `/delete Search Name` to remove permanently
5. **Manual checks**: `/check` to run searches immediately

**No manual file editing required** - everything is managed through the Telegram interface.

### Environment Variables

#### Campsite Checker Lambda
- `CONFIG_BUCKET`: S3 bucket containing user configurations
- `TELEGRAM_BOT_TOKEN`: Bot token for sending notifications
- `PUSHOVER_USER_KEY`: (Optional) Legacy Pushover support
- `PUSHOVER_API_TOKEN`: (Optional) Legacy Pushover support

#### Telegram Bot Lambda  
- `CONFIG_BUCKET`: S3 bucket for storing user configurations
- `TELEGRAM_BOT_TOKEN`: Bot token for processing commands

### System Configuration Management

#### User Configuration Storage
- **Location**: S3 bucket under `users/telegram_{user_id}.json`
- **Auto-creation**: New user configs created on first `/start` command
- **Backup**: S3 versioning recommended for configuration backup
- **Migration**: Existing single-user configs can be migrated to per-user format

#### Schedule Management
EventBridge rules control when Campsite Checker Lambda runs:
- `rate(30 minutes)` - Every 30 minutes
- `rate(1 hour)` - Every hour  
- `cron(0 8,20 * * ? *)` - 8am and 8pm daily

#### Telegram Webhook Setup
Configure Telegram webhook to point to your Telegram Bot Lambda:
```bash
curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-api-gateway-url.amazonaws.com/telegram-webhook"}'
```

## 🔍 Monitoring & Debugging

### CloudWatch Logs

#### Campsite Checker Lambda Logs (`/aws/lambda/campbot`)
```
Multi-user mode processing started
Processing 3 searches for user 123456789
Checking park 1/1 (232448) with 45000ms remaining
Real camping check result: No availability found
No notification sent for: Yosemite Valley 4th of July Weekend
Processing 2 searches for user 987654321
Found availability: true for Joshua Tree October
Telegram notification sent to user 987654321
Processed 5 searches across 2 users, found availability in 1, sent 1 notifications
```

#### Telegram Bot Lambda Logs (`/aws/lambda/telegram-bot`)
```
Received message from user 123456789: /add "Yosemite Trip" 2025-07-04 2025-07-06 232448
Added search: Yosemite Trip for user 123456789
Manual check request for user 123456789
Invoking campbot Lambda for user 123456789
Manual check completed successfully
```

### Common Log Messages

#### Campsite Checker Lambda
- `"Processing search: [name] for user [id]"` - Starting a user's search
- `"Found availability: true/false"` - Search results
- `"Telegram notification sent to user [id]"` - Notification delivered
- `"Skipping remaining users due to time limit"` - Lambda timeout protection

#### Telegram Bot Lambda  
- `"Received message from user [id]: [command]"` - Incoming command
- `"Added search: [name] for user [id]"` - Search created successfully
- `"Invoking campbot Lambda for user [id]"` - Manual check triggered
- `"Error loading user config for [id]"` - Configuration issues

### Troubleshooting

#### No Notifications Issues
1. **Check user searches**: Use `/list` in Telegram to verify enabled searches
2. **Check date ranges**: Ensure dates are current and valid
3. **Verify search criteria**: Overly restrictive filters may prevent matches
4. **Check CloudWatch logs**: Look for errors or availability results

#### Command Issues
1. **Date format errors**: Use YYYY-MM-DD format exactly
2. **Park not found**: Try using numeric park ID instead of name
3. **Duplicate names**: Choose unique search names per user
4. **S3 permission errors**: Verify Lambda has S3 read/write access

#### System Issues  
1. **Lambda timeouts**: Check user count and reduce check frequency if needed
2. **S3 errors**: Verify bucket permissions and region configuration
3. **Telegram API errors**: Check bot token and webhook configuration
4. **Recreation.gov API errors**: Check external service status

## 💰 Cost Estimation

### Multi-User System Costs (10 users, 30-minute checks)
- **Campsite Checker Lambda**: ~$1.50/month (longer execution times)
- **Telegram Bot Lambda**: ~$0.25/month (command processing)
- **S3 storage**: ~$0.05/month (user configurations)
- **EventBridge**: ~$0.10/month (scheduled triggers)
- **API Gateway**: ~$0.10/month (Telegram webhook)
- **Telegram**: Free (bot messaging)
- **Total**: ~$2.00/month

### Scaling Costs (50 users)
- **Total estimated cost**: ~$6-8/month
- **Cost per user**: ~$0.12-0.16/month

### Legacy Single-User System (for comparison)
- **Lambda executions**: ~$0.50/month
- **S3 storage**: ~$0.01/month  
- **EventBridge**: ~$0.10/month
- **Pushover**: Free (500 notifications/month)
- **Total**: ~$0.61/month

## 🎯 Best Practices

### User Management
- 👥 **Educate users**: Provide clear examples of `/add` command usage
- 👥 **Monitor usage**: Track active users and searches via CloudWatch
- 👥 **Set expectations**: Explain automatic monitoring vs manual checks
- 👥 **Limit searches**: Encourage users to focus on 3-5 high-priority searches

### Search Strategy (for users)
- ✅ **Specific dates**: Better than broad date ranges
- ✅ **Popular parks**: Check more frequently during peak seasons
- ✅ **Backup dates**: Include multiple viable date options
- ✅ **Flexible criteria**: Don't over-constrain campsite types

### System Configuration
- 🔧 **Monitor timeouts**: Adjust Lambda timeout based on user count
- 🔧 **S3 versioning**: Enable versioning for user configuration backup
- 🔧 **CloudWatch alarms**: Set up alerts for high error rates
- 🔧 **Cost monitoring**: Track Lambda execution costs as user base grows

### Telegram Bot Management
- 🤖 **Clear commands**: Provide helpful error messages with examples
- 🤖 **Input validation**: Validate dates and park IDs before saving
- 🤖 **User feedback**: Confirm successful operations with clear messages
- 🤖 **Error handling**: Gracefully handle malformed commands

### Monitoring Tips
- 📊 **Check CloudWatch logs** for both Lambda functions weekly
- 📊 **Monitor user activity** and search success rates
- 📊 **Track notification delivery** to identify issues
- 📊 **Review error patterns** to improve system reliability
- 📊 **Update user searches** as trip dates approach

## 🔗 Related Files

### Lambda Functions
- `src/campsite_checker/lambda_handler.py` - Main campsite monitoring Lambda
- `src/telegram_bot/handler.py` - Telegram bot command processing Lambda
- `deployment/campsite_checker.zip` - Deployable campsite checker package
- `deployment/telegram_bot.zip` - Deployable telegram bot package

### Documentation  
- `docs/DEPLOYMENT_GUIDE.md` - AWS deployment instructions for both Lambdas
- `docs/TELEGRAM_BOT_SETUP.md` - Telegram bot configuration guide
- `docs/LOCAL_TESTING.md` - Local development and testing guide
- `docs/FUTURE_ROADMAP.md` - Planned enhancements and features

### Configuration Templates
- `config/legacy_searches.json` - Example legacy configuration format
- User configurations are stored dynamically in S3 as `users/telegram_{user_id}.json`
