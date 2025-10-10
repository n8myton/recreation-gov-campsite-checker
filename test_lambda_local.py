#!/usr/bin/env python3
"""
Local test script for the Lambda function.
This allows you to test your Lambda function locally without deploying to AWS.
"""

import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import your lambda function
from lambda_function import lambda_handler

def test_lambda_locally():
    """Test the lambda function locally with mock event and context."""
    
    # Mock event (you can modify this as needed)
    mock_event = {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }
    
    # Mock context (simple object with basic Lambda context properties)
    class MockContext:
        def __init__(self):
            self.function_name = "campbot"
            self.function_version = "$LATEST"
            self.invoked_function_arn = "arn:aws:lambda:us-west-1:123456789012:function:campbot"
            self.memory_limit_in_mb = "128"
            self.remaining_time_in_millis = lambda: 300000
            self.log_group_name = "/aws/lambda/campbot"
            self.log_stream_name = "2023/10/10/[$LATEST]test-stream"
            self.aws_request_id = "test-request-id"
    
    mock_context = MockContext()
    
    # Check if required environment variables are set
    required_vars = ["PUSHOVER_USER_KEY", "PUSHOVER_API_TOKEN"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file with your Pushover credentials:")
        print("PUSHOVER_USER_KEY=your_user_key_here")
        print("PUSHOVER_API_TOKEN=your_api_token_here")
        return
    
    print("🚀 Testing Lambda function locally...")
    print(f"Event: {json.dumps(mock_event, indent=2)}")
    print("-" * 50)
    
    try:
        # Call your lambda function
        result = lambda_handler(mock_event, mock_context)
        
        print("✅ Lambda function executed successfully!")
        print(f"Status Code: {result['statusCode']}")
        print(f"Response: {json.dumps(json.loads(result['body']), indent=2)}")
        
    except Exception as e:
        print(f"❌ Error executing Lambda function: {str(e)}")
        raise

if __name__ == "__main__":
    test_lambda_locally()
