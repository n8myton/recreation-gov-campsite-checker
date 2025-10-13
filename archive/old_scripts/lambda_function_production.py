#!/usr/bin/env python3
"""
Production Lambda function for scheduled campsite monitoring.
Loads search configurations from S3 and checks multiple campsite/date combinations.
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

def load_search_config(bucket_name=None, config_key="campsite_searches.json"):
    """
    Load search configuration from S3 or local file
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

def lambda_handler(event, context):
    """
    Production Lambda handler for scheduled campsite monitoring
    """
    try:
        # Get configuration from event or environment
        bucket_name = event.get('config_bucket') or os.environ.get('CONFIG_BUCKET')
        config_key = event.get('config_key', 'campsite_searches.json')
        
        # Load search configuration
        config = load_search_config(bucket_name, config_key)
        if not config:
            error_msg = "Failed to load search configuration"
            send_pushover_notification(f"🚨 {error_msg}", "Configuration Error", 1)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }
        
        if not CAMPING_AVAILABLE:
            error_msg = "Camping module not available"
            send_pushover_notification(f"🚨 {error_msg}", "Module Error", 1)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }
        
        # Process all enabled searches
        results = []
        notifications_sent = 0
        
        for search_config in config['searches']:
            if not search_config.get('enabled', True):
                continue
                
            result = process_search(search_config)
            if result:
                results.append(result)
                
                # Only notify if there are availabilities (unless there's an error)
                if result.get('has_availabilities') or result.get('error'):
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
                        
                        if message:  # Only send if we have a message
                            # Adjust priority based on search config
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
        total_searches = len([s for s in config['searches'] if s.get('enabled', True)])
        availabilities_found = len([r for r in results if r.get('has_availabilities')])
        
        print(f"Processed {total_searches} searches, found availability in {availabilities_found}, sent {notifications_sent} notifications")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Campsite monitoring completed",
                "total_searches": total_searches,
                "availabilities_found": availabilities_found,
                "notifications_sent": notifications_sent,
                "results": results
            })
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
