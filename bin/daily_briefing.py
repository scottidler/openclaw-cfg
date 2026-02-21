#!/usr/bin/env python3
"""Gather daily briefing data from Gmail, Google Calendar, Slack and format for delivery."""
import json, subprocess, datetime, os
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
PROMPTS_DIR = WORKSPACE / "prompts"

def load_prompt(name):
    """Load a prompt template from the prompts directory (use hyphens in name)."""
    prompt_file = PROMPTS_DIR / f"{name}.pmt"
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

def slack_api(method, token, params=None):
    """Call Slack API using urllib (same approach as weekly summary)."""
    import urllib.request, urllib.parse
    url = f"https://slack.com/api/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return resp

def get_slack():
    """Fetch notable Slack activity from the last 24 hours across key channels."""
    import re, time

    # Channels to monitor (from weekly-summary-config + extras Scott requested)
    CHANNELS = {
        "sre": "CBC5M4ZQW",
        "sre-private": "C01FXF7P3ST",
        "data-platform": "C0195L0G667",
        "data-platform-internal": "C023YTN4B1D",
        "sre-dp": "C039YLDJW5T",
        "engineering": "C0L0DJU56",
        "staging-env": "C01TSJ3F9GV",
        "ask-security": "C2BDSAAQ7",
        "incidents": "C01EMTW0XS7",
    }

    try:
        with open('/data/.openclaw/openclaw.json') as f:
            config = json.load(f)
            token = config['channels']['slack']['userToken']

        now = time.time()
        oldest = now - (24 * 3600)

        # Build user map with pagination
        user_map = {}
        cursor = ""
        for _ in range(10):
            params = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            resp = slack_api("users.list", token, params)
            if not resp.get("ok"):
                break
            for u in resp.get("members", []):
                name = (u.get("profile", {}).get("display_name")
                        or u.get("profile", {}).get("real_name")
                        or u.get("name", u["id"]))
                user_map[u["id"]] = name
            cursor = resp.get("response_metadata", {}).get("next_cursor", "")
            if not cursor:
                break

        def resolve(text):
            text = re.sub(r'<@(U[A-Z0-9]+)>', lambda m: f"@{user_map.get(m.group(1), m.group(1))}", text)
            text = re.sub(r'<#C[A-Z0-9]+\|([^>]+)>', r'#\1', text)
            text = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', r'\2', text)
            text = re.sub(r'<(https?://[^>]+)>', r'\1', text)
            return text.strip()

        # Noise filter
        noise_re = [re.compile(p, re.IGNORECASE) for p in [
            r'^(lol|haha|lmao|nice|thanks|ty|thx|np|👍|🎉|💯|😂|🙏|👀|\+1)[\s!.]*$',
            r'^(good morning|gm|morning|hey|hi|hello|bye|ttyl|brb)[\s!.]*$',
        ]]

        results = {}
        for ch_name, ch_id in CHANNELS.items():
            resp = slack_api("conversations.history", token, {
                "channel": ch_id,
                "oldest": int(oldest),
                "limit": 50,
            })
            if not resp.get("ok"):
                results[ch_name] = f"(error: {resp.get('error', 'unknown')})"
                continue

            messages = resp.get("messages", [])
            entries = []
            for msg in messages:
                if msg.get("subtype") in ("channel_join", "channel_leave", "bot_add",
                                           "bot_remove", "channel_topic", "channel_purpose",
                                           "pinned_item", "unpinned_item"):
                    continue
                text = msg.get("text", "").strip()
                if not text:
                    continue
                if any(p.match(text.strip()) for p in noise_re):
                    continue

                text = resolve(text)
                user = user_map.get(msg.get("user", ""), msg.get("username", "?"))
                thread_count = msg.get("reply_count", 0)
                preview = text[:150]
                if len(text) > 150:
                    preview += "..."
                thread_note = f" ({thread_count} replies)" if thread_count > 0 else ""
                entries.append(f"  - {user}: {preview}{thread_note}")

            if entries:
                results[ch_name] = "\n".join(entries[:10])  # Top 10 per channel
            # Skip channels with no activity (don't clutter output)

        if not results:
            return ["No notable Slack activity in the last 24h."]

        output = []
        for ch_name, content in results.items():
            output.append(f"#{ch_name}:\n{content}")
        return output

    except Exception as e:
        return [f"Error fetching Slack: {str(e)}"]

def format_output(calendar_data, email_data, slack_data):
    """Format the raw data using the prompt template if available."""
    prompt_template = load_prompt("daily-briefing")
    
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
