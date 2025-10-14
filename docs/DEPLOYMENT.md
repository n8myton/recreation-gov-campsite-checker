# 🚀 CampBot Deployment Guide

Quick and practical guide for deploying Lambda functions to AWS.

---

## ⚡ Quick Start

**Deploy everything in one command:**
```bash
make deploy
```

**That's it!** The scripts handle packaging, dependencies, and deployment automatically.

---

## 📋 Prerequisites

One-time setup:

```bash
# 1. Install AWS CLI (if not already installed)
brew install awscli

# 2. Configure AWS credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1)

# 3. Verify setup
make check-aws
```

**Requirements:**
- AWS CLI installed and configured
- Python 3.9+ and pip3
- Lambda functions exist in AWS: `campbot` and `campbot-telegram-bot`

---

## 🎯 Common Commands

```bash
# Deployment
make deploy              # Deploy both functions
make deploy-campbot      # Deploy campsite checker only
make deploy-telegram     # Deploy telegram bot only

# Monitoring
make logs-campbot        # Watch logs in real-time
make logs-telegram       # Watch telegram logs
make invoke-campbot      # Manually trigger checker

# Maintenance
make package             # Package without deploying
make clean               # Remove old packages
make check-aws           # Verify AWS setup
make help                # Show all commands
```

---

## 🔄 Typical Workflow

When you make code changes:

```bash
# 1. Edit code
vim src/campsite_checker/campsite_handler.py

# 2. Deploy
make deploy-campbot

# 3. Test via Telegram
# Send: /check

# 4. Monitor
make logs-campbot
```

---

## 📦 What Gets Packaged?

### **Telegram Bot** (~6 KB)
- Just `telegram_handler.py`
- Boto3 included in Lambda runtime

### **Campsite Checker** (~2 MB)
- All source files (`campsite_handler.py`, `camping.py`, etc.)
- All dependencies from `campsite_requirements.txt`
- Clients, enums, and utils directories

Expected sizes are fine - Lambda limit is 50 MB zipped.

---

## 🐛 Troubleshooting

### Quick Fixes

| Problem | Solution |
|---------|----------|
| "Package not found" | `make package` then `make deploy` |
| "AWS CLI not found" | `brew install awscli && aws configure` |
| "Access Denied" | Run `aws configure` to set credentials |
| "Function not found" | Update function names in `scripts/deploy.sh` |
| Import errors | `make clean && make deploy` |

### Check Logs
```bash
# See what went wrong
make logs-campbot

# Test manually
make invoke-campbot
```

### Verify Package
```bash
# Check size (should be ~2 MB for campbot, ~6 KB for telegram)
ls -lh deployment/

# View contents
unzip -l deployment/campsite_checker.zip | head -30
```

---

## 🔧 Advanced Usage

### Using Scripts Directly
```bash
# Package only
./scripts/package.sh all           # Both functions
./scripts/package.sh campbot        # Campsite checker only
./scripts/package.sh telegram       # Telegram bot only

# Deploy only (must package first)
./scripts/deploy.sh all
./scripts/deploy.sh campbot
./scripts/deploy.sh telegram
```

### Manual AWS CLI
```bash
# Package first
./scripts/package.sh all

# Deploy manually
aws lambda update-function-code \
    --function-name campbot \
    --zip-file fileb://deployment/campsite_checker.zip
```

### Adding Dependencies
```bash
# 1. Add to requirements
echo "new-package>=1.0.0" >> src/campsite_checker/campsite_requirements.txt

# 2. Rebuild and deploy
make deploy-campbot
```

---

## 📝 Pre-Deployment Checklist

Quick checks before deploying:

- [ ] Code tested (at least manually via Telegram)
- [ ] Dependencies updated in requirements.txt (if changed)
- [ ] AWS credentials configured
- [ ] Lambda environment variables set (TELEGRAM_BOT_TOKEN, CONFIG_BUCKET, etc.)
- [ ] Function names correct in scripts

After deployment:
- [ ] Test with `/check` command
- [ ] Monitor logs for a few minutes
- [ ] Verify expected behavior

---

## 🔐 Security Reminders

**Never commit:**
- AWS credentials
- `.env` files
- `TELEGRAM_BOT_TOKEN`
- Deployment packages (`*.zip`)

Already handled by `.gitignore` ✅

**Store secrets as:**
- Lambda environment variables (AWS Console)
- AWS Systems Manager Parameter Store
- AWS Secrets Manager

---

## 🎓 How It Works

### Package Script (`scripts/package.sh`)
1. Creates temp directory
2. Installs dependencies from requirements.txt
3. Copies source files
4. Creates zip archive
5. Saves to `deployment/` directory

### Deploy Script (`scripts/deploy.sh`)
1. Checks AWS credentials
2. Verifies package exists
3. Calls `aws lambda update-function-code`
4. Confirms success

### Makefile
- Wrapper around scripts for convenience
- Provides helpful commands like `make deploy`
- Self-documenting with `make help`

---

## 💡 Tips

- **Tab completion works:** Type `make dep` + TAB
- **Chain commands:** `make clean && make deploy`
- **Watch during deploy:** Open two terminals (one for deploy, one for logs)
- **Test before wide rollout:** Deploy and test with `/check` first
- **Don't overthink it:** For personal use, `make deploy` is all you need

---

## 🆘 Getting Help

If something breaks:

1. **Check logs first** - Most errors show here
   ```bash
   make logs-campbot
   ```

2. **Verify AWS setup**
   ```bash
   make check-aws
   aws lambda get-function --function-name campbot
   ```

3. **Clean and rebuild**
   ```bash
   make clean
   make deploy
   ```

4. **Manual test**
   ```bash
   make invoke-campbot
   ```

---

## 📚 Additional Files

- **Function names:** Edit `scripts/deploy.sh`
- **Dependencies:** Edit `src/*/requirements.txt`
- **Package contents:** Edit `scripts/package.sh`
- **Roadmap:** See `docs/ROADMAP_V2.md`

---

**Remember:** Deployment should be boring. Run `make deploy`, test, done. 🎉

