#!/usr/bin/env python3
"""
Multi-user Production Lambda function for scheduled campsite monitoring.
Loads search configurations from S3 for all users and checks multiple campsite/date combinations.
Supports both legacy single-user mode and new multi-user Telegram bot mode.
"""

import json
import urllib.request
import urllib.parse
import os
import boto3
from datetime import datetime, timedelta
import re

# Load environment variables when running locally (only import dotenv if available)
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv()
except ImportError:
    # dotenv not available (e.g., in Lambda), which is fine
    pass

# Import your camping functionality
try:
    from camping import generate_human_output, check_park
    CAMPING_AVAILABLE = True
except ImportError:
    CAMPING_AVAILABLE = False
    print("Warning: camping module not available")

def send_pushover_notification(message, title="Campsite Alert", priority=0):
    """Send a notification via Pushover"""
    user_key = os.environ.get('PUSHOVER_USER_KEY')
    api_token = os.environ.get('PUSHOVER_API_TOKEN')
    
    if not user_key or not api_token:
        raise ValueError("PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN environment variables must be set")

    data = urllib.parse.urlencode({
        "token": api_token,
        "user": user_key,
        "message": message,
        "title": title,
        "priority": priority
    }).encode()

    req = urllib.request.Request("https://api.pushover.net/1/messages.json", data=data)
    with urllib.request.urlopen(req) as response:
        result = response.read().decode()
    
    return json.loads(result)

