# 🤖 Telegram Bot Setup Guide

This guide will help you set up the Telegram bot interface for your campsite monitoring system, allowing multiple users to manage their own campsite searches remotely.

## 🏗️ New Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram      │───▶│   Bot Lambda     │───▶│   S3 Configs    │
│   Users         │    │   Handler        │    │  (per user)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          │
                              ▼                          ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Multi-user     │    │   Recreation    │
                       │   Campsite       │───▶│   .gov API      │
                       │   Lambda         │    │                 │
                       └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Telegram      │
                       │   Notifications │
                       └─────────────────┘
```

## 📋 Prerequisites

1. **Existing campsite checker** working with AWS Lambda
2. **AWS CLI** configured with appropriate permissions
3. **Telegram account** to create the bot

## 🤖 Step 1: Create Telegram Bot

1. **Message @BotFather** on Telegram
2. **Send `/newbot`**
3. **Choose a name** (e.g., "Campsite Alert Bot")
4. **Choose a username** (e.g., "your_campsite_bot")
5. **Save the bot token** - you'll need this for AWS

```
Example token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

## 🚀 Step 2: Deploy New Lambda Functions

### 2A. Deploy Telegram Bot Handler

1. **Create new Lambda function:**
```bash
# Create deployment package
cd /path/to/your/campsite-checker
cp telegram_bot_handler.py lambda_package/
cd lambda_package
zip telegram_bot_handler.zip telegram_bot_handler.py

# Create Lambda function
aws lambda create-function \
  --function-name campsite-telegram-bot \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/YOUR_LAMBDA_ROLE \
  --handler telegram_bot_handler.lambda_handler \
  --zip-file fileb://telegram_bot_handler.zip
```

2. **Set environment variables:**
```bash
aws lambda update-function-configuration \
  --function-name campsite-telegram-bot \
  --environment Variables='{
    "TELEGRAM_BOT_TOKEN":"YOUR_BOT_TOKEN_HERE",
    "CONFIG_BUCKET":"your-campsite-config-bucket"
  }'
```

### 2B. Update Main Monitoring Lambda

1. **Replace your existing lambda function with the multi-user version:**
```bash
# Copy new multi-user version
cp lambda_function_multiuser.py lambda_package/lambda_function.py
cd lambda_package
zip -r campsite_multiuser.zip .

# Update existing Lambda
aws lambda update-function-code \
  --function-name your-existing-campsite-function \
  --zip-file fileb://campsite_multiuser.zip
```

2. **Add environment variable for multi-user mode:**
```bash
aws lambda update-function-configuration \
  --function-name your-existing-campsite-function \
  --environment Variables='{
    "PUSHOVER_USER_KEY":"your_key",
    "PUSHOVER_API_TOKEN":"your_token",
    "CONFIG_BUCKET":"your-bucket",
    "TELEGRAM_BOT_TOKEN":"YOUR_BOT_TOKEN_HERE"
  }'
```

## 🌐 Step 3: Set Up API Gateway for Telegram Webhook

1. **Create API Gateway:**
```bash
# Create REST API
aws apigateway create-rest-api \
  --name campsite-telegram-webhook \
  --description "Webhook for Telegram campsite bot"
```

2. **Create resource and method:**
```bash
# Get the API ID from previous command
API_ID="your-api-id"

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query 'items[0].id' --output text)

# Create POST method
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $ROOT_ID \
  --http-method POST \
  --authorization-type NONE

# Set up Lambda integration
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $ROOT_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:campsite-telegram-bot/invocations

# Deploy API
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod
```

3. **Set up webhook URL:**
```bash
# Your webhook URL will be:
# https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod

# Set webhook with Telegram
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
  -d "url=https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod"
```

## 🔑 Step 4: Update IAM Permissions

