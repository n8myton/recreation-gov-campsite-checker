#!/usr/bin/env python3
"""
Enhanced Lambda function that integrates with the camping checker.
This can be used as a replacement or enhancement to your current lambda_function.py
"""

import json
import urllib.request
import urllib.parse
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables when running locally
if os.path.exists('.env'):
    load_dotenv()

# Import your camping functionality
try:
    from camping import main as check_camping
    from utils.camping_argparser import CampingArgumentParser
    CAMPING_AVAILABLE = True
except ImportError:
    CAMPING_AVAILABLE = False
    print("Warning: camping module not available")

def send_pushover_notification(message, title="Campsite Alert"):
    """Send a notification via Pushover"""
    user_key = os.environ.get('PUSHOVER_USER_KEY')
    api_token = os.environ.get('PUSHOVER_API_TOKEN')
    
    if not user_key or not api_token:
        raise ValueError("PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN environment variables must be set")

    data = urllib.parse.urlencode({
        "token": api_token,
        "user": user_key,
        "message": message,
        "title": title
    }).encode()

    req = urllib.request.Request("https://api.pushover.net/1/messages.json", data=data)
    with urllib.request.urlopen(req) as response:
        result = response.read().decode()
    
    return json.loads(result)

def lambda_handler(event, context):
    """
    Enhanced Lambda handler that can check campsites and send notifications.
    
    Event structure (all optional):
    {
        "parks": ["park_id1", "park_id2"],  // List of park IDs to check
        "start_date": "2023-07-01",         // Start date (YYYY-MM-DD)
        "end_date": "2023-07-07",           // End date (YYYY-MM-DD)
        "message": "Custom message",        // Custom message to send
        "check_camping": true               // Whether to check camping availability
    }
    """
    
    try:
        # Get parameters from event or use defaults
        custom_message = event.get('message')
        check_camping_flag = event.get('check_camping', False)
        
        if custom_message:
            # Send custom message
            result = send_pushover_notification(custom_message)
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Custom notification sent successfully",
                    "pushover_response": result
                })
            }
        
        elif check_camping_flag and CAMPING_AVAILABLE:
            # Check camping availability
            parks = event.get('parks', ['232448'])  # Default to a park ID
            start_date_str = event.get('start_date')
            end_date_str = event.get('end_date')
            
            # Use default dates if not provided (next weekend)
            if not start_date_str or not end_date_str:
                today = datetime.now()
                # Find next Friday
                days_ahead = 4 - today.weekday()  # Friday is 4
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                next_friday = today + timedelta(days=days_ahead)
                next_sunday = next_friday + timedelta(days=2)
                
                start_date_str = next_friday.strftime('%Y-%m-%d')
                end_date_str = next_sunday.strftime('%Y-%m-%d')
            
            # Mock args object for camping checker
            class MockArgs:
                def __init__(self):
                    self.parks = parks
                    self.start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                    self.end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    self.campsite_type = None
                    self.campsite_ids = ()
                    self.nights = None
                    self.weekends_only = False
                    self.exclusion_file = None
                    self.show_campsite_info = True
                    self.debug = False
                    self.json_output = True
            
            # This is a simplified version - you'd need to adapt this
            # to work with your camping.py main function properly
            message = f"Checking campsites for {', '.join(parks)} from {start_date_str} to {end_date_str}"
            result = send_pushover_notification(message, "Campsite Check")
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Campsite check notification sent",
                    "parks": parks,
                    "date_range": f"{start_date_str} to {end_date_str}",
                    "pushover_response": result
                })
            }
        
        else:
            # Default: send hello message
            result = send_pushover_notification("Hello from Campbot! 🏕️")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Default notification sent successfully",
                    "pushover_response": result
                })
            }
            
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "Failed to execute lambda function"
            })
        }
