#!/usr/bin/env python3
"""
Telegram Bot Handler for Campsite Checker
Handles user interactions and manages per-user campsite search configurations.
"""

import json
import urllib.request
import urllib.parse
import os
import boto3
from datetime import datetime, timedelta
import re

# Load environment variables when running locally
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv()
except ImportError:
    pass

def send_telegram_notification(chat_id, text, bot_token, reply_markup=None):
    """Send a message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    
    data_encoded = urllib.parse.urlencode(data).encode()
    
    req = urllib.request.Request(url, data=data_encoded)
    with urllib.request.urlopen(req) as response:
        result = response.read().decode()
    
    return json.loads(result)

def load_user_config(bucket_name, user_id):
    """Load user-specific search configuration from S3"""
    s3 = boto3.client('s3')
    config_key = f"users/telegram_{user_id}.json"
    
    try:
        response = s3.get_object(Bucket=bucket_name, Key=config_key)
        config_content = response['Body'].read().decode('utf-8')
        return json.loads(config_content)
    except s3.exceptions.NoSuchKey:
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
        save_user_config(bucket_name, user_id, default_config)
        return default_config
    except Exception as e:
        print(f"Error loading user config for {user_id}: {e}")
        return None

def save_user_config(bucket_name, user_id, config):
    """Save user-specific search configuration to S3"""
    s3 = boto3.client('s3')
    config_key = f"users/telegram_{user_id}.json"
    
    try:
        config_content = json.dumps(config, indent=2)
        s3.put_object(
            Bucket=bucket_name,
            Key=config_key,
            Body=config_content.encode('utf-8'),
            ContentType='application/json'
        )
        return True
    except Exception as e:
        print(f"Error saving user config for {user_id}: {e}")
        return False

def get_all_user_configs(bucket_name):
    """Get all user configurations for scheduled monitoring"""
    s3 = boto3.client('s3')
    user_configs = []
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix="users/telegram_")
        
        if 'Contents' not in response:
            return []
        
        for obj in response['Contents']:
            if obj['Key'].endswith('.json'):
                user_id = obj['Key'].replace('users/telegram_', '').replace('.json', '')
                config = load_user_config(bucket_name, user_id)
                if config:
                    user_configs.append(config)
        
        return user_configs
    except Exception as e:
        print(f"Error loading all user configs: {e}")
        return []

def parse_park_input(park_input):
    """Parse park input - accepts only park ID numbers or recreation.gov URLs"""
    # If it's a direct ID (all digits)
    if park_input.isdigit():
        return park_input
    
    # If it's a recreation.gov URL
    url_match = re.search(r'recreation\.gov/camping/campgrounds/(\d+)', park_input)
    if url_match:
        return url_match.group(1)
    
    # Park names are not supported - only numeric IDs and URLs
    return None

def handle_start_command(chat_id, bot_token):
    """Handle /start command"""
    welcome_message = """🏕️ *Welcome to Campsite Bot!*

I'll help you monitor recreation.gov campsites and notify you when sites become available.

*Available Commands:*
• `/add` - Add a new campsite search
• `/list` - Show your active searches
• `/toggle <name>` - Enable/disable a search
• `/delete <name>` - Remove a search
• `/deleteall` - Remove all searches (reset)
• `/check` - Manually check all your searches
• `/help` - Show this help message

*Getting Started:*
1. Use `/add` to create your first search
2. I'll check every minute automatically
3. You'll get notified here when sites are found!

Let's find you some campsites! 🎉"""
    
    return send_telegram_notification(chat_id, welcome_message, bot_token)