def load_search_config(bucket_name=None, config_key="campsite_searches.json"):
    """
    Load search configuration from S3 or local file (legacy single-user mode)
    """
    if bucket_name:
        # Load from S3 (production)
        s3 = boto3.client('s3')
        try:
            response = s3.get_object(Bucket=bucket_name, Key=config_key)
            config_content = response['Body'].read().decode('utf-8')
            return json.loads(config_content)
        except Exception as e:
            print(f"Error loading config from S3: {e}")
            return None
    else:
        # Load from local file (testing)
        try:
            with open(config_key, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading local config: {e}")
            return None

def load_user_config(bucket_name, user_id):
    """Load user-specific search configuration from S3"""
    s3 = boto3.client('s3')
    config_key = f"users/telegram_{user_id}.json"
    
    try:
        response = s3.get_object(Bucket=bucket_name, Key=config_key)
        config_content = response['Body'].read().decode('utf-8')
        return json.loads(config_content)
    except s3.exceptions.NoSuchKey:
        return None
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
                if config and config.get("searches"):
                    # Add metadata for notification routing
                    config['_user_id'] = user_id
                    user_configs.append(config)
        
        return user_configs
    except Exception as e:
        print(f"Error loading all user configs: {e}")
        return []

def format_campsite_availability_message(camping_output, has_availabilities, search_name=None):
    """
    Format camping availability results into a nice notification message
    """
    SUCCESS_EMOJI = "🏕"
    FAILURE_EMOJI = "❌"
    
    if "Something went wrong" in camping_output:
        title = "🚨 Campbot Error"
        if search_name:
            message = f"🚨 Error checking '{search_name}': Campbot is broken! Please help :'("
        else:
            message = "🚨 Campbot is broken! Please help :'("
        return message, title, 1
    
    if not has_availabilities:
        return None, None, 0  # Don't notify for no availability
    
    # Parse the camping output to extract available sites
    lines = camping_output.strip().split('\n')
    first_line = lines[0] if lines else "Campsites found!"
    
    available_site_strings = []
    for line in lines:
        if SUCCESS_EMOJI in line and ":" in line:
            # Extract park name and availability count
            parts = line.split(":")
            if len(parts) >= 2:
                park_part = parts[0].replace(SUCCESS_EMOJI, "").strip()
                available_part = parts[1].strip()
                available_count = available_part.split(" ")[0]
                park_name = park_part.split("(")[0].strip()
                available_site_strings.append(f"{available_count} site(s) available in {park_name}")
    
    if available_site_strings:
        # Create an exciting notification message
        if search_name:
            message = f"🎉 FOUND: {search_name}\n\n{first_line} 🏕🏕🏕\n\n"
        else:
            message = f"🎉 {first_line} 🏕🏕🏕\n\n"
        
        message += "\n".join(available_site_strings)
        message += f"\n\n🏕 Book now! 🏕"
        
        title = f"🏕 CAMPSITES FOUND!"
        if search_name:
            title = f"🏕 {search_name.upper()}"
        
        return message, title, 1  # High priority for availability
    
    return None, None, 0  # Don't notify if no specific availability found

def extract_site_count_from_output(camping_output):
    """Extract the total number of available sites from camping output"""
    if not camping_output:
        return 0
    
    total_sites = 0
    SUCCESS_EMOJI = "🏕"
    
    lines = camping_output.strip().split('\n')
    for line in lines:
        if SUCCESS_EMOJI in line and ":" in line:
            # Extract availability count from lines like "🏕 Park Name: 3 sites available"
            parts = line.split(":")
            if len(parts) >= 2:
                available_part = parts[1].strip()
                # Extract number from strings like "3 sites available" or "3 site(s) available"
                match = re.search(r'(\d+)\s+site', available_part, re.IGNORECASE)
                if match:
                    total_sites += int(match.group(1))
    
    return total_sites

def should_notify_availability_change(result, last_state):
    """
    Determine if we should notify based on availability state changes
    Returns: (should_notify, reason, new_state)
    """
    current_has_sites = result.get('has_availabilities', False)
    current_count = 0
    
    if current_has_sites:
        current_count = extract_site_count_from_output(result.get('camping_output', ''))
    
    # Create current state
    current_state = {
        'has_sites': current_has_sites,
        'site_count': current_count,
        'last_checked': datetime.now().isoformat()
    }
    
    # If no previous state, notify if we have availability
    if not last_state:
        if current_has_sites:
            return True, "first_availability_found", current_state
        else:
            return False, "no_availability", current_state
    
    previous_has_sites = last_state.get('has_sites', False)
    previous_count = last_state.get('site_count', 0)
    
    # Case 1: New availability (none → some)
    if current_has_sites and not previous_has_sites:
        return True, "new_availability", current_state
    
    # Case 2: Availability disappeared (some → none) - don't notify for this
    if not current_has_sites and previous_has_sites:
        return False, "availability_disappeared", current_state
    
    # Case 3: Both have availability - check for significant increases
    if current_has_sites and previous_has_sites:
        # Notify if availability doubled or increased by at least 3 sites
        if (current_count >= previous_count * 2 and current_count > previous_count + 2) or \
           (current_count >= previous_count + 5):
            return True, "significant_increase", current_state
        else:
            return False, "availability_unchanged", current_state
    
    # Case 4: No availability in either state
    return False, "no_availability", current_state

def update_search_availability_state(bucket_name, user_id, search_name, new_state):
    """Update the availability state for a specific search"""
    config = load_user_config(bucket_name, user_id)
    if not config:
        return False
    
    # Find the search and update its state
    for search in config.get('searches', []):
        if search['name'] == search_name:
            search['last_availability_state'] = new_state
            break
    
    return save_user_config(bucket_name, user_id, config)

def process_search(search_config):
    """Process a single search configuration"""
    if not search_config.get('enabled', True):
        return None
    
    try:
        parks = search_config['parks']
        start_date = datetime.strptime(search_config['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(search_config['end_date'], '%Y-%m-%d')
        search_name = search_config.get('name', 'Unnamed Search')
        
        print(f"Processing search: {search_name}")
        
        # Check each park
        info_by_park_id = {}
        for park_id in parks:
            current, maximum, availabilities_filtered, park_name = check_park(
                park_id,
                start_date,
                end_date,
                search_config.get('campsite_type'),
                search_config.get('campsite_ids', ()),
                nights=search_config.get('nights'),
                weekends_only=search_config.get('weekends_only', False),
                excluded_site_ids=[]
            )
            info_by_park_id[park_id] = (current, maximum, availabilities_filtered, park_name)
        
        # Generate human-readable output
        camping_output, has_availabilities = generate_human_output(
            info_by_park_id,
            start_date,
            end_date,
            gen_campsite_info=True
        )
        
        return {
            'search_name': search_name,
            'camping_output': camping_output,
            'has_availabilities': has_availabilities,
            'parks': parks,
            'date_range': f"{search_config['start_date']} to {search_config['end_date']}",
            'priority': search_config.get('priority', 'normal')
        }
        
    except Exception as e:
        return {
            'search_name': search_config.get('name', 'Unknown'),
            'error': str(e),
            'has_availabilities': False
        }

def notify_user(result, user_config, bucket_name=None):
    """Send notifications to a user via their preferred channels with state-based change detection"""
    notifications_sent = 0
    
    # Always notify errors immediately
    if result.get('error'):
        return _send_error_notification(result, user_config)
    
    # For availability notifications, use state-based change detection
    if not result.get('has_availabilities'):
        # No availability - just update state without notifying
        if bucket_name:
            _update_search_state_if_needed(result, user_config, bucket_name)
        return 0
    
    # Check if we should notify based on state changes
    search_name = result.get('search_name', 'Unknown')
    last_state = _get_search_last_state(result, user_config)
    
    should_notify, reason, new_state = should_notify_availability_change(result, last_state)
    
    # Update the state regardless of notification decision
    if bucket_name:
        user_id = user_config.get('_user_id')
        if user_id:
            update_search_availability_state(bucket_name, user_id, search_name, new_state)
            print(f"🔄 Updated availability state for '{search_name}': {reason}")
    
    if not should_notify:
        print(f"🔇 Skipping notification for '{search_name}': {reason}")
        return 0
    
    # Proceed with notification - enhance message with reason
    try:
        message, title, priority = format_campsite_availability_message(
            result['camping_output'],
            result['has_availabilities'],
            result['search_name']
        )
        
        if not message:  # No message to send
            return 0
            
        # Enhance message based on the reason for notification
        if reason == "first_availability_found":
            message = f"🎉 NEW: First availability found!\n\n{message}"
        elif reason == "new_availability":
            message = f"🎉 NEW: Availability just appeared!\n\n{message}"
        elif reason == "significant_increase":
            site_count = new_state.get('site_count', 0)
            message = f"📈 MORE SITES: Now {site_count} sites available!\n\n{message}"
        
        # Adjust priority based on search config
        if result.get('priority') == 'high':
            priority = max(priority, 1)
        
        notification_settings = user_config.get('notification_settings', {})
        
        # Send Telegram notification if enabled
        if notification_settings.get('telegram_enabled', True):
            user_id = user_config.get('_user_id')
            if user_id:
                try:
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                    if bot_token:
                        if title and title != "Campsite Alert":
                            formatted_message = f"<b>{title}</b>\n\n{message}"
                        else:
                            formatted_message = message
                        
                        telegram_result = send_telegram_notification(bot_token, user_id, formatted_message)
                    if telegram_result and telegram_result.get('ok'):
                        notifications_sent += 1
                        result['telegram_notification_sent'] = True
                        result['notification_reason'] = reason
                        print(f"✅ Sent notification to user {user_id}: {reason}")
                except Exception as telegram_error:
                    print(f"❌ Failed to send Telegram notification to user {user_id}: {telegram_error}")
                    result['telegram_notification_error'] = str(telegram_error)
        
        # Send Pushover notification if enabled (legacy support)
        if notification_settings.get('pushover_enabled', False):
            try:
                pushover_result = send_pushover_notification(message, title, priority)
                if pushover_result.get('status') == 1:
                    notifications_sent += 1
                    result['pushover_notification_sent'] = True
                    result['pushover_response'] = pushover_result
                    print(f"✅ Sent Pushover notification")
            except Exception as pushover_error:
                print(f"❌ Failed to send Pushover notification: {pushover_error}")
                result['pushover_notification_error'] = str(pushover_error)
        
        return notifications_sent
        
    except Exception as notification_error:
        print(f"❌ Error in notify_user: {notification_error}")
        result['notification_error'] = str(notification_error)
        return 0

def _send_error_notification(result, user_config):
    """Send error notifications immediately (no state checking needed)"""
    message = f"🚨 Error checking '{result['search_name']}': {result['error']}"
    title = "Search Error"
    priority = 1
    notifications_sent = 0
    
    notification_settings = user_config.get('notification_settings', {})
    
    # Send Telegram notification if enabled
    if notification_settings.get('telegram_enabled', True):
        user_id = user_config.get('_user_id')
        if user_id:
            try:
                bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                if bot_token:
                    formatted_message = f"<b>{title}</b>\n\n{message}"
                    telegram_result = send_telegram_notification(bot_token, user_id, formatted_message)
                if telegram_result and telegram_result.get('ok'):
                    notifications_sent += 1
                    result['telegram_notification_sent'] = True
                    print(f"✅ Sent error notification to user {user_id}")
            except Exception as telegram_error:
                print(f"❌ Failed to send Telegram error notification to user {user_id}: {telegram_error}")
                result['telegram_notification_error'] = str(telegram_error)
    
    # Send Pushover notification if enabled (legacy support)
    if notification_settings.get('pushover_enabled', False):
        try:
            pushover_result = send_pushover_notification(message, title, priority)
            if pushover_result.get('status') == 1:
                notifications_sent += 1
                result['pushover_notification_sent'] = True
                result['pushover_response'] = pushover_result
        except Exception as pushover_error:
            print(f"❌ Failed to send Pushover error notification: {pushover_error}")
            result['pushover_notification_error'] = str(pushover_error)
    
    return notifications_sent

def _get_search_last_state(result, user_config):
    """Get the last availability state for a search"""
    search_name = result.get('search_name', 'Unknown')
    
    for search in user_config.get('searches', []):
        if search.get('name') == search_name:
            return search.get('last_availability_state')
    
    return None

def _update_search_state_if_needed(result, user_config, bucket_name):
    """Update search state even when there's no availability"""
    search_name = result.get('search_name', 'Unknown')
    last_state = _get_search_last_state(result, user_config)
    
    # Create new state for no availability
    new_state = {
        'has_sites': False,
        'site_count': 0,
        'last_checked': datetime.now().isoformat()
    }
    
    # Only update if state actually changed
    if not last_state or last_state.get('has_sites', False):
        user_id = user_config.get('_user_id')
        if user_id:
            update_search_availability_state(bucket_name, user_id, search_name, new_state)
            print(f"🔄 Updated state for '{search_name}': availability_disappeared")

def sanitize_for_telegram(text):
    """Sanitize text for safe Telegram sending"""
    if not text:
        return "No details available"
    
    # Remove or replace problematic characters
    text = str(text)
    
    # Remove HTML tags that might conflict
    import re
    text = re.sub(r'<[^>]+>', '', text)
    
    # Replace problematic characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    # Limit length to avoid message too long errors
    if len(text) > 3000:
        text = text[:2950] + "...\n\n[Message truncated]"
    
    return text

def send_telegram_notification(bot_token, chat_id, message):
    """Send a message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # First try with HTML parsing
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        encoded_data = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=encoded_data)
        
        with urllib.request.urlopen(req) as response:
            result = response.read().decode()
            return json.loads(result)
            
    except Exception as e:
        print(f"HTML parsing failed: {e}")
        
        # Fallback: try without any parsing
        try:
            # Strip all HTML tags and send as plain text
            import re
            plain_text = re.sub(r'<[^>]+>', '', message)
            
            data = {
                'chat_id': chat_id,
                'text': plain_text
            }
            
            encoded_data = urllib.parse.urlencode(data).encode()
            req = urllib.request.Request(url, data=encoded_data)
            
            with urllib.request.urlopen(req) as response:
                result = response.read().decode()
                return json.loads(result)
                
        except Exception as fallback_error:
            print(f"Failed to send Telegram message (both HTML and plain): {fallback_error}")
            return None

def handle_manual_check(event, context):
    """Handle manual check requests from Telegram bot"""
    try:
        user_id = event.get('user_id')
        chat_id = event.get('telegram_chat_id')
        bot_token = event.get('telegram_bot_token')
        bucket_name = os.environ.get('CONFIG_BUCKET')
        
        print(f"🔍 Manual check for user {user_id}, chat {chat_id}")
        
        if not CAMPING_AVAILABLE:
            error_msg = "❌ Camping module not available"
            if bot_token and chat_id:
                send_telegram_notification(bot_token, chat_id, error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }
        
        # Load user configuration
        user_config = load_user_config(bucket_name, user_id)
        if not user_config:
            error_msg = "❌ No searches found for your account"
            if bot_token and chat_id:
                send_telegram_notification(bot_token, chat_id, error_msg)
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "No searches found"})
            }
        
        # Extract searches from user config
        user_searches = user_config.get('searches', [])
        if not user_searches:
            error_msg = "❌ No searches configured for your account"
            if bot_token and chat_id:
                send_telegram_notification(bot_token, chat_id, error_msg)
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "No searches configured"})
            }
        
        # Filter enabled searches
        enabled_searches = [s for s in user_searches if s.get('enabled', True)]
        if not enabled_searches:
            error_msg = "❌ No enabled searches found"
            if bot_token and chat_id:
                send_telegram_notification(bot_token, chat_id, error_msg)
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "No enabled searches"})
            }
        
        print(f"🔍 Processing {len(enabled_searches)} enabled searches for user {user_id}")
        
        # Process each search
        results = []
        availabilities_found = 0
        
        for search_config in enabled_searches:
            try:
                search_name = search_config.get('name', 'Unnamed Search')
                print(f"🔍 Checking search: {search_name}")
                
                result = process_search(search_config)
                
                # Send immediate notification if availability found
                if result.get('has_availabilities') and bot_token and chat_id:
                    availabilities_found += 1
                    
                    # Sanitize the camping output for safe Telegram sending
                    safe_output = sanitize_for_telegram(result.get('camping_output', 'Availability found but no details available'))
                    
                    # Format the message for Telegram using HTML
                    message = f"🎉 <b>FOUND: {search_name}</b>\n\n{safe_output}\n\n🏕 Book now! 🏕"
                    
                    print(f"🔍 DEBUG: Sending message with length: {len(message)}")
                    print(f"🔍 DEBUG: First 200 chars: {message[:200]}...")
                    
                    send_telegram_notification(bot_token, chat_id, message)
                    print(f"✅ Sent availability notification for {search_name}")
                elif result.get('error') and bot_token and chat_id:
                    error_message = f"⚠️ <b>Error in search: {search_name}</b>\n\n{result['error']}\n\nPlease check your search criteria."
                    send_telegram_notification(bot_token, chat_id, error_message)
                    print(f"❌ Sent error notification for {search_name}")
                
                results.append(result)
                
            except Exception as search_error:
                print(f"❌ Error processing search {search_config.get('name', 'Unknown')}: {search_error}")
                error_result = {
                    'search_name': search_config.get('name', 'Unknown'),
                    'user_id': user_id,
                    'has_availabilities': False,
                    'error': str(search_error)
                }
                results.append(error_result)
        
        # Send summary message
        errors = len([r for r in results if r.get('error')])
        if availabilities_found > 0:
            summary = f"✅ <b>Manual Check Complete!</b>\n\n🎉 Found availability in {availabilities_found} of {len(enabled_searches)} searches!\n\nDetailed results were sent above. 🏕️"
        else:
            summary = f"✅ <b>Manual Check Complete!</b>\n\n❌ No availability found in {len(enabled_searches)} search(es).\n\nI'll keep monitoring automatically every minute. 🔍"
        
        if errors > 0:
            summary += f"\n\n⚠️ {errors} search(es) had errors - check your search criteria."
        
        if bot_token and chat_id:
            send_telegram_notification(bot_token, chat_id, summary)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Manual check completed",
                "availabilities_found": availabilities_found,
                "total_searches": len(enabled_searches),
                "errors": errors,
                "results": results
            })
        }
        
    except Exception as e:
        print(f"❌ Error in handle_manual_check: {e}")
        error_msg = f"❌ Error during manual check: {str(e)}"
        
        if event.get('telegram_bot_token') and event.get('telegram_chat_id'):
            send_telegram_notification(event.get('telegram_bot_token'), event.get('telegram_chat_id'), error_msg)
        
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def campsite_checker_handler(event, context):
    """
    Main Campsite Checker Lambda handler
    Supports both scheduled monitoring and manual check requests from Telegram bot
    """
    try:
        # Check if this is a manual check request from Telegram bot
        if event.get('manual_check') and event.get('user_id'):
            print(f"🔍 Processing manual check request for user {event['user_id']}")
            return handle_manual_check(event, context)
        
        # Original scheduled monitoring logic
        # Get configuration from event or environment
        bucket_name = event.get('config_bucket') or os.environ.get('CONFIG_BUCKET')
        config_key = event.get('config_key', 'campsite_searches.json')
        multi_user_mode = event.get('multi_user_mode', True)  # Default to multi-user
        
        if not CAMPING_AVAILABLE:
            error_msg = "Camping module not available"
            send_pushover_notification(f"🚨 {error_msg}", "Module Error", 1)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }
        
        results = []
        notifications_sent = 0
        total_searches = 0
        
        if multi_user_mode:
            # Multi-user mode: load all user configurations
            print("Running in multi-user mode")
            user_configs = get_all_user_configs(bucket_name)
            
            if not user_configs:
                print("No user configurations found")
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "No users with active searches",
                        "total_searches": 0,
                        "availabilities_found": 0,
                        "notifications_sent": 0,
                        "users_processed": 0
                    })
                }
            
            for user_config in user_configs:
                user_id = user_config.get('_user_id', 'unknown')
                user_searches = user_config.get('searches', [])
                print(f"Processing {len(user_searches)} searches for user {user_id}")
                
                for search_config in user_searches:
                    if not search_config.get('enabled', True):
                        continue
                    
                    total_searches += 1
                    result = process_search(search_config)
                    if result:
                        # Add user context to result
                        result['user_id'] = user_id
                        results.append(result)
                        
                        # Send notifications to this user
                        user_notifications = notify_user(result, user_config, bucket_name)
                        notifications_sent += user_notifications
        
        else:
            # Legacy single-user mode
            print("Running in legacy single-user mode")
            config = load_search_config(bucket_name, config_key)
            if not config:
                error_msg = "Failed to load search configuration"
                send_pushover_notification(f"🚨 {error_msg}", "Configuration Error", 1)
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error": error_msg})
                }
            
            # Process searches in legacy format
            for search_config in config['searches']:
                if not search_config.get('enabled', True):
                    continue
                    
                total_searches += 1
                result = process_search(search_config)
                if result:
                    results.append(result)
                    
                    # Legacy notification handling
                    if result.get('has_availabilities') or result.get('error'):
                        try:
                            if result.get('error'):
                                message = f"🚨 Error checking '{result['search_name']}': {result['error']}"
                                title = "Search Error"
                                priority = 1
                            else:
                                message, title, priority = format_campsite_availability_message(
                                    result['camping_output'],
                                    result['has_availabilities'],
                                    result['search_name']
                                )
                            
                            if message:
                                if result.get('priority') == 'high':
                                    priority = max(priority, 1)
                                
                                pushover_result = send_pushover_notification(message, title, priority)
                                result['notification_sent'] = True
                                result['pushover_response'] = pushover_result
                                notifications_sent += 1
                                print(f"Notification sent for: {result['search_name']}")
                            
                        except Exception as notification_error:
                            print(f"Failed to send notification for {result['search_name']}: {notification_error}")
                            result['notification_error'] = str(notification_error)
        
        # Summary
        availabilities_found = len([r for r in results if r.get('has_availabilities')])
        users_processed = len(set(r.get('user_id') for r in results if r.get('user_id'))) if multi_user_mode else 1
        
        print(f"Processed {total_searches} searches across {users_processed} users, found availability in {availabilities_found}, sent {notifications_sent} notifications")
        
        response_body = {
            "message": "Campsite monitoring completed",
            "total_searches": total_searches,
            "availabilities_found": availabilities_found,
            "notifications_sent": notifications_sent,
            "results": results
        }
        
        if multi_user_mode:
            response_body["users_processed"] = users_processed
            response_body["mode"] = "multi-user"
        else:
            response_body["mode"] = "legacy"
        
        return {
            "statusCode": 200,
            "body": json.dumps(response_body)
        }
        
    except Exception as e:
        error_msg = f"Lambda execution failed: {str(e)}"
        try:
            send_pushover_notification(f"🚨 {error_msg}", "Lambda Error", 1)
        except:
            pass  # Don't fail on notification error
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": error_msg,
                "message": "Critical lambda failure"
            })
        }

# AWS Lambda entry point (keeps existing name for compatibility)
def lambda_handler(event, context):
    """AWS Lambda entry point - delegates to campsite_checker_handler"""
    return campsite_checker_handler(event, context)
