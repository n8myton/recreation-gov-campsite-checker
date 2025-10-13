#!/usr/bin/env python3
"""
Test script for the production Lambda function with multiple searches
"""

import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the production lambda function
from lambda_function_production import lambda_handler

def test_production_lambda():
    """Test the production lambda with local config file"""
    
    print("🚀 Testing Production Lambda function with multiple searches...")
    print("-" * 60)
    
    # Mock event for local testing
    mock_event = {
        # Don't specify config_bucket to use local file
        "config_key": "campsite_searches.json"
    }
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = "campbot-production"
            self.remaining_time_in_millis = lambda: 300000
    
    mock_context = MockContext()
    
    try:
        result = lambda_handler(mock_event, mock_context)
        
        print("✅ Production Lambda executed successfully!")
        print(f"Status Code: {result['statusCode']}")
        
        body = json.loads(result['body'])
        if result['statusCode'] == 200:
            print(f"📊 Results Summary:")
            print(f"   • Total searches: {body['total_searches']}")
            print(f"   • Availabilities found: {body['availabilities_found']}")
            print(f"   • Notifications sent: {body['notifications_sent']}")
            
            print(f"\n📋 Detailed Results:")
            for i, search_result in enumerate(body['results'], 1):
                print(f"   {i}. {search_result['search_name']}")
                if search_result.get('has_availabilities'):
                    print(f"      ✅ AVAILABILITY FOUND!")
                    if search_result.get('notification_sent'):
                        print(f"      📱 Notification sent")
                elif search_result.get('error'):
                    print(f"      ❌ Error: {search_result['error']}")
                else:
                    print(f"      ⏸  No availability (no notification sent)")
        else:
            print(f"❌ Error: {body.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error testing production lambda: {str(e)}")
        raise

if __name__ == "__main__":
    test_production_lambda()