def handle_add_command(chat_id, message_text, bot_token, bucket_name, user_id):
    """Handle /add command with guided search creation"""
    # Format: /add "Search Name" YYYY-MM-DD YYYY-MM-DD park_id
    
    # Better parsing to handle quoted search names
    import re
    
    # Try to parse quoted search name first - handle both straight and curly quotes (iOS smart quotes)
    # Straight quotes: "text" 
    # Curly quotes: "text" (iOS default)
    # Mixed quotes: "text" or "text" (possible edge cases)
    quoted_pattern = r'/add\s+["""]([^"""]+)[""]\s+(\S+)\s+(\S+)\s+(.+)'
    match = re.match(quoted_pattern, message_text)
    
    if match:
        search_name = match.group(1)
        start_date = match.group(2)
        end_date = match.group(3)
        park_input = match.group(4)
        
        # Clean up search name - strip any remaining quotes that might have been captured
        # Handle both straight quotes (") and curly quotes (" ")
        search_name = search_name.strip('"').strip('\u201c').strip('\u201d')
    else:
        # Smarter fallback parsing without quotes - look for date patterns
        parts = message_text.split()
        if len(parts) < 4:
            help_message = """📝 *Add New Search*

Format: `/add "Search Name" start_date end_date park_id`

*Examples:*
• `/add "Yosemite Trip" 2025-07-04 2025-07-06 232448`
• `/add "Christmas Camping" 2025-10-15 2025-10-17 232472`
• `/add "Grand Canyon Camping" 2025-08-01 2025-08-03 232266`

*Finding Park IDs:*
• Visit recreation.gov and search for your campground
• When you view campsites, check the URL - it will contain the park ID
• Example: `recreation.gov/camping/campgrounds/232448` → Park ID is `232448`
"""
            
            return send_telegram_notification(chat_id, help_message, bot_token)
        
        # Look for date patterns to identify where search name ends
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        search_name = None
        start_date = None
        end_date = None
        park_input = None
        
        # Find the first date in the parts
        date_start_index = None
        for i, part in enumerate(parts[1:], 1):  # Skip '/add'
            if re.match(date_pattern, part):
                date_start_index = i
                break
        
        if date_start_index is None or date_start_index + 1 >= len(parts):
            # No date found or not enough parts after first date
            help_message = """❌ *Invalid Format*

I couldn't find valid dates in your command. 

*Format:* `/add "Search Name" start_date end_date park_id`

*Examples:*
• `/add "Yosemite Trip" 2025-07-04 2025-07-06 232448`
• `/add Jtree 2025-07-04 2025-07-06 232472`

*Park ID required - find it in the recreation.gov campground URL*"""
            
            return send_telegram_notification(chat_id, help_message, bot_token)
        
        # Check if we have a second date
        if date_start_index + 1 < len(parts) and re.match(date_pattern, parts[date_start_index + 1]):
            # We have both dates
            search_name = ' '.join(parts[1:date_start_index])
            start_date = parts[date_start_index]
            end_date = parts[date_start_index + 1]
            if date_start_index + 2 < len(parts):
                park_input = ' '.join(parts[date_start_index + 2:])
            else:
                park_input = None
        else:
            # Only one date found - malformed
            help_message = """❌ *Invalid Format*

I found only one date. Please provide both start and end dates.

*Format:* `/add "Search Name" start_date end_date park_id`

*Examples:*
• `/add "Yosemite Trip" 2025-07-04 2025-07-06 232448`
• `/add Jtree 2025-07-04 2025-07-06 232472`"""
            
            return send_telegram_notification(chat_id, help_message, bot_token)
        
        # Validate we have all required parts
        if not search_name or not search_name.strip():
            help_message = """❌ *Missing Search Name*

Please provide a name for your search.

*Format:* `/add "Search Name" start_date end_date park_id`"""
            
            return send_telegram_notification(chat_id, help_message, bot_token)
            
        if not park_input or not park_input.strip():
            help_message = """❌ *Missing Park Information*

Please provide the park ID number.

*Format:* `/add "Search Name" start_date end_date park_id`

*Examples:*
• `/add "Yosemite Trip" 2025-07-04 2025-07-06 232448`
• `/add "Joshua Tree" 2025-10-15 2025-10-17 232472`

*Find Park IDs:* Visit recreation.gov, search for your campground, and copy the ID from the URL."""
            
            return send_telegram_notification(chat_id, help_message, bot_token)
        
        search_name = search_name.strip()
        park_input = park_input.strip()
        
        # Clean up search name - strip any quotes that might have been included
        # Handle both straight quotes (") and curly quotes (" ")
        search_name = search_name.strip('"').strip('\u201c').strip('\u201d')
        
    try:
        # Validate dates
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            if start_dt >= end_dt:
                raise ValueError("End date must be after start date")
            # Allow dates that are today or in the future (give some flexibility)
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if start_dt < today:
                raise ValueError("Start date must be today or in the future")
        except ValueError as e:
            return send_telegram_notification(chat_id, f"❌ Invalid date: {str(e)}", bot_token)
        
        # Parse park
        park_id = parse_park_input(park_input)
        if not park_id:
            return send_telegram_notification(
                chat_id, 
                f"❌ Invalid park ID '{park_input}'. Please use a numeric park ID from recreation.gov URLs (e.g., 232448).",
                bot_token
            )
        
        # Load user config
        config = load_user_config(bucket_name, user_id)
        if not config:
            return send_telegram_notification(chat_id, "❌ Error loading your configuration", bot_token)
        
        # Create new search
        new_search = {
            "name": search_name,
            "enabled": True,
            "parks": [park_id],
            "start_date": start_date,
            "end_date": end_date,
            "campsite_type": None,
            "campsite_ids": [],
            "nights": (end_dt - start_dt).days,
            "weekends_only": False,
            "priority": "normal",
            "created_at": datetime.now().isoformat(),
            "last_availability_state": None  # Initialize state tracking for smart notifications
        }
        
        # Check for duplicate names (case-insensitive)
        existing_names = [s["name"].lower() for s in config["searches"]]
        if search_name.lower() in existing_names:
            return send_telegram_notification(
                chat_id,
                f"❌ You already have a search named '{search_name}'. Use a different name or delete the existing one first.",
                bot_token
            )
        
        # Add search and save
        config["searches"].append(new_search)
        
        if save_user_config(bucket_name, user_id, config):
            success_message = f"""✅ *Added "{search_name}"!*

📅 *Dates:* {start_date} to {end_date}
🏕️ *Park:* {park_id}
🔔 *Status:* Enabled

I'll check this search every minute and notify you when sites become available! 🎉

Use `/list` to see all your searches."""
            
            return send_telegram_notification(chat_id, success_message, bot_token)
        else:
            return send_telegram_notification(chat_id, "❌ Error saving your search", bot_token)
            
    except Exception as e:
        return send_telegram_notification(chat_id, f"❌ Error adding search: {str(e)}", bot_token)

