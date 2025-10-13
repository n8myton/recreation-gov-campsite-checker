#!/usr/bin/env python3
"""
Test Telegram Notifications
Send test campsite notifications to verify bot messaging works
"""

import json
import urllib.request
import urllib.parse
import os
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def send_telegram_message(chat_id, message, bot_token, parse_mode="Markdown"):
    """Send a message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode
    }).encode()
    
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
    
    return result

def get_chat_id_instructions():
    """Show how to get chat_id"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return None
    
    print("📱 HOW TO GET YOUR CHAT ID:")
    print("=" * 40)
    print("1. Message your bot on Telegram: @desertcampbot")
    print("2. Send any message (like 'hello')")  
    print("3. Visit this URL in your browser:")
    print(f"   https://api.telegram.org/bot{bot_token}/getUpdates")
    print("4. Look for your message in the JSON response")
    print("5. Find the 'chat' object and copy the 'id' number")
    print()
    print("Example JSON structure:")
    print('''   {
     "result": [{
       "message": {
         "chat": {
           "id": 123456789,  <-- This is your chat_id
           "first_name": "Your Name"
         }
       }
     }]
   }''')
    print()
    
    return bot_token

def create_sample_notifications():
    """Create sample campsite notification messages"""
    notifications = [
        {
            "title": "🏕 YOSEMITE FOUND!",
            "message": """🎉 *FOUND: Yosemite Summer Trip*

there are campsites available from 2025-07-04 to 2025-07-06!!! 🏕🏕🏕

12 site(s) available in Yosemite Valley Campground
3 site(s) available in Bridalveil Creek Campground

🏕 Book now! 🏕""",
            "description": "Campsite availability found"
        },
        {
            "title": "🔍 Manual Check Complete",
            "message": """✅ *Manual Check Complete!*

🎉 Found availability in 2 of 3 searches!

I checked:
• Yosemite Summer Trip ✅ *Available*
• Joshua Tree October ❌ No availability  
• Death Valley Weekend ✅ *Available*

Detailed results were sent above. 🏕️""",
            "description": "Manual check results"
        },
        {
            "title": "⚠️ Search Error",
            "message": """🚨 *Error checking 'Grand Canyon Trip'*

The recreation.gov API is temporarily unavailable. I'll keep trying automatically.

Your other searches are still being monitored normally.""",
            "description": "Error notification"
        },
        {
            "title": "🎉 Welcome",
            "message": """🏕️ *Welcome to Campsite Bot!*

I'll help you monitor recreation.gov campsites and notify you when sites become available.

*Available Commands:*
• `/add` - Add a new campsite search
• `/list` - Show your active searches
• `/check` - Manually check all your searches

Let's find you some campsites! 🎉""",
            "description": "Welcome message"
        }
    ]
    
    return notifications

def test_notification_formatting():
    """Test notification message formatting"""
    print("🧪 TESTING NOTIFICATION FORMATTING")
    print("=" * 50)
    
    notifications = create_sample_notifications()
    
    for i, notification in enumerate(notifications, 1):
        print(f"\n{i}. {notification['description'].upper()}")
        print("-" * 30)
        print(f"Title: {notification['title']}")
        print("Message:")
        print(notification['message'])
        print()

def send_test_notifications():
    """Send test notifications to Telegram"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        return
    
    print("🚀 SEND TEST NOTIFICATIONS")
    print("=" * 40)
    
    chat_id = input("Enter your chat_id (or 'skip' to skip): ").strip()
    
    if not chat_id or chat_id.lower() == 'skip':
        print("⏭️  Skipped sending test notifications")
        return
    
    # Validate chat_id is numeric
    try:
        int(chat_id)
    except ValueError:
        print("❌ Chat ID must be a number")
        return
    
    notifications = create_sample_notifications()
    
    print(f"\n📤 Sending test notifications to chat_id: {chat_id}")
    
    for i, notification in enumerate(notifications, 1):
        print(f"\n{i}. Sending: {notification['description']}")
        
        try:
            result = send_telegram_message(
                chat_id, 
                notification['message'], 
                bot_token
            )
            
            if result.get('ok'):
                print(f"   ✅ Sent successfully! Message ID: {result['result']['message_id']}")
            else:
                print(f"   ❌ Failed: {result.get('description', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        # Small delay between messages
        import time
        time.sleep(1)
    
    print(f"\n🎉 Test notifications complete!")
    print("Check your Telegram app to see how they look!")

def quick_message_test():
    """Send a quick test message"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        return
    
    print("⚡ QUICK MESSAGE TEST")
    print("=" * 30)
    
    chat_id = input("Enter your chat_id: ").strip()
    if not chat_id:
        print("⏭️  Skipped")
        return
    
    test_message = f"""🧪 *Test Message*

Hello from your campsite bot! 

This is a test sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

If you can see this, the bot messaging is working perfectly! ✅"""
    
    try:
        result = send_telegram_message(chat_id, test_message, bot_token)
        
        if result.get('ok'):
            print("✅ Test message sent successfully!")
            print(f"   Message ID: {result['result']['message_id']}")
        else:
            print(f"❌ Failed: {result.get('description', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("📱 TELEGRAM NOTIFICATION TESTING")
    print("=" * 50)
    
    # Check bot token
    bot_token = get_chat_id_instructions()
    if not bot_token:
        print("❌ No bot token found. Check your .env file.")
        exit(1)
    
    print("=" * 50)
    print("Choose a test option:")
    print("1. Show notification formatting (no sending)")
    print("2. Send quick test message")
    print("3. Send sample campsite notifications")
    print("4. Show chat_id instructions again")
    
    try:
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            test_notification_formatting()
        elif choice == "2":
            quick_message_test()
        elif choice == "3":
            send_test_notifications()
        elif choice == "4":
            get_chat_id_instructions()
        else:
            print("Invalid choice")
            
    except EOFError:
        # Non-interactive mode - just show formatting
        print("Running in non-interactive mode...")
        test_notification_formatting()
    
    print("\n🎉 Telegram notification testing complete!")
