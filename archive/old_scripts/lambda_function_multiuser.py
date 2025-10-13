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

def send_telegram_notification(chat_id, message, title="Campsite Alert", bot_token=None):
    """Send a notification via Telegram"""
    if not bot_token:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("Warning: TELEGRAM_BOT_TOKEN not set, skipping Telegram notification")
        return None
    
    # Format message for Telegram
    if title and title != "Campsite Alert":
        formatted_message = f"*{title}*\n\n{message}"
    else:
        formatted_message = message
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": formatted_message,
        "parse_mode": "Markdown"
    }).encode()
    
    req = urllib.request.Request(url, data=data)
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

def notify_user(result, user_config):
    """Send notifications to a user via their preferred channels"""
    notifications_sent = 0
    
    # Determine if we should notify
    should_notify = result.get('has_availabilities') or result.get('error')
    if not should_notify:
        return 0
    
    try:
        if result.get('error'):
            # Error notification
            message = f"🚨 Error checking '{result['search_name']}': {result['error']}"
            title = "Search Error"
            priority = 1
        else:
            # Format availability notification
            message, title, priority = format_campsite_availability_message(
                result['camping_output'],
                result['has_availabilities'],
                result['search_name']
            )
        
        if not message:  # No message to send
            return 0
        
        # Adjust priority based on search config
        if result.get('priority') == 'high':
            priority = max(priority, 1)
        
        notification_settings = user_config.get('notification_settings', {})
        
        # Send Telegram notification if enabled
        if notification_settings.get('telegram_enabled', True):
            user_id = user_config.get('_user_id')
            if user_id:
                try:
                    telegram_result = send_telegram_notification(user_id, message, title)
                    if telegram_result and telegram_result.get('ok'):
                        notifications_sent += 1
                        result['telegram_notification_sent'] = True
                        print(f"Telegram notification sent to user {user_id}")
                except Exception as telegram_error:
                    print(f"Failed to send Telegram notification to user {user_id}: {telegram_error}")
                    result['telegram_notification_error'] = str(telegram_error)
        
        # Send Pushover notification if enabled (legacy support)
        if notification_settings.get('pushover_enabled', False):
            try:
                pushover_result = send_pushover_notification(message, title, priority)
                if pushover_result.get('status') == 1:
                    notifications_sent += 1
                    result['pushover_notification_sent'] = True
                    result['pushover_response'] = pushover_result
                    print(f"Pushover notification sent")
            except Exception as pushover_error:
                print(f"Failed to send Pushover notification: {pushover_error}")
                result['pushover_notification_error'] = str(pushover_error)
        
        return notifications_sent
        
    except Exception as notification_error:
        print(f"Error in notify_user: {notification_error}")
        result['notification_error'] = str(notification_error)
        return 0

def send_telegram_message(bot_token, chat_id, message):
    """Send a message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        encoded_data = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=encoded_data)
        
        with urllib.request.urlopen(req) as response:
            result = response.read().decode()
            return json.loads(result)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
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
                send_telegram_message(bot_token, chat_id, error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }
        
        # Load user configuration
        user_config = load_user_config(bucket_name, user_id)
        if not user_config:
            error_msg = "❌ No searches found for your account"
            if bot_token and chat_id:
                send_telegram_message(bot_token, chat_id, error_msg)
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "No searches found"})
            }
        
        # Extract searches from user config
        user_searches = user_config.get('searches', [])
        if not user_searches:
            error_msg = "❌ No searches configured for your account"
            if bot_token and chat_id:
                send_telegram_message(bot_token, chat_id, error_msg)
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "No searches configured"})
            }
        
        # Filter enabled searches
        enabled_searches = [s for s in user_searches if s.get('enabled', True)]
        if not enabled_searches:
            error_msg = "❌ No enabled searches found"
            if bot_token and chat_id:
                send_telegram_message(bot_token, chat_id, error_msg)
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
                
                result = process_search_for_user(user_id, search_config)
                
                # Send immediate notification if availability found
                if result.get('has_availabilities') and bot_token and chat_id:
                    availabilities_found += 1
                    
                    # Format the message for Telegram
                    message = f"🎉 *FOUND: {search_name}*\n\n{result['camping_output']}\n\n🏕 Book now! 🏕"
                    send_telegram_message(bot_token, chat_id, message)
                    print(f"✅ Sent availability notification for {search_name}")
                elif result.get('error') and bot_token and chat_id:
                    error_message = f"⚠️ *Error in search: {search_name}*\n\n{result['error']}\n\nPlease check your search criteria."
                    send_telegram_message(bot_token, chat_id, error_message)
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
            summary = f"✅ *Manual Check Complete!*\n\n🎉 Found availability in {availabilities_found} of {len(enabled_searches)} searches!\n\nDetailed results were sent above. 🏕️"
        else:
            summary = f"✅ *Manual Check Complete!*\n\n❌ No availability found in {len(enabled_searches)} search(es).\n\nI'll keep monitoring automatically every 30 minutes. 🔍"
        
        if errors > 0:
            summary += f"\n\n⚠️ {errors} search(es) had errors - check your search criteria."
        
        if bot_token and chat_id:
            send_telegram_message(bot_token, chat_id, summary)
        
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
            send_telegram_message(event.get('telegram_bot_token'), event.get('telegram_chat_id'), error_msg)
        
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def lambda_handler(event, context):
    """
    Production Lambda handler for scheduled campsite monitoring
    Supports both legacy single-user and new multi-user modes
    Also supports manual check requests from Telegram bot
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
                        user_notifications = notify_user(result, user_config)
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