def handle_list_command(chat_id, bot_token, bucket_name, user_id):
    """Handle /list command"""
    config = load_user_config(bucket_name, user_id)
    if not config:
        return send_telegram_notification(chat_id, "❌ Error loading your configuration", bot_token)
    
    searches = config.get("searches", [])
    if not searches:
        message = """📋 *Your Searches*

You don't have any campsite searches yet!

Use `/add` to create your first search and start monitoring campsites. 🏕️"""
        return send_telegram_notification(chat_id, message, bot_token)
    
    message_parts = ["📋 *Your Searches*\n"]
    
    for i, search in enumerate(searches, 1):
        status = "🟢 Enabled" if search.get("enabled", True) else "🔴 Disabled"
        parks_text = ", ".join(search["parks"])
        
        search_text = f"""*{i}. {search["name"]}*
{status}
📅 {search["start_date"]} to {search["end_date"]}
🏕️ Parks: {parks_text}
🌙 Nights: {search.get("nights", "auto")}
"""
        message_parts.append(search_text)
    
    message_parts.append("\nUse `/toggle <name>` to enable/disable or `/delete <name>` to remove.")
    
    return send_telegram_notification(chat_id, "\n".join(message_parts), bot_token)

def handle_toggle_command(chat_id, message_text, bot_token, bucket_name, user_id):
    """Handle /toggle command"""
    parts = message_text.split(maxsplit=1)
    if len(parts) < 2:
        return send_telegram_notification(
            chat_id,
            "Usage: `/toggle <search_name>`\n\nExample: `/toggle Yosemite Trip`",
            bot_token
        )
    
    search_name = parts[1]
    config = load_user_config(bucket_name, user_id)
    if not config:
        return send_telegram_notification(chat_id, "❌ Error loading your configuration", bot_token)
    
    # Find and toggle the search (case-insensitive)
    found = False
    found_search = None
    for search in config["searches"]:
        if search["name"].lower() == search_name.lower():
            found = True
            found_search = search
            search["enabled"] = not search.get("enabled", True)
            new_status = "enabled" if search["enabled"] else "disabled"
            
            if save_user_config(bucket_name, user_id, config):
                return send_telegram_notification(
                    chat_id,
                    f"✅ Search '{search['name']}' is now *{new_status}*",
                    bot_token
                )
            else:
                return send_telegram_notification(chat_id, "❌ Error saving changes", bot_token)
    
    if not found:
        return send_telegram_notification(
            chat_id,
            f"❌ Search '{search_name}' not found. Use `/list` to see your searches.",
            bot_token
        )

