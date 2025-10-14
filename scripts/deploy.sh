#!/bin/bash
# Deploy Lambda functions to AWS
# Usage: ./scripts/deploy.sh [campbot|telegram|all]

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 CampBot Deployer${NC}\n"

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Install it first:${NC}"
    echo "   brew install awscli"
    echo "   or visit: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured.${NC}"
    echo "   Run: aws configure"
    exit 1
fi

# Function to deploy Telegram Bot
deploy_telegram() {
    echo -e "${YELLOW}🤖 Deploying Telegram Bot...${NC}"
    
    if [ ! -f "$DEPLOYMENT_DIR/telegram_bot.zip" ]; then
        echo -e "${RED}❌ Package not found. Run ./scripts/package.sh first${NC}"
        exit 1
    fi
    
    FUNCTION_NAME="campbot-telegram-bot"  # Actual function name in AWS
    
    echo "   Updating Lambda function: $FUNCTION_NAME"
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$DEPLOYMENT_DIR/telegram_bot.zip" \
        --output text \
        --query 'LastModified'
    
    echo -e "${GREEN}✅ Telegram bot deployed!${NC}"
    echo ""
}

# Function to deploy Campsite Checker
deploy_campbot() {
    echo -e "${YELLOW}🏕️  Deploying Campsite Checker...${NC}"
    
    if [ ! -f "$DEPLOYMENT_DIR/campsite_checker.zip" ]; then
        echo -e "${RED}❌ Package not found. Run ./scripts/package.sh first${NC}"
        exit 1
    fi
    
    FUNCTION_NAME="campbot"  # Update this if your function has a different name
    
    echo "   Updating Lambda function: $FUNCTION_NAME"
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$DEPLOYMENT_DIR/campsite_checker.zip" \
        --output text \
        --query 'LastModified'
    
    echo -e "${GREEN}✅ Campsite checker deployed!${NC}"
    echo ""
}

# Main logic
case "${1:-all}" in
    telegram)
        deploy_telegram
        ;;
    campbot)
        deploy_campbot
        ;;
    all)
        deploy_campbot
        deploy_telegram
        ;;
    *)
        echo "Usage: $0 [campbot|telegram|all]"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo "Check status:"
echo "  aws lambda get-function --function-name campbot"
echo "  aws lambda get-function --function-name telegram_bot"

