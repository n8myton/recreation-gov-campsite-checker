#!/bin/bash
# Package Lambda functions for deployment
# Usage: ./scripts/package.sh [campbot|telegram|all]

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"
TEMP_DIR="/tmp/campbot_build"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏕️  CampBot Package Builder${NC}\n"

# Function to package Telegram Bot
package_telegram() {
    echo -e "${YELLOW}📦 Packaging Telegram Bot...${NC}"
    
    cd "$PROJECT_ROOT/src/telegram_bot"
    
    # Remove old package
    rm -f "$DEPLOYMENT_DIR/telegram_bot.zip"
    
    # Create new package (just the handler, boto3 included in Lambda runtime)
    zip "$DEPLOYMENT_DIR/telegram_bot.zip" telegram_handler.py
    
    # Check size
    SIZE=$(du -h "$DEPLOYMENT_DIR/telegram_bot.zip" | cut -f1)
    echo -e "${GREEN}✅ Telegram bot packaged: ${SIZE}${NC}"
    echo -e "   Expected size: 5-10 KB"
    echo ""
}

# Function to package Campsite Checker
package_campbot() {
    echo -e "${YELLOW}📦 Packaging Campsite Checker...${NC}"
    
    # Clean up old temp directory
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
    
    # Install dependencies
    echo "   Installing dependencies..."
    pip3 install -q -r "$PROJECT_ROOT/src/campsite_checker/campsite_requirements.txt" \
        -t "$TEMP_DIR" --upgrade 2>&1 | grep -v "Requirement already satisfied" || true
    
    # Copy source files
    echo "   Copying source files..."
    cp "$PROJECT_ROOT/src/campsite_checker/campsite_handler.py" "$TEMP_DIR/"
    cp "$PROJECT_ROOT/src/campsite_checker/camping.py" "$TEMP_DIR/"
    cp -r "$PROJECT_ROOT/src/campsite_checker/clients" "$TEMP_DIR/"
    cp -r "$PROJECT_ROOT/src/campsite_checker/enums" "$TEMP_DIR/"
    cp -r "$PROJECT_ROOT/src/campsite_checker/utils" "$TEMP_DIR/"
    
    # Remove old package
    rm -f "$DEPLOYMENT_DIR/campsite_checker.zip"
    
    # Create new package
    echo "   Creating zip archive..."
    cd "$TEMP_DIR"
    zip -q -r "$DEPLOYMENT_DIR/campsite_checker.zip" . \
        -x "*.pyc" \
        -x "*__pycache__*" \
        -x "*.dist-info/*" \
        -x "*/tests/*" \
        -x "*/test/*"
    
    # Check size
    SIZE=$(du -h "$DEPLOYMENT_DIR/campsite_checker.zip" | cut -f1)
    echo -e "${GREEN}✅ Campsite checker packaged: ${SIZE}${NC}"
    echo -e "   Expected size: 1.5-2.5 MB"
    echo ""
    
    # Clean up
    rm -rf "$TEMP_DIR"
}

# Main logic
case "${1:-all}" in
    telegram)
        package_telegram
        ;;
    campbot)
        package_campbot
        ;;
    all)
        package_telegram
        package_campbot
        ;;
    *)
        echo "Usage: $0 [campbot|telegram|all]"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Packaging complete!${NC}"
echo -e "Packages are in: ${BLUE}$DEPLOYMENT_DIR${NC}"
echo ""
echo "Next steps:"
echo "  1. Deploy: ./scripts/deploy.sh [campbot|telegram|all]"
echo "  2. Or manually: aws lambda update-function-code --function-name campbot --zip-file fileb://deployment/campsite_checker.zip"

