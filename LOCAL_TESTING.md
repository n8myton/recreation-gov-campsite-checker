# Local Lambda Testing - Quick Reference

## 🚀 The Right Way (Using .env file)

### 1. Create `.env` file
Create a `.env` file in project root with your Pushover credentials:
```
PUSHOVER_USER_KEY=your_actual_pushover_user_key
PUSHOVER_API_TOKEN=your_actual_pushover_api_token
```
⚠️ **Never commit .env to git** (already in .gitignore)

### 2. Install dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Test locally
```bash
python3 test_lambda_local.py
```

That's it! ✅

## 📋 What We Built

- **`lambda_function.py`** - Your original Lambda function
- **`test_lambda_local.py`** - Local test script (mimics Lambda environment)
- **`lambda_function_enhanced.py`** - Enhanced version with camping integration
- **`.env`** - Your local credentials (not in git)

## 🔑 Getting Pushover Credentials

1. Go to https://pushover.net/
2. Sign up/Login  
3. User Key = on main dashboard
4. Create app → get API Token

## 🐛 Quick Troubleshooting

- **Missing env vars**: Check `.env` file exists and has correct variable names
- **ImportError**: Run `pip3 install -r requirements.txt`
- **Network errors**: Verify Pushover credentials are correct
