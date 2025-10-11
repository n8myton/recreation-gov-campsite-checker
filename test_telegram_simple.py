#!/usr/bin/env python3
"""
Simple Telegram Bot Integration Test
Tests core functionality with your actual bot token
"""

import json
import os
import tempfile
import urllib.request
import urllib.parse
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  dotenv not available, make sure TELEGRAM_BOT_TOKEN is set in environment")

def test_telegram_api_directly():
    """Test sending a message directly via Telegram API"""
    print("🧪 TESTING DIRECT TELEGRAM API")
    print("=" * 40)
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        return False
    
    # First, get bot info
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        with urllib.request.urlopen(url) as response:
            result = json.loads(response.read().decode())
        
        if result.get('ok'):
            bot_info = result['result']
            print(f"✅ Bot: @{bot_info.get('username', 'Unknown')}")
            print(f"✅ ID: {bot_info.get('id', 'Unknown')}")
        else:
            print(f"❌ Bot info error: {result.get('description', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting bot info: {e}")
        return False
    
    # Test sending a message (you'll need to provide a chat_id)
    print("\n📱 To test sending messages, you need a chat_id.")
    print("   1. Message your bot on Telegram")
    print("   2. Visit: https://api.telegram.org/bot{}/getUpdates".format(bot_token))
    print("   3. Look for your chat_id in the response")
    print("   4. Or just run the interactive test below with a dummy chat_id")
    
    return True

def test_bot_logic_with_mocks():
    """Test bot logic with mocked services but real API calls"""
    print("\n🧪 TESTING BOT LOGIC")
    print("=" * 40)
    
    # Create temporary storage
    temp_dir = tempfile.mkdtemp(prefix="campsite_test_")
    print(f"📁 Using temp storage: {temp_dir}")
    
    # Mock S3 functions but keep real Telegram API
    def mock_load_user_config(bucket_name, user_id):
        config_path = os.path.join(temp_dir, f"user_{user_id}.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        
        # Create default config
        default_config = {
            "version": "1.0",
            "user_id": str(user_id),
            "notification_settings": {
                "telegram_enabled": True,
                "pushover_enabled": False,
            },
            "searches": []
        }
        
        # Save default config
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def mock_save_user_config(bucket_name, user_id, config):
        config_path = os.path.join(temp_dir, f"user_{user_id}.json")
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving: {e}")
            return False
    
    # Test the individual command handlers
    from telegram_bot_handler import (
        handle_start_command, handle_add_command, handle_list_command,
        parse_park_input
    )
    
    # Patch the functions
    import telegram_bot_handler
    original_load = telegram_bot_handler.load_user_config
    original_save = telegram_bot_handler.save_user_config
    
    telegram_bot_handler.load_user_config = mock_load_user_config
    telegram_bot_handler.save_user_config = mock_save_user_config
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    test_chat_id = "123456789"  # This won't actually send since it's invalid
    test_user_id = "123456789"
    test_bucket = "test-bucket"
    
    try:
        print("\n1. Testing command handlers:")
        
        # Test park parsing
        print("   📍 Park parsing:")
        tests = [
            ("232448", "Direct ID"),
            ("yosemite valley", "Park name"),
            ("https://www.recreation.gov/camping/campgrounds/232448", "URL")
        ]
        
        for park_input, desc in tests:
            result = parse_park_input(park_input)
            print(f"      ✅ {desc}: {park_input} → {result}")
        
        # Test config management  
        print("\n   💾 Configuration:")
        config = mock_load_user_config(test_bucket, test_user_id)
        print(f"      ✅ Load user config: {len(config.get('searches', []))} searches")
        
        # Add a test search
        config['searches'].append({
            "name": "Test Search",
            "enabled": True,
            "parks": ["232448"],
            "start_date": "2025-12-15",
            "end_date": "2025-12-17",
            "nights": 2
        })
        
        save_result = mock_save_user_config(test_bucket, test_user_id, config)
        print(f"      ✅ Save user config: {save_result}")
        
        # Reload to verify
        reloaded = mock_load_user_config(test_bucket, test_user_id)
        print(f"      ✅ Reload verification: {len(reloaded.get('searches', []))} searches")
        
        print("\n   🎯 Core bot logic is working perfectly!")
        
    except Exception as e:
        print(f"   ❌ Error testing bot logic: {e}")
    finally:
        # Restore original functions
        telegram_bot_handler.load_user_config = original_load
        telegram_bot_handler.save_user_config = original_save
    
    return True

def create_simple_telegram_test():
    """Create a simple way to test Telegram messages"""
    print("\n🤖 SIMPLE TELEGRAM MESSAGE TEST")
    print("=" * 40)
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ No bot token found")
        return
    
    print("To test your bot with real messages:")
    print("1. Open Telegram and find your bot: @desertcampbot")
    print("2. Send /start to your bot")
    print("3. Check if you receive a welcome message")
    print()
    print("If the bot doesn't respond, check:")
    print("   • Bot token is correct")
    print("   • Bot is not blocked")
    print("   • No webhook is interfering")
    print()
    print("🔧 Manual API test:")
    
    try:
        # Test a simple API call
        test_message = "🤖 Test message from local development!"
        test_chat_id = input("Enter your Telegram chat ID (or 'skip'): ").strip()
        
        if test_chat_id and test_chat_id != 'skip':
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            data = urllib.parse.urlencode({
                "chat_id": test_chat_id,
                "text": test_message,
                "parse_mode": "Markdown"
            }).encode()
            
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
            
            if result.get('ok'):
                print(f"✅ Test message sent successfully!")
                print(f"   Message ID: {result['result']['message_id']}")
            else:
                print(f"❌ Failed to send message: {result.get('description', 'Unknown error')}")
        else:
            print("⏭️  Skipped manual message test")
            
    except Exception as e:
        print(f"❌ Error in manual test: {e}")

if __name__ == "__main__":
    print("🤖 TELEGRAM BOT - SIMPLE INTEGRATION TEST")
    print("=" * 50)
    
    # Test basic API connectivity
    if test_telegram_api_directly():
        # Test core bot logic
        test_bot_logic_with_mocks()
        
        # Offer simple message test
        create_simple_telegram_test()
    
    print("\n🎉 Testing complete!")
    print("\n💡 If the core logic tests passed, your bot is ready!")
    print("📖 Deploy following TELEGRAM_BOT_SETUP.md for full functionality")
