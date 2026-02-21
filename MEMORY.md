# MEMORY.md - Long-Term Memory

## Conventions & Preferences

### File Naming Convention (2026-02-20)
**Scott's rule:** Use hyphens for everything EXCEPT Python files.

- **Python files** (`.py`): Use underscores (`daily_briefing.py`) for import compatibility
- **All other files**: Use hyphens (`.pmt`, `.json`, `.yml`, `.md`, etc.)
  - Example: `daily-briefing.pmt`, `config-prod.json`, `setup-guide.md`

**Why:** Python imports require underscores. Everything else should be consistent with hyphen-preference.

**Never mix.** This is a hard rule.

### NEVER GUESS (2026-02-20)
**Hard rule:** Do not guess or speculate and present it as fact. If I don't know something, say "I don't know" and either look it up or ask. Scott finds guessing extremely frustrating. This applies to everything — API scopes, config values, tool behavior, anything. Verify before stating.

---

## Setup & Configuration

### Git Repository
- Workspace repo: `github.com/scottidler/openclaw-cfg.git`
- Always commit changes to workspace
- Prompts live in `prompts/` directory as `.pmt` files
- Scripts live in `bin/` directory

### Services Connected
- **Slack:** Tatari workspace (scott.idler@tatari.tv)
- **Email:** Via himalaya (personal account)
- **Calendar:** Google Calendar via gcalcli
- **WhatsApp:** +15039990803

---

## Lessons Learned

### 2026-02-20: Commit Hygiene
- I was not committing workspace changes for 5 days
- **New rule:** Commit after every meaningful change
- Push regularly so Scott can see progress
- Use descriptive commit messages

### 2026-02-20: Prompts as Data
- Separate prompts from code logic
- Store prompts in `prompts/*.pmt` files
- Load them dynamically in Python scripts
- Makes it easier to iterate on prompts without touching code

---

_This file is my curated long-term memory. Daily notes go in `memory/YYYY-MM-DD.md`._