def handle_delete_command(chat_id, message_text, bot_token, bucket_name, user_id):
    """Handle /delete command"""
    parts = message_text.split(maxsplit=1)
    if len(parts) < 2:
        return send_telegram_notification(
            chat_id,
            "Usage: `/delete <search_name>`\n\nExample: `/delete Yosemite Trip`",
            bot_token
        )
    
    search_name = parts[1]
    config = load_user_config(bucket_name, user_id)
    if not config:
        return send_telegram_notification(chat_id, "❌ Error loading your configuration", bot_token)
    
    # Find and remove the search (case-insensitive)
    original_count = len(config["searches"])
    found_search_name = None
    
    # First find the actual search name (preserve original casing for response)
    for search in config["searches"]:
        if search["name"].lower() == search_name.lower():
            found_search_name = search["name"]
            break
    
    # Remove searches that match (case-insensitive)
    config["searches"] = [s for s in config["searches"] if s["name"].lower() != search_name.lower()]
    
    if len(config["searches"]) < original_count:
        if save_user_config(bucket_name, user_id, config):
            return send_telegram_notification(
                chat_id,
                f"✅ Deleted search '{found_search_name or search_name}'",
                bot_token
            )
        else:
            return send_telegram_notification(chat_id, "❌ Error saving changes", bot_token)
    else:
        return send_telegram_notification(
            chat_id,
            f"❌ Search '{search_name}' not found. Use `/list` to see your searches.",
            bot_token
        )

def handle_delete_all_command(chat_id, bot_token, bucket_name, user_id):
    """Handle /deleteall command to remove all searches"""
    config = load_user_config(bucket_name, user_id)
    if not config:
        return send_telegram_notification(chat_id, "❌ Error loading your configuration", bot_token)
    
    searches = config.get("searches", [])
    if not searches:
        return send_telegram_notification(
            chat_id,
            "❌ You don't have any searches to delete.\n\nUse `/add` to create your first search!",
            bot_token
        )
    
    search_count = len(searches)
    
    # Clear all searches
    config["searches"] = []
    
    if save_user_config(bucket_name, user_id, config):
        return send_telegram_notification(
            chat_id,
            f"✅ Deleted all {search_count} search(es)!\n\nYour campsite monitoring has been reset. Use `/add` to create new searches.",
            bot_token
        )
    else:
        return send_telegram_notification(chat_id, "❌ Error saving changes", bot_token)

