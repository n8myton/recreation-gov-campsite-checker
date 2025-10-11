#!/usr/bin/env python3
"""
Configure Telegram Bot Commands via API
Sets up the command menu and descriptions
"""

import json
import urllib.request
import urllib.parse
import os

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def set_bot_commands():
    """Set bot commands via Telegram API"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment!")
        print("   Make sure your .env file contains the bot token")
        return False
    
    print("🤖 CONFIGURING BOT COMMANDS")
    print("=" * 40)
    
    # Define the commands
    commands = [
        {
            "command": "start",
            "description": "🏕️ Welcome message and setup guide"
        },
        {
            "command": "add", 
            "description": "➕ Add a new campsite search"
        },
        {
            "command": "list",
            "description": "📋 Show your active searches"
        },
        {
            "command": "toggle",
            "description": "🔄 Enable/disable a search"
        },
        {
            "command": "delete", 
            "description": "🗑️ Remove a search"
        },
        {
            "command": "check",
            "description": "🔍 Manually check all searches now"
        },
        {
            "command": "help",
            "description": "❓ Show available commands"
        }
    ]
    
    try:
        # Set commands via API
        url = f"https://api.telegram.org/bot{bot_token}/setMyCommands"
        
        data = urllib.parse.urlencode({
            "commands": json.dumps(commands)
        }).encode()
        
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
        
        if result.get('ok'):
            print("✅ Bot commands configured successfully!")
            print("\nConfigured commands:")
            for cmd in commands:
                print(f"   /{cmd['command']} - {cmd['description']}")
            
            print(f"\n🎉 Users will now see these commands in their Telegram app!")
            print("   Commands appear when they type '/' in the chat")
            return True
            
        else:
            print(f"❌ Failed to set commands: {result.get('description', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting commands: {e}")
        return False

def get_current_commands():
    """Get currently configured commands"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMyCommands"
        
        with urllib.request.urlopen(url) as response:
            result = json.loads(response.read().decode())
        
        if result.get('ok'):
            commands = result.get('result', [])
            if commands:
                print("\n📋 Current bot commands:")
                for cmd in commands:
                    print(f"   /{cmd['command']} - {cmd['description']}")
            else:
                print("\n📋 No commands currently configured")
        else:
            print(f"❌ Error getting commands: {result.get('description', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error getting current commands: {e}")

def test_bot_info():
    """Test bot connection and get info"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        with urllib.request.urlopen(url) as response:
            result = json.loads(response.read().decode())
        
        if result.get('ok'):
            bot_info = result['result']
            print(f"🤖 Bot Info:")
            print(f"   Name: {bot_info.get('first_name', 'Unknown')}")
            print(f"   Username: @{bot_info.get('username', 'Unknown')}")
            print(f"   ID: {bot_info.get('id', 'Unknown')}")
            return True
        else:
            print(f"❌ Bot error: {result.get('description', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("🛠️  TELEGRAM BOT COMMAND CONFIGURATION")
    print("=" * 50)
    
    # Test connection first
    if test_bot_info():
        # Show current commands
        get_current_commands()
        
        # Ask if they want to set commands
        print("\n" + "=" * 50)
        choice = input("Set/update bot commands? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            if set_bot_commands():
                print("\n✅ Commands configured! Users will see them in Telegram.")
            else:
                print("\n❌ Command configuration failed.")
        else:
            print("⏭️  Skipped command configuration")
    
    print("\n🎉 Bot configuration complete!")
