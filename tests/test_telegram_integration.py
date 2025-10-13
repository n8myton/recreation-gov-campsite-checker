#!/usr/bin/env python3
"""
Local Telegram Bot Integration Testing
Tests real Telegram API calls with mocked AWS services
"""

import json
import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  dotenv not available, make sure TELEGRAM_BOT_TOKEN is set in environment")

class LocalFileStorage:
    """Mock S3 with local file storage for testing"""
    def __init__(self):
        self.base_dir = tempfile.mkdtemp(prefix="campsite_bot_test_")
        print(f"📁 Using local storage: {self.base_dir}")
        
    def get_user_config_path(self, user_id):
        return os.path.join(self.base_dir, f"telegram_{user_id}.json")
    
    def load_user_config(self, user_id):
        """Load user config from local file"""
        config_path = self.get_user_config_path(user_id)
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Create default config for new user
            default_config = {
                "version": "1.0",
                "user_id": str(user_id),
                "notification_settings": {
                    "telegram_enabled": True,
                    "pushover_enabled": False,
                    "only_notify_on_availability": True,
                    "include_search_name_in_notification": True
                },
                "searches": []
            }
            self.save_user_config(user_id, default_config)
            return default_config
    
    def save_user_config(self, user_id, config):
        """Save user config to local file"""
        config_path = self.get_user_config_path(user_id)
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

def create_mock_s3_client(storage):
    """Create a mock S3 client that uses local file storage"""
    mock_s3 = Mock()
    
    def mock_get_object(Bucket, Key):
        # Extract user_id from key like "users/telegram_123456789.json"
        if Key.startswith("users/telegram_") and Key.endswith(".json"):
            user_id = Key.replace("users/telegram_", "").replace(".json", "")
            config = storage.load_user_config(user_id)
            
            # Create proper mock response structure
            response = {
                'Body': Mock()
            }
            response['Body'].read = Mock(return_value=json.dumps(config).encode('utf-8'))
            return response
        else:
            # Create proper S3 exception
            from botocore.exceptions import ClientError
            raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
    
    def mock_put_object(Bucket, Key, Body, ContentType=None):
        if Key.startswith("users/telegram_") and Key.endswith(".json"):
            user_id = Key.replace("users/telegram_", "").replace(".json", "")
            config = json.loads(Body.decode('utf-8') if isinstance(Body, bytes) else Body)
            return storage.save_user_config(user_id, config)
        return True
    
    def mock_list_objects_v2(Bucket, Prefix=""):
        # For multi-user functionality
        if Prefix == "users/telegram_":
            # Return empty for now (no users)
            return {}
        return {}
    
    mock_s3.get_object = mock_get_object
    mock_s3.put_object = mock_put_object  
    mock_s3.list_objects_v2 = mock_list_objects_v2
    
    # Create proper exception class
    mock_s3.exceptions = Mock()
    mock_s3.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})
    
    return mock_s3

def simulate_telegram_webhook(command, user_id="123456789", chat_id="123456789"):
    """Simulate a Telegram webhook call"""
    return {
        "body": json.dumps({
            "message": {
                "message_id": 1,
                "from": {
                    "id": int(user_id),
                    "is_bot": False,
                    "first_name": "TestUser",
                    "username": "testuser"
                },
                "chat": {
                    "id": int(chat_id),
                    "first_name": "TestUser", 
                    "username": "testuser",
                    "type": "private"
                },
                "date": int(datetime.now().timestamp()),
                "text": command
            }
        })
    }

