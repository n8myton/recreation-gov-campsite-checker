# Local Lambda Testing Setup

This guide helps you test your Lambda function locally instead of using remote invoke.

## Quick Setup

### 1. Create Environment Variables File

Create a `.env` file in your project root with your Pushover credentials:

```bash
# Copy the example and fill in your actual values
cp .env.example .env

# Edit .env with your actual credentials
PUSHOVER_USER_KEY=your_actual_pushover_user_key
PUSHOVER_API_TOKEN=your_actual_pushover_api_token
```

**Important:** Never commit the `.env` file to git (it should be in .gitignore)

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Test Your Lambda Function

#### Option A: Test Original Lambda Function
```bash
python3 test_lambda_local.py
```

#### Option B: Test Enhanced Lambda Function
```bash
# Test basic notification
python3 -c "
from lambda_function_enhanced import lambda_handler
result = lambda_handler({}, None)
print(result)
"

# Test with custom message
python3 -c "
from lambda_function_enhanced import lambda_handler
result = lambda_handler({'message': 'Testing from local!'}, None)
print(result)
"
```

## Alternative Methods

### Method 1: Export Environment Variables
```bash
export PUSHOVER_USER_KEY="your_user_key"
export PUSHOVER_API_TOKEN="your_api_token"
python3 test_lambda_local.py
```

### Method 2: Use a Config File
Create `config.py`:
```python
import os

PUSHOVER_USER_KEY = os.getenv('PUSHOVER_USER_KEY', 'your_default_key')
PUSHOVER_API_TOKEN = os.getenv('PUSHOVER_API_TOKEN', 'your_default_token')
```

### Method 3: Interactive Testing
```bash
python3
>>> from lambda_function import lambda_handler
>>> import os
>>> os.environ['PUSHOVER_USER_KEY'] = 'your_key'
>>> os.environ['PUSHOVER_API_TOKEN'] = 'your_token'
>>> result = lambda_handler({}, None)
>>> print(result)
```

## Files Created

- `test_lambda_local.py` - Test script for your original lambda function
- `lambda_function_enhanced.py` - Enhanced version that can integrate with your camping checker
- `.env.example` - Template for environment variables

## Getting Your Pushover Credentials

1. Go to https://pushover.net/
2. Sign up/Login
3. Your User Key is on the main dashboard
4. Create an application to get an API Token

## Troubleshooting

- **ImportError**: Make sure all dependencies are installed with `pip3 install -r requirements.txt`
- **Missing env vars**: Ensure your `.env` file exists and has the correct variable names
- **Network errors**: Check your Pushover credentials are correct
