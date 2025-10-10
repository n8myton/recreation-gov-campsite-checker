import json
import urllib.request
import urllib.parse
import os

def lambda_handler(event, context):
    user_key = os.environ['PUSHOVER_USER_KEY']
    api_token = os.environ['PUSHOVER_API_TOKEN']

    data = urllib.parse.urlencode({
        "token": api_token,
        "user": user_key,
        "message": "Hello from Campbot!"
    }).encode()

    req = urllib.request.Request("https://api.pushover.net/1/messages.json", data=data)
    with urllib.request.urlopen(req) as response:
        result = response.read().decode()

    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
