#!/usr/bin/env python3
"""Gather daily briefing data from Gmail, Google Calendar, Slack and format for delivery."""
import json, subprocess, datetime, os, requests
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
PROMPTS_DIR = WORKSPACE / "prompts"

def load_prompt(name):
    """Load a prompt template from the prompts directory."""
    prompt_file = PROMPTS_DIR / f"{name}.txt"
    if not prompt_file.exists():
        return None
    return prompt_file.read_text()

def get_calendar():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    
    with open(os.path.expanduser('~/.config/gcalcli/oauth')) as f:
        token_data = json.load(f)
    
    creds = Credentials.from_authorized_user_info(token_data)
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.datetime.now(datetime.UTC).isoformat()
    eod = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24)).isoformat()
    
    events = service.events().list(
        calendarId='primary', timeMin=now, timeMax=eod,
        singleEvents=True, orderBy='startTime'
    ).execute()
    
    items = []
    for event in events.get('items', []):
        start = event['start'].get('dateTime', event['start'].get('date'))
        items.append(f"- {start}: {event.get('summary', 'No title')}")
    
    return items if items else ["No events today."]

def get_emails():
    result = subprocess.run(
        ['himalaya', 'envelope', 'list', '-a', 'personal', '-s', '10'],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip() if result.stdout.strip() else "No recent emails."

def get_slack():
    """Fetch recent Slack DMs and mentions from the last 24 hours"""
    try:
        # Load Slack user token from config
        with open('/data/.openclaw/openclaw.json') as f:
            config = json.load(f)
            token = config['channels']['slack']['userToken']
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Calculate 24 hours ago timestamp
        oldest = (datetime.datetime.now() - datetime.timedelta(hours=24)).timestamp()
        
        # Get list of DM channels
        dm_response = requests.get(
            'https://slack.com/api/conversations.list',
            headers=headers,
            params={'types': 'im', 'limit': 100}
        ).json()
        
        highlights = []
        
        if dm_response.get('ok'):
            for channel in dm_response.get('channels', [])[:10]:  # Check top 10 DMs
                channel_id = channel['id']
                
                # Get recent messages in this DM
                history = requests.get(
                    'https://slack.com/api/conversations.history',
                    headers=headers,
                    params={'channel': channel_id, 'oldest': oldest, 'limit': 5}
                ).json()
                
                if history.get('ok') and history.get('messages'):
                    user_id = channel.get('user')
                    # Get user info
                    user_info = requests.get(
                        'https://slack.com/api/users.info',
                        headers=headers,
                        params={'user': user_id}
                    ).json()
                    
                    user_name = user_info.get('user', {}).get('real_name', 'Unknown')
                    
                    for msg in history.get('messages', []):
                        text = msg.get('text', '')[:100]  # First 100 chars
                        highlights.append(f"- DM from {user_name}: {text}")
        
        return highlights if highlights else ["No new DM activity in last 24h"]
    
    except Exception as e:
        return [f"Error fetching Slack: {str(e)}"]

def format_output(calendar_data, email_data, slack_data):
    """Format the raw data using the prompt template if available."""
    prompt_template = load_prompt("daily_briefing")
    
    # For now, just return structured text (AI summarization would happen elsewhere)
    output = "=== DAILY BRIEFING ===\n\n"
    
    output += "CALENDAR:\n"
    if isinstance(calendar_data, list):
        output += '\n'.join(calendar_data) + "\n\n"
    else:
        output += f"{calendar_data}\n\n"
    
    output += "RECENT EMAILS:\n"
    output += f"{email_data}\n\n"
    
    output += "SLACK HIGHLIGHTS:\n"
    if isinstance(slack_data, list):
        output += '\n'.join(slack_data) + "\n"
    else:
        output += f"{slack_data}\n"
    
    return output

if __name__ == '__main__':
    try:
        calendar = get_calendar()
    except Exception as e:
        calendar = f"Error: {e}"
    
    try:
        emails = get_emails()
    except Exception as e:
        emails = f"Error: {e}"
    
    try:
        slack = get_slack()
    except Exception as e:
        slack = f"Error: {e}"
    
    print(format_output(calendar, emails, slack))
