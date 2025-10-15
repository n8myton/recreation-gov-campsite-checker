# 🤖 Telegram Bot Setup Guide

Quick guide to creating and configuring your Telegram bot for campsite monitoring.

## 📋 Prerequisites

1. A Telegram account
2. AWS Lambda functions deployed (see [DEPLOYMENT.md](DEPLOYMENT.md))
3. AWS CLI configured

## 🤖 Step 1: Create Telegram Bot

1. **Message @BotFather** on Telegram
2. **Send `/newbot`**
3. **Choose a name** (e.g., "Campsite Alert Bot")
4. **Choose a username** (must end in 'bot', e.g., "your_campsite_bot")
5. **Save the bot token** - you'll need this for AWS Lambda

```
Example token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

⚠️ **Keep this token secret!** Anyone with this token can control your bot.

## 🌐 Step 2: Set Up API Gateway Webhook

Your Telegram bot needs a webhook URL to receive messages. This connects Telegram to your Lambda function.

### Create API Gateway (if not already done)

```bash
# Get your API Gateway URL from AWS Console or CLI
aws apigateway get-rest-apis
```

Your webhook URL will be: `https://YOUR_API_ID.execute-api.REGION.amazonaws.com/prod`

### Configure Telegram Webhook

```bash
# Replace YOUR_BOT_TOKEN and YOUR_API_GATEWAY_URL
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_API_GATEWAY_URL"}'
```

### Verify Webhook

```bash
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
```

You should see your webhook URL and `pending_update_count: 0`.

## 🔑 Step 3: Set Lambda Environment Variables

Both Lambda functions need the bot token:

```bash
# For Telegram Bot Lambda
aws lambda update-function-configuration \
  --function-name campbot-telegram-bot \
  --environment Variables='{
    "TELEGRAM_BOT_TOKEN":"YOUR_BOT_TOKEN",
    "CONFIG_BUCKET":"your-s3-bucket-name"
  }'

# For Campsite Checker Lambda
aws lambda update-function-configuration \
  --function-name campbot \
  --environment Variables='{
    "TELEGRAM_BOT_TOKEN":"YOUR_BOT_TOKEN",
    "CONFIG_BUCKET":"your-s3-bucket-name"
  }'
```

## ✅ Step 4: Test Your Bot

1. **Find your bot** on Telegram (search for the username you created)
2. **Send `/start`** - you should get a welcome message
3. **Try adding a search:**
   ```
   /add "Test Search" 2025-12-01 2025-12-03 232448
   ```
4. **List your searches:**
   ```
   /list
   ```

If you get responses, congratulations! Your bot is working. 🎉

## 🔧 IAM Permissions

Your Lambda execution role needs these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-config-bucket/*",
                "arn:aws:s3:::your-config-bucket"
            ]
        },
        {
            "Effect": "Allow",
            "Action": ["lambda:InvokeFunction"],
            "Resource": "arn:aws:lambda:*:*:function:campbot"
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

Also add API Gateway permission to invoke your bot Lambda:

```bash
aws lambda add-permission \
  --function-name campbot-telegram-bot \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com
```

## 🐛 Troubleshooting

### Bot not responding
- Check webhook is set correctly: `curl https://api.telegram.org/botYOUR_TOKEN/getWebhookInfo`
- Verify API Gateway URL is correct and deployed
- Check CloudWatch logs for errors: `/aws/lambda/campbot-telegram-bot`

### "Invalid bot token" error
- Double-check you copied the entire token from BotFather
- Make sure token is set in Lambda environment variables

### Commands work but no scheduled checks
- Verify EventBridge rule is enabled
- Check Campsite Checker Lambda has correct environment variables
- Look at CloudWatch logs: `/aws/lambda/campbot`

## 🎯 Available Commands

Once set up, users can use these commands:

- `/start` - Welcome message and help
- `/add "Name" YYYY-MM-DD YYYY-MM-DD park_id` - Add a search
- `/list` - Show active searches
- `/toggle <name>` - Enable/disable a search
- `/delete <name>` - Remove a search
- `/deleteall` - Remove all searches
- `/check` - Manually check all searches now
- `/help` - Show help message

## 📱 User Experience

After setup:
1. Users find your bot on Telegram
2. They send `/start` to begin
3. They add searches with `/add`
4. Bot checks automatically every minute
5. Users get notified when campsites are found

No AWS knowledge required for users! 🎉
