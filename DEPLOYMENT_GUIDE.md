# Production Deployment Guide

## 🚀 Deployment Architecture

**Best Setup**: S3 + Lambda + EventBridge + Pushover

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

## 📋 Setup Steps

### 1. Create S3 Bucket for Configuration
```bash
# Create bucket (replace with your unique name)
aws s3 mb s3://your-campbot-config

# Upload your search configuration
aws s3 cp campsite_searches.json s3://your-campbot-config/
```

### 2. Package Lambda Function
```bash
# Install production dependencies
pip3 install -r requirements.txt -t ./package/

# Copy your code
cp lambda_function_production.py ./package/
cp -r clients/ ./package/
cp -r enums/ ./package/
cp -r utils/ ./package/
cp camping.py ./package/

# Create deployment package
cd package && zip -r ../campbot-deployment.zip . && cd ..
```

### 3. Create Lambda Function
```bash
aws lambda create-function \
  --function-name campbot \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR-ACCOUNT:role/lambda-execution-role \
  --handler lambda_function_production.lambda_handler \
  --zip-file fileb://campbot-deployment.zip \
  --timeout 300 \
  --memory-size 512
```

### 4. Set Environment Variables
```bash
aws lambda update-function-configuration \
  --function-name campbot \
  --environment Variables='{
    "PUSHOVER_USER_KEY":"your_user_key",
    "PUSHOVER_API_TOKEN":"your_api_token",
    "CONFIG_BUCKET":"your-campbot-config"
  }'
```

### 5. Create EventBridge Schedule
```bash
# Create rule for every 30 minutes
aws events put-rule \
  --name campbot-schedule \
  --schedule-expression "rate(30 minutes)"

# Add Lambda as target
aws events put-targets \
  --rule campbot-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT:function:campbot"
```

## 🔧 Configuration Management

### Updating Search Configurations
```bash
# Edit campsite_searches.json locally, then:
aws s3 cp campsite_searches.json s3://your-campbot-config/

# Changes take effect on next scheduled run (no Lambda redeployment!)
```

### Configuration Structure
```json
{
  "searches": [
    {
      "name": "Descriptive Name",
      "enabled": true,
      "parks": ["park_id1", "park_id2"],
      "start_date": "2025-07-04",
      "end_date": "2025-07-06",
      "campsite_type": null,
      "nights": 2,
      "priority": "high"
    }
  ]
}
```

## 🎛️ Alternative Deployment Options

### Option A: EventBridge with Event Payload
```json
{
  "searches": [
    {
      "name": "Quick Check",
      "parks": ["232472"],
      "start_date": "2025-10-14",
      "end_date": "2025-10-15"
    }
  ]
}
```

### Option B: Parameter Store
```bash
# Store config in Parameter Store
aws ssm put-parameter \
  --name "/campbot/searches" \
  --value file://campsite_searches.json \
  --type "String"
```

### Option C: Multiple Schedules
- Different EventBridge rules for different priorities
- High priority searches every 15 minutes
- Normal priority searches every hour

## 🔄 Schedule Options

- **Every 15 minutes**: `rate(15 minutes)`
- **Every hour**: `rate(1 hour)`
- **Twice daily**: `rate(12 hours)`
- **Specific times**: `cron(0 8,20 * * ? *)` (8am & 8pm daily)

## 📊 Monitoring

### CloudWatch Logs
- All execution logs appear in `/aws/lambda/campbot`
- Search results and notifications logged

### Metrics to Monitor
- Execution duration
- Error rates
- Memory usage
- Pushover notification success

## 💰 Cost Estimate

**Monthly costs** (assuming every 30 minutes):
- Lambda executions: ~$0.50
- S3 storage: ~$0.01
- EventBridge: ~$0.10
- **Total**: ~$0.61/month

## 🔒 Security Best Practices

1. **IAM Role**: Lambda needs S3 read permissions only
2. **Environment Variables**: Store Pushover credentials securely
3. **S3 Bucket**: Private bucket with versioning enabled
4. **VPC**: Not needed for this use case

## 🧪 Testing Before Deployment

```bash
# Test locally first
python3 test_production_lambda.py

# Test individual components
python3 -c "from lambda_function_production import load_search_config; print(load_search_config())"
```