Your Lambda execution role needs these additional permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-config-bucket/*",
                "arn:aws:s3:::your-config-bucket"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
```

## 📅 Step 5: Update EventBridge Schedule

Update your existing EventBridge rule to use multi-user mode:

```bash
# Update the rule target to pass multi_user_mode parameter
aws events put-targets \
  --rule your-campsite-monitoring-rule \
  --targets Id=1,Arn=arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:your-campsite-function,Input='{"multi_user_mode": true}'
```

## 🧪 Step 6: Test Your Setup

### Test Telegram Bot

1. **Find your bot** on Telegram (search for the username you created)
2. **Send `/start`** - you should get a welcome message
3. **Try adding a search:**
```
/add "Test Search" 2025-12-01 2025-12-03 232448
```

### Test Monitoring

1. **Manually trigger** your main Lambda:
```bash
aws lambda invoke \
  --function-name your-campsite-function \
  --payload '{"multi_user_mode": true}' \
  response.json

cat response.json
```

## 👥 User Management

### S3 Structure

Your S3 bucket will now have this structure:
```
your-config-bucket/
├── campsite_searches.json          # Legacy config (optional)
├── users/
│   ├── telegram_123456789.json     # User 1's searches
│   ├── telegram_987654321.json     # User 2's searches
│   └── telegram_555666777.json     # User 3's searches
```

### User Configuration Format

Each user's config file looks like:
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
      "name": "Yosemite Summer",
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

## 🎯 Bot Commands for Users

Once set up, users can interact with your bot using these commands:

```
🏕️ CAMPSITE BOT COMMANDS

/start - Welcome message and setup
/add "Name" YYYY-MM-DD YYYY-MM-DD park_id - Add search
/list - Show your active searches  
/toggle <search_name> - Enable/disable a search
/delete <search_name> - Remove a search
/help - Show available commands

EXAMPLES:
/add "Yosemite Trip" 2025-07-04 2025-07-06 232448
/add "Joshua Tree" 2025-10-15 2025-10-17 joshua tree
/toggle Yosemite Trip
/delete Yosemite Trip
```

## 🔧 Monitoring & Troubleshooting

### CloudWatch Logs

Monitor these log groups:
- `/aws/lambda/campsite-telegram-bot` - Bot interactions
- `/aws/lambda/your-campsite-function` - Monitoring execution

### Common Issues

1. **Bot not responding:**
   - Check webhook is set correctly
   - Verify API Gateway permissions
   - Check CloudWatch logs

2. **No notifications sent:**
   - Verify user configs exist in S3
   - Check TELEGRAM_BOT_TOKEN is set
   - Ensure searches are enabled

3. **API Gateway 403 errors:**
   - Add Lambda permission for API Gateway
   ```bash
   aws lambda add-permission \
     --function-name campsite-telegram-bot \
     --statement-id api-gateway-permission \
     --action lambda:InvokeFunction \
     --principal apigateway.amazonaws.com
   ```

## 💰 Cost Impact

Adding Telegram bot support will add minimal costs:
- **Lambda invocations**: ~$0.10/month for bot interactions
- **API Gateway**: ~$0.05/month for webhook calls
- **Additional S3 storage**: ~$0.01/month for user configs

**Total additional cost: ~$0.16/month**

## 🚀 Going Live

1. **Test with yourself first** - make sure everything works
2. **Invite 2-3 friends** to test the bot
3. **Monitor for a week** to ensure stability
4. **Share with your target 10-20 users**

## 📈 Scaling Considerations

For 10-20 users, this setup handles easily. For larger scale:

- **Rate limiting**: Add user-specific rate limits
- **Database**: Consider moving from S3 JSON to DynamoDB
- **Caching**: Add Redis for frequently accessed data
- **Monitoring**: Set up alerts for errors and usage spikes

## 🎉 You're Ready!

Your campsite monitoring system now supports:
- ✅ **Multiple users** with separate configurations
- ✅ **Telegram bot interface** for easy management
- ✅ **Real-time notifications** via Telegram
- ✅ **Backward compatibility** with your existing setup
- ✅ **Scalable architecture** for growth

Users can now manage their campsite alerts from anywhere using just their phone! 📱🏕️
