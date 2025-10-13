#!/usr/bin/env python3
"""
Local testing script for Telegram bot functionality
Run this to test bot commands without deploying to AWS
"""

import json
import os
from telegram_bot_handler import lambda_handler, handle_start_command, handle_add_command, handle_list_command

# Mock data for testing
TEST_USER_ID = "123456789"
TEST_CHAT_ID = "123456789"

def create_test_event(command, user_id=TEST_USER_ID, chat_id=TEST_CHAT_ID):
    """Create a test Telegram webhook event"""
    return {
        "body": json.dumps({
            "message": {
                "message_id": 1,
                "from": {
                    "id": int(user_id),
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": int(chat_id),
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1640995200,
                "text": command
            }
        })
    }

def test_bot_commands():
    """Test various bot commands locally"""
    
    # Set up environment variables for testing
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_123'
    os.environ['CONFIG_BUCKET'] = 'test-bucket'
    
    print("🧪 Testing Telegram Bot Commands Locally\n")
    
    # Test /start command
    print("1. Testing /start command:")
    event = create_test_event("/start")
    try:
        response = lambda_handler(event, None)
        print(f"   Status: {response['statusCode']}")
        print(f"   Response: {response['body']}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Test /add command with proper format
    print("2. Testing /add command:")
    event = create_test_event('/add "Test Search" 2025-07-04 2025-07-06 232448')
    try:
        response = lambda_handler(event, None)
        print(f"   Status: {response['statusCode']}")
        print(f"   Response: {response['body']}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Test /add command with invalid format
    print("3. Testing /add command (invalid format):")
    event = create_test_event('/add incomplete')
    try:
        response = lambda_handler(event, None)
        print(f"   Status: {response['statusCode']}")
        print(f"   Response: {response['body']}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Test /list command
    print("4. Testing /list command:")
    event = create_test_event("/list")
    try:
        response = lambda_handler(event, None)
        print(f"   Status: {response['statusCode']}")
        print(f"   Response: {response['body']}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Test unknown command
    print("5. Testing unknown command:")
    event = create_test_event("/unknown")
    try:
        response = lambda_handler(event, None)
        print(f"   Status: {response['statusCode']}")
        print(f"   Response: {response['body']}\n")
    except Exception as e:
        print(f"   Error: {e}\n")

def create_sample_user_config():
    """Create a sample user configuration for testing"""
    return {
        "version": "1.0",
        "user_id": TEST_USER_ID,
        "notification_settings": {
            "telegram_enabled": True,
            "pushover_enabled": False,
            "only_notify_on_availability": True,
            "include_search_name_in_notification": True
        },
        "searches": [
            {
                "name": "Yosemite Test",
                "enabled": True,
                "parks": ["232448"],
                "start_date": "2025-07-04",
                "end_date": "2025-07-06",
                "campsite_type": None,
                "campsite_ids": [],
                "nights": 2,
                "weekends_only": False,
                "priority": "high",
                "created_at": "2025-01-15T10:30:00"
            },
            {
                "name": "Joshua Tree Weekend",
                "enabled": False,
                "parks": ["232472"],
                "start_date": "2025-08-15",
                "end_date": "2025-08-17",
                "campsite_type": "STANDARD NONELECTRIC",
                "campsite_ids": [],
                "nights": 2,
                "weekends_only": False,
                "priority": "normal",
                "created_at": "2025-01-15T11:00:00"
            }
        ]
    }

def test_multi_user_lambda():
    """Test the multi-user lambda function"""
    print("🧪 Testing Multi-User Lambda Function\n")
    
    # Import the multi-user lambda
    try:
        from lambda_function_multiuser import lambda_handler as multiuser_handler
        
        # Test multi-user mode
        print("1. Testing multi-user mode:")
        event = {
            "multi_user_mode": True,
            "config_bucket": "test-bucket"
        }
        
        try:
            response = multiuser_handler(event, None)
            print(f"   Status: {response['statusCode']}")
            print(f"   Body: {json.dumps(json.loads(response['body']), indent=2)}\n")
        except Exception as e:
            print(f"   Error: {e}\n")
        
        # Test legacy mode
        print("2. Testing legacy mode:")
        event = {
            "multi_user_mode": False,
            "config_bucket": "test-bucket",
            "config_key": "campsite_searches.json"
        }
        
        try:
            response = multiuser_handler(event, None)
            print(f"   Status: {response['statusCode']}")
            print(f"   Body: {json.dumps(json.loads(response['body']), indent=2)}\n")
        except Exception as e:
            print(f"   Error: {e}\n")
            
    except ImportError as e:
        print(f"Error importing multi-user lambda: {e}")

def print_sample_user_config():
    """Print a sample user configuration"""
    print("📋 Sample User Configuration:\n")
    config = create_sample_user_config()
    print(json.dumps(config, indent=2))
    print("\nThis would be stored as: s3://your-bucket/users/telegram_123456789.json\n")

def print_deployment_checklist():
    """Print deployment checklist"""
    print("✅ Deployment Checklist:\n")
    checklist = [
        "1. Create Telegram bot with @BotFather",
        "2. Save bot token securely",
        "3. Deploy telegram_bot_handler.py as Lambda function",
        "4. Deploy lambda_function_multiuser.py as updated main function", 
        "5. Set up API Gateway webhook for Telegram",
        "6. Configure environment variables (TELEGRAM_BOT_TOKEN, CONFIG_BUCKET)",
        "7. Update IAM permissions for S3 access",
        "8. Update EventBridge rule to use multi-user mode",
        "9. Set Telegram webhook URL",
        "10. Test with /start command"
    ]
    
    for item in checklist:
        print(f"   □ {item}")
    
    print("\n📖 See TELEGRAM_BOT_SETUP.md for detailed instructions!")

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 TELEGRAM CAMPSITE BOT - LOCAL TESTING")
    print("=" * 60)
    print()
    
    # Run tests
    test_bot_commands()
    print("-" * 60)
    test_multi_user_lambda()
    print("-" * 60)
    print_sample_user_config()
    print("-" * 60)
    print_deployment_checklist()
    
    print("\n🎉 Testing complete! Ready to deploy your Telegram bot!")