def test_telegram_integration():
    """Test with real Telegram API"""
    print("🤖 TELEGRAM BOT - REAL API INTEGRATION TEST")
    print("=" * 60)
    
    # Check if token is available
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment!")
        print("   Make sure your .env file contains TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    print(f"✅ Bot token found: ...{bot_token[-10:]}")
    
    # Set up local storage
    storage = LocalFileStorage()
    mock_s3 = create_mock_s3_client(storage)
    
    # Test user
    test_user_id = "123456789"
    test_chat_id = "123456789"
    
    print(f"\n📱 Testing with user ID: {test_user_id}")
    print("=" * 60)
    
    # Import the handler
    from telegram_bot_handler import lambda_handler
    
    # Patch boto3 to use our mock
    with patch('boto3.client', return_value=mock_s3):
        
        print("\n1. Testing /start command:")
        print("-" * 30)
        event = simulate_telegram_webhook("/start", test_user_id, test_chat_id)
        os.environ['CONFIG_BUCKET'] = 'test-bucket'
        
        try:
            response = lambda_handler(event, None)
            print(f"   Status: {response['statusCode']}")
            if response['statusCode'] == 200:
                print("   ✅ /start command sent successfully!")
            else:
                print(f"   ❌ Error: {response.get('body', 'Unknown error')}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        print("\n2. Testing /add command:")
        print("-" * 30)
        add_command = '/add "Local Test Search" 2025-12-15 2025-12-17 232448'
        event = simulate_telegram_webhook(add_command, test_user_id, test_chat_id)
        
        try:
            response = lambda_handler(event, None)
            print(f"   Status: {response['statusCode']}")
            if response['statusCode'] == 200:
                print("   ✅ /add command sent successfully!")
                
                # Check if config was saved locally
                config = storage.load_user_config(test_user_id)
                if config and config.get('searches'):
                    print(f"   ✅ Search saved locally: '{config['searches'][0]['name']}'")
                else:
                    print("   ⚠️  Search may not have been saved")
            else:
                print(f"   ❌ Error: {response.get('body', 'Unknown error')}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        print("\n3. Testing /list command:")
        print("-" * 30)
        event = simulate_telegram_webhook("/list", test_user_id, test_chat_id)
        
        try:
            response = lambda_handler(event, None)
            print(f"   Status: {response['statusCode']}")
            if response['statusCode'] == 200:
                print("   ✅ /list command sent successfully!")
            else:
                print(f"   ❌ Error: {response.get('body', 'Unknown error')}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

def get_bot_info():
    """Get information about your bot"""
    print("\n🤖 BOT INFORMATION")
    print("=" * 30)
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ No bot token found")
        return
    
    import urllib.request
    import urllib.parse
    
    try:
        # Get bot info
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        with urllib.request.urlopen(url) as response:
            result = json.loads(response.read().decode())
        
        if result.get('ok'):
            bot_info = result['result']
            print(f"✅ Bot Name: {bot_info.get('first_name', 'Unknown')}")
            print(f"✅ Bot Username: @{bot_info.get('username', 'Unknown')}")
            print(f"✅ Bot ID: {bot_info.get('id', 'Unknown')}")
            
            # Check webhook status
            webhook_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            with urllib.request.urlopen(webhook_url) as response:
                webhook_result = json.loads(response.read().decode())
            
            if webhook_result.get('ok'):
                webhook_info = webhook_result['result']
                current_webhook = webhook_info.get('url', '')
                if current_webhook:
                    print(f"⚠️  Webhook currently set to: {current_webhook}")
                    print("   (This is normal if you have the bot deployed)")
                else:
                    print("✅ No webhook set (good for local testing)")
            
        else:
            print(f"❌ Error getting bot info: {result.get('description', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error connecting to Telegram API: {e}")

def interactive_test():
    """Interactive testing mode"""
    print("\n🎮 INTERACTIVE TEST MODE")
    print("=" * 30)
    print("You can now send test commands!")
    print("Commands: /start, /add, /list, /toggle, /delete, /help")
    print("Type 'quit' to exit\n")
    
    storage = LocalFileStorage()
    mock_s3 = create_mock_s3_client(storage)
    
    from telegram_bot_handler import lambda_handler
    
    test_user_id = input("Enter test user ID (or press Enter for '123456789'): ").strip()
    if not test_user_id:
        test_user_id = "123456789"
    
    os.environ['CONFIG_BUCKET'] = 'test-bucket'
    
    with patch('boto3.client', return_value=mock_s3):
        while True:
            command = input(f"\nUser {test_user_id}> ").strip()
            
            if command.lower() in ['quit', 'exit', 'q']:
                break
            
            if not command:
                continue
            
            event = simulate_telegram_webhook(command, test_user_id, test_user_id)
            
            try:
                response = lambda_handler(event, None)
                if response['statusCode'] == 200:
                    print("✅ Command sent successfully!")
                else:
                    print(f"❌ Error: {response.get('body', 'Unknown error')}")
            except Exception as e:
                print(f"❌ Exception: {e}")

if __name__ == "__main__":
    # Get bot info first
    get_bot_info()
    
    # Run integration tests
    test_telegram_integration()
    
    # Ask if they want interactive mode
    print("\n" + "=" * 60)
    choice = input("Run interactive test mode? (y/n): ").strip().lower()
    if choice in ['y', 'yes']:
        interactive_test()
    
    print("\n🎉 Local Telegram integration testing complete!")
    print("\n💡 If the tests worked, your bot is ready for deployment!")
    print("📖 Next: Follow TELEGRAM_BOT_SETUP.md for full AWS deployment")
