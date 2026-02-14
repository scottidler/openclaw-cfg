#!/usr/bin/env python3
"""
Weekly SRE & Data Platform summary - Slack message fetcher & compactor.
Pulls messages + threads, strips noise, compacts into a concise format
ready for LLM summarization.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

CONFIG_PATH = "/data/.openclaw/workspace/weekly-summary-config.json"
OUTPUT_PATH = "/data/.openclaw/workspace/weekly-summary-raw.json"

# Noise patterns to filter
NOISE_PATTERNS = [
    r'^(lol|haha|lmao|nice|thanks|ty|thx|np|👍|🎉|💯|😂|🙏|👀)$',
    r'^(good morning|gm|morning|hey|hi|hello|bye|ttyl|brb)[\s!.]*$',
    r'^\+1$',
    r'^(joined|left) #',
    r'^<@U[A-Z0-9]+> (has joined|has left)',
    r'^set the channel (topic|purpose)',
]
NOISE_RE = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]

def is_noise(text):
    """Check if a message is casual banter / noise."""
    clean = text.strip()
    if len(clean) < 4 and not any(c.isalnum() for c in clean):
        return True
    return any(p.match(clean) for p in NOISE_RE)

def slack_api(method, token, params=None):
    url = f"https://slack.com/api/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    except Exception as e:
        print(f"  API error ({method}): {e}", file=sys.stderr)
        return {"ok": False}
    if not resp.get("ok"):
        print(f"  API error ({method}): {resp.get('error')}", file=sys.stderr)
    return resp

def get_user_map(token):
    users = {}
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
            users[u["id"]] = name
        cursor = resp.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
    return users

def resolve_mentions(text, user_map):
    def repl(m):
        uid = m.group(1)
        return f"@{user_map.get(uid, uid)}"
    text = re.sub(r'<@(U[A-Z0-9]+)>', repl, text)
    # Strip channel links to just name
    text = re.sub(r'<#C[A-Z0-9]+\|([^>]+)>', r'#\1', text)
    # Strip URL formatting
    text = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', r'\2 (\1)', text)
    text = re.sub(r'<(https?://[^>]+)>', r'\1', text)
    return text

def compact_text(text):
    """Strip extra whitespace, collapse blank lines."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def fetch_channel(token, channel_id, oldest, latest, user_map):
    """Fetch and compact messages + threads for one channel."""
    entries = []
    parent_messages = []
    cursor = ""

    # Fetch top-level messages
    for _ in range(20):
        params = {
            "channel": channel_id,
            "oldest": int(oldest),
            "latest": int(latest),
            "limit": 200,
        }
        if cursor:
            params["cursor"] = cursor
        resp = slack_api("conversations.history", token, params)
        if not resp.get("ok"):
            break
        parent_messages.extend(resp.get("messages", []))
        cursor = resp.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break

    # Process each message
    for msg in parent_messages:
        if msg.get("subtype") in ("channel_join", "channel_leave", "bot_add",
                                   "bot_remove", "channel_topic", "channel_purpose",
                                   "pinned_item", "unpinned_item"):
            continue

        text = msg.get("text", "").strip()
        if not text or is_noise(text):
            continue

        text = resolve_mentions(text, user_map)
        text = compact_text(text)
        user = user_map.get(msg.get("user", ""), msg.get("user", "?"))
        ts = float(msg.get("ts", 0))
        day = datetime.fromtimestamp(ts).strftime("%a %m/%d")

        # Compact thread replies
        thread_lines = []
        if msg.get("reply_count", 0) > 0:
            t_cursor = ""
            for _ in range(5):
                t_params = {
                    "channel": channel_id,
                    "ts": msg["ts"],
                    "limit": 100,
                    "oldest": int(oldest),
                }
                if t_cursor:
                    t_params["cursor"] = t_cursor
                t_resp = slack_api("conversations.replies", token, t_params)
                if not t_resp.get("ok"):
                    break
                for reply in t_resp.get("messages", [])[1:]:  # skip parent
                    r_text = reply.get("text", "").strip()
                    if r_text and not is_noise(r_text):
                        r_text = resolve_mentions(r_text, user_map)
                        r_text = compact_text(r_text)
                        r_user = user_map.get(reply.get("user", ""), "?")
                        thread_lines.append(f"  {r_user}: {r_text}")
                t_cursor = t_resp.get("response_metadata", {}).get("next_cursor", "")
                if not t_cursor:
                    break

        entry = f"[{day}] {user}: {text}"
        if thread_lines:
            entry += "\n" + "\n".join(thread_lines)
        entries.append(entry)

    return entries

def main():
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    token = os.environ.get("SLACK_USER_TOKEN", "")
    if not token:
        print("ERROR: SLACK_USER_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    now = time.time()
    oldest = now - (7 * 24 * 3600)
    period = f"{datetime.fromtimestamp(oldest).strftime('%b %d')} - {datetime.fromtimestamp(now).strftime('%b %d, %Y')}"

    print("Fetching user map...")
    user_map = get_user_map(token)
    print(f"Got {len(user_map)} users")

    output = {"period": period, "groups": {}}

    total_msgs = 0
    total_chars = 0

    for group_name, channels in config["channels"].items():
        output["groups"][group_name] = {}
        for ch_name, ch_id in channels.items():
            print(f"Fetching #{ch_name}...")
            entries = fetch_channel(token, ch_id, oldest, now, user_map)
            compacted = "\n\n".join(entries)
            output["groups"][group_name][ch_name] = compacted
            total_msgs += len(entries)
            total_chars += len(compacted)
            print(f"  {len(entries)} messages -> {len(compacted):,} chars")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nTotal: {total_msgs} messages, {total_chars:,} chars compacted")
    print(f"Output: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
