#!/usr/bin/env python3
"""Google Calendar OAuth setup. Reads client credentials from env vars."""

from google_auth_oauthlib.flow import InstalledAppFlow
import json, os, sys

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars")
    sys.exit(1)

CLIENT_CONFIG = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = os.environ.get("GCAL_TOKEN_PATH", os.path.expanduser("~/.config/gcalcli/oauth"))

flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES, redirect_uri="http://localhost")

# If auth code passed as argument, use it directly; otherwise prompt
if len(sys.argv) > 1:
    code = sys.argv[1]
else:
    auth_url, _ = flow.authorization_url(prompt="consent")
    print(f"Go to this URL in your browser:\n\n{auth_url}\n")
    code = input("Enter the authorization code: ")

flow.fetch_token(code=code)
creds = flow.credentials

os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
with open(TOKEN_PATH, "w") as f:
    f.write(creds.to_json())

print(f"Auth complete! Token saved to {TOKEN_PATH}")
