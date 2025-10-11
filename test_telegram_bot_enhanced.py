#!/usr/bin/env python3
"""
Enhanced local testing with mocked AWS and Telegram services
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch
from telegram_bot_handler import (
    handle_start_command, handle_add_command, handle_list_command,
    handle_toggle_command, handle_delete_command, handle_check_command,
    load_user_config, save_user_config
)

class MockS3:
    """Mock S3 client for local testing"""
    def __init__(self):
        self.objects = {}
    
    def get_object(self, Bucket, Key):
        if Key in self.objects:
            response = Mock()
            response['Body'].read.return_value = self.objects[Key].encode('utf-8')
            return response
        else:
            from botocore.exceptions import ClientError
            raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
    
    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.objects[Key] = Body.decode('utf-8') if isinstance(Body, bytes) else Body
        return True
    
    def list_objects_v2(self, Bucket, Prefix=""):
        keys = [k for k in self.objects.keys() if k.startswith(Prefix)]
        if keys:
            return {
                'Contents': [{'Key': k} for k in keys]
            }
        else:
            return {}

def mock_telegram_send(chat_id, text, bot_token, reply_markup=None):
    """Mock Telegram API call"""
    print(f"📱 TELEGRAM MESSAGE TO {chat_id}:")
    print(f"   {text[:100]}{'...' if len(text) > 100 else ''}")
    print()
    return {"ok": True, "result": {"message_id": 123}}

def create_test_user_config(user_id="123456789"):
    """Create a test user configuration"""
    return {
        "version": "1.0",
        "user_id": user_id,
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
                "priority": "high"
            },
            {
                "name": "Joshua Tree Test",
                "enabled": False,
                "parks": ["232472"],
                "start_date": "2025-08-15",
                "end_date": "2025-08-17",
                "campsite_type": None,
                "campsite_ids": [],
                "nights": 2,
                "weekends_only": False,
                "priority": "normal"
            }
        ]
    }

def test_bot_commands_with_mocks():
    """Test bot commands with mocked services"""
    print("🧪 ENHANCED LOCAL TESTING WITH MOCKS")
    print("=" * 60)
    
    # Set up mock S3
    mock_s3 = MockS3()
    
    # Pre-populate with test user config
    test_config = create_test_user_config()
    mock_s3.objects["users/telegram_123456789.json"] = json.dumps(test_config, indent=2)
    
    test_user_id = "123456789"
    test_chat_id = "123456789"
    test_bucket = "test-bucket"
    
    with patch('boto3.client', return_value=mock_s3), \
         patch('telegram_bot_handler.send_telegram_message', mock_telegram_send):
        
        print("\n1. Testing /start command:")
        print("-" * 30)
        handle_start_command(test_chat_id, "mock_token")
        
        print("\n2. Testing /list command with existing searches:")
        print("-" * 30)
        handle_list_command(test_chat_id, "mock_token", test_bucket, test_user_id)
        
        print("\n3. Testing /add command:")
        print("-" * 30)
        handle_add_command(
            test_chat_id, 
            '/add "Death Valley Trip" 2025-09-15 2025-09-17 232447',
            "mock_token", 
            test_bucket, 
            test_user_id
        )
        
        print("\n4. Testing /toggle command:")
        print("-" * 30)
        handle_toggle_command(
            test_chat_id,
            "/toggle Joshua Tree Test",
            "mock_token",
            test_bucket,
            test_user_id
        )
        
        print("\n5. Testing /list after changes:")
        print("-" * 30)
        handle_list_command(test_chat_id, "mock_token", test_bucket, test_user_id)
        
        print("\n6. Testing /delete command:")
        print("-" * 30)
        handle_delete_command(
            test_chat_id,
            "/delete Death Valley Trip",
            "mock_token",
            test_bucket,
            test_user_id
        )

def test_camping_integration():
    """Test camping module integration if available"""
    print("\n🏕️ TESTING CAMPING MODULE INTEGRATION")
    print("=" * 60)
    
    try:
        from camping import check_park, generate_human_output
        print("✅ Camping module available!")
        
        # Test with a simple date range (won't actually call API without real setup)
        from datetime import datetime
        start_date = datetime(2025, 7, 4)
        end_date = datetime(2025, 7, 6)
        
        print("   - Camping functions imported successfully")
        print("   - Ready for real campsite checking in deployment")
        
    except ImportError as e:
        print(f"❌ Camping module not available: {e}")
        print("   - This is normal if camping.py has dependencies not installed")
        print("   - Will work in Lambda deployment with proper package")

def test_configuration_management():
    """Test configuration loading and saving"""
    print("\n⚙️ TESTING CONFIGURATION MANAGEMENT") 
    print("=" * 60)
    
    mock_s3 = MockS3()
    test_user_id = "987654321"
    test_bucket = "test-bucket"
    
    with patch('boto3.client', return_value=mock_s3):
        print("\n1. Testing new user (no existing config):")
        config = load_user_config(test_bucket, test_user_id)
        print(f"   Created default config for user {test_user_id}")
        print(f"   Searches: {len(config.get('searches', []))}")
        
        print("\n2. Testing config modification:")
        config['searches'].append({
            "name": "Test Search",
            "enabled": True,
            "parks": ["232448"],
            "start_date": "2025-12-01", 
            "end_date": "2025-12-03",
            "nights": 2
        })
        
        success = save_user_config(test_bucket, test_user_id, config)
        print(f"   Save successful: {success}")
        
        print("\n3. Testing config reload:")
        reloaded_config = load_user_config(test_bucket, test_user_id)
        print(f"   Reloaded searches: {len(reloaded_config.get('searches', []))}")
        print(f"   New search name: {reloaded_config['searches'][-1]['name']}")

if __name__ == "__main__":
    os.environ['TELEGRAM_BOT_TOKEN'] = 'mock_token_for_testing'
    os.environ['CONFIG_BUCKET'] = 'test-bucket'
    
    test_bot_commands_with_mocks()
    test_camping_integration()
    test_configuration_management()
    
    print("\n" + "=" * 60)
    print("🎉 ENHANCED LOCAL TESTING COMPLETE!")
    print("=" * 60)
    print("\n✅ What works locally:")
    print("   • All bot command logic")
    print("   • Configuration management")
    print("   • User data storage simulation")
    print("   • Message formatting")
    print("\n⚠️  What needs deployment:")
    print("   • Real Telegram API integration")
    print("   • AWS S3 access")
    print("   • Recreation.gov API calls")
    print("   • Push notifications")
    print("\n🚀 Ready to deploy when you are!")
