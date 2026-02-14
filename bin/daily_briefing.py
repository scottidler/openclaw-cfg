#!/usr/bin/env python3
"""Gather daily briefing data from Gmail, Google Calendar, and format for delivery."""
import json, subprocess, datetime, os

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
    
    return items

def get_emails():
    result = subprocess.run(
        ['himalaya', 'envelope', 'list', '-a', 'personal', '-s', '10'],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip()

if __name__ == '__main__':
    print("=== CALENDAR ===")
    try:
        events = get_calendar()
        if events:
            print('\n'.join(events))
        else:
            print("No events today.")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== RECENT EMAILS ===")
    try:
        print(get_emails())
    except Exception as e:
        print(f"Error: {e}")