def handle_manual_check_request(chat_id, bot_token, bucket_name, user_id):
    """Handle /check command - manually trigger campsite checking via existing Lambda"""
    print(f"🔍 DEBUG: Starting manual check for user {user_id}")
    
    config = load_user_config(bucket_name, user_id)
    if not config:
        print(f"❌ DEBUG: Failed to load config for user {user_id}")
        return send_telegram_notification(chat_id, "❌ Error loading your configuration", bot_token)
    
    print(f"🔍 DEBUG: Loaded config with {len(config.get('searches', []))} total searches")
    
    enabled_searches = [s for s in config.get("searches", []) if s.get("enabled", True)]
    if not enabled_searches:
        print(f"🔍 DEBUG: No enabled searches found")
        return send_telegram_notification(
            chat_id,
            "❌ You don't have any enabled searches to check.\n\nUse `/add` to create a search or `/toggle` to enable existing ones.",
            bot_token
        )
    
    print(f"🔍 DEBUG: Found {len(enabled_searches)} enabled searches")
    
    # Send initial status message
    status_message = f"🔍 Checking {len(enabled_searches)} search(es) for available campsites...\n\nThis may take a few moments."
    print(f"🔍 DEBUG: Sending initial status message")
    send_telegram_notification(chat_id, status_message, bot_token)
    
    try:
        # Invoke the existing campsite checking Lambda
        print(f"🔍 DEBUG: Invoking campbot Lambda for user {user_id}")
        lambda_client = boto3.client('lambda')
        
        # Prepare payload for the campsite checking Lambda
        payload = {
            'user_id': str(user_id),
            'manual_check': True,
            'telegram_chat_id': chat_id,
            'telegram_bot_token': bot_token
        }
        
        print(f"🔍 DEBUG: Lambda payload: {json.dumps(payload, indent=2)}")
        
        response = lambda_client.invoke(
            FunctionName='campbot',  # Your existing campsite checking Lambda
            Payload=json.dumps(payload)
        )
        
        print(f"🔍 DEBUG: Lambda invocation completed with StatusCode: {response['StatusCode']}")
        
        # Read the response
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"🔍 DEBUG: Lambda response: {json.dumps(response_payload, indent=2)}")
        
        # Check if the Lambda execution was successful
        if response['StatusCode'] == 200:
            if 'errorMessage' in response_payload:
                print(f"❌ DEBUG: Lambda returned error: {response_payload['errorMessage']}")
                error_msg = f"❌ Error during campsite check: {response_payload['errorMessage']}"
                return send_telegram_notification(chat_id, error_msg, bot_token)
            else:
                print(f"✅ DEBUG: Manual check completed successfully")
                # The campbot Lambda already sent detailed results and summary to Telegram
                # No need to send additional message here
                return {"statusCode": 200, "body": "OK"}
        else:
            print(f"❌ DEBUG: Lambda invocation failed with status code: {response['StatusCode']}")
            return send_telegram_notification(
                chat_id, 
                "❌ Error invoking campsite checker. Please try again later.",
                bot_token
            )
            
    except Exception as e:
        print(f"❌ DEBUG: Error invoking campbot Lambda: {str(e)}")
        print(f"❌ DEBUG: Error type: {type(e).__name__}")
        error_message = f"❌ Error during manual check: {str(e)}\n\nPlease try again or contact support if the issue persists."
        return send_telegram_notification(chat_id, error_message, bot_token)

def telegram_bot_handler(event, context):
    """
    Main Telegram Bot Lambda handler - processes incoming webhook messages
    """
    try:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        bucket_name = os.environ.get('CONFIG_BUCKET')
        
        if not bot_token:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "TELEGRAM_BOT_TOKEN not set"})
            }
        
        if not bucket_name:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "CONFIG_BUCKET not set"})
            }
        
        # Parse Telegram webhook
        if 'body' not in event:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No body in request"})
            }
        
        update = json.loads(event['body'])
        
        if 'message' not in update:
            return {"statusCode": 200, "body": "OK"}
        
        message = update['message']
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        text = message.get('text', '')
        
        print(f"Received message from user {user_id}: {text}")
        
        # Handle commands
        if text.startswith('/start'):
            handle_start_command(chat_id, bot_token)
        elif text.startswith('/add'):
            handle_add_command(chat_id, text, bot_token, bucket_name, user_id)
        elif text.startswith('/list'):
            handle_list_command(chat_id, bot_token, bucket_name, user_id)
        elif text.startswith('/toggle'):
            handle_toggle_command(chat_id, text, bot_token, bucket_name, user_id)
        elif text.startswith('/deleteall'):
            handle_delete_all_command(chat_id, bot_token, bucket_name, user_id)
        elif text.startswith('/delete'):
            handle_delete_command(chat_id, text, bot_token, bucket_name, user_id)
        elif text.startswith('/check'):
            handle_manual_check_request(chat_id, bot_token, bucket_name, user_id)
        elif text.startswith('/help'):
            handle_start_command(chat_id, bot_token)  # Same as start
        else:
            # Unknown command
            help_message = """❓ *Unknown Command*

*Available Commands:*
• `/add` - Add a new campsite search
• `/list` - Show your active searches  
• `/toggle <name>` - Enable/disable a search
• `/delete <name>` - Remove a search
• `/deleteall` - Remove all searches (reset)
• `/check` - Manually check all your searches
• `/help` - Show help message

Type `/help` for more details!"""
            
            send_telegram_notification(chat_id, help_message, bot_token)
        
        return {"statusCode": 200, "body": "OK"}
        
    except Exception as e:
        print(f"Error in Telegram bot handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

# AWS Lambda entry point (keeps existing name for compatibility)
def lambda_handler(event, context):
    """AWS Lambda entry point - delegates to telegram_bot_handler"""
    return telegram_bot_handler(event, context)
