.PHONY: help package deploy package-campbot package-telegram deploy-campbot deploy-telegram clean test

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)🏕️  CampBot Deployment Commands$(NC)\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

package: ## Package both Lambda functions
	@./scripts/package.sh all

package-campbot: ## Package only campsite checker
	@./scripts/package.sh campbot

package-telegram: ## Package only telegram bot
	@./scripts/package.sh telegram

deploy: package ## Package and deploy both functions
	@./scripts/deploy.sh all

deploy-campbot: package-campbot ## Package and deploy campsite checker only
	@./scripts/deploy.sh campbot

deploy-telegram: package-telegram ## Package and deploy telegram bot only
	@./scripts/deploy.sh telegram

clean: ## Remove all deployment packages
	@echo "🧹 Cleaning deployment packages..."
	@rm -f deployment/campsite_checker.zip deployment/telegram_bot.zip
	@echo "✅ Clean complete"

test: ## Run tests (placeholder)
	@echo "🧪 Running tests..."
	@python3 -m pytest tests/ -v

check-aws: ## Check AWS configuration
	@echo "🔍 Checking AWS configuration..."
	@aws sts get-caller-identity || (echo "❌ AWS not configured. Run: aws configure" && exit 1)
	@echo "✅ AWS credentials OK"
	@echo ""
	@echo "Lambda functions:"
	@aws lambda list-functions --query 'Functions[?contains(FunctionName, `camp`) || contains(FunctionName, `telegram`)].FunctionName' --output table

logs-campbot: ## Tail logs for campsite checker
	@aws logs tail /aws/lambda/campbot --follow

logs-telegram: ## Tail logs for telegram bot
	@aws logs tail /aws/lambda/campbot-telegram-bot --follow

invoke-campbot: ## Manually invoke campsite checker (scheduled check)
	@echo "🔍 Invoking campsite checker..."
	@aws lambda invoke --function-name campbot --payload '{"multi_user_mode": true}' /tmp/campbot-response.json
	@cat /tmp/campbot-response.json | jq '.'
	@rm /tmp/campbot-response.json

