# Slack Token Scope Verification
# Generated: 2026-02-20 20:33:00 EST
# Method: Each scope tested by calling its corresponding Slack API endpoint.
# YES = API call succeeded or returned a resource error (not a scope error)
# NO = API returned missing_scope or not_allowed

========== BOT TOKEN ==========
Identity: scotts_openclaw_bot, team: Tatari

  auth.test                 YES                                      | Basic auth check
  channels:read             YES                                      | List public channels
  groups:read               YES                                      | List private channels
  im:read                   YES                                      | List DM channels
  mpim:read                 YES                                      | List group DM channels
  channels:history          YES                                      | Read public channel history (sre-dp)
  groups:history            YES (scope works, channel invalid)       | Read private channel history (sre-private)
  im:history                YES                                      | Read DM history (bot DM with Scott)
  users:read                YES                                      | List users
  users.profile:read        YES                                      | Get user profile
  search:read               MAYBE (not_allowed_token_type)           | Search messages
  reactions:read            MAYBE (message_not_found)                | Get reactions
  pins:read                 YES                                      | List pins
  team:read                 YES                                      | Get team info
  usergroups:read           YES                                      | List user groups
  chat:write                YES (scope works, channel invalid)       | Post message (expected channel_not_found = scope OK)
  im:write                  YES                                      | Open DM conversation

========== USER TOKEN ==========
Identity: scott.idler, team: Tatari

  auth.test                 YES                                      | Basic auth check
  channels:read             YES                                      | List public channels
  groups:read               YES                                      | List private channels
  im:read                   YES                                      | List DM channels
  mpim:read                 YES                                      | List group DM channels
  channels:history          YES                                      | Read public channel history (sre-dp)
  groups:history            YES (scope works, channel invalid)       | Read private channel history (sre-private)
  im:history                YES                                      | Read DM history (bot DM with Scott)
  users:read                YES                                      | List users
  users.profile:read        NO                                       | Get user profile
  search:read               YES                                      | Search messages
  reactions:read            NO                                       | Get reactions
  pins:read                 NO                                       | List pins
  team:read                 NO                                       | Get team info
  usergroups:read           NO                                       | List user groups
  chat:write                NO                                       | Post message (expected channel_not_found = scope OK)
  im:write                  NO                                       | Open DM conversation

