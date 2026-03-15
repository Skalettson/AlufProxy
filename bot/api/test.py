"""
Minimal test handler for Vercel
"""

def handler(event, context):
    """Simple test handler"""
    return {
        'statusCode': 200,
        'body': '{"status": "ok", "message": "AlufProxy Bot is running!"}'
    }
