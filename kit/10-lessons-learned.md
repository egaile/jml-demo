# 10. Lessons learned

Things that cost us time, so they do not cost you any.

## From the first build

| What happened | Why | Do instead |
| --- | --- | --- |
| A1 refused to save: "Space must differ from the Issue created trigger" | Loop protection on same-project creates from Work item created | Trigger on the Fan out transition; the Concierge runs it after creating |
| "Error parsing template" on Lifecycle phase and Fan-out team | Rovo writes select values as strings | Pick each from the dropdown; no prompt avoids it |
| Link steps had a red badge | No link type chosen; no "is child of" on the site | relates to for fan-out, is blocked by for revoke-before-grant |
| Scheduled A2 failed with `issue in linkedIssues(, "relates to")` | Lookup + Branch has no current work item | JQL on the trigger, Related work items condition, or make it event-driven (done) |
| REVOKE_KEY rejected | Variable names are alphabetic only | revokeKey |
| Rovo could not build Demo reset | No manual trigger in its catalogue | Trigger on a `#reset` comment |
| Rovo could not update a flow | Not supported | Delete and recreate; prompts are the source of truth |
| Web request returned 502 | Supabase service key still a placeholder | Set all three env vars before testing; 401 = wrong secret, 502 = Supabase rejected the key |
| Vercel secret could not be read back | Created as "sensitive" | Create as "encrypted"; rotate if already sensitive |
| Older Atlassian Rovo MCP connector returned 403 | Not installed on that site | Use the Atlassian MCP connector (mcp.atlassian.com) |
| Assets text attribute would not hold a list | Only references and selects are multi-value | Textarea, newline separated, or model zones as objects |
| Seed Joiner had no fan-out tasks | Created before the rule existed | Create seeds after rules are enabled, or run Fan out by hand |
| Could not install Time to SLA | Site admin, not org admin, on an SE demo org | The reason this document exists |
| Time to SLA API `HAS_BREACHED` threshold never fired | Accepted by the API but not used by the app | Use `IS_BREACHED` (what the UI saves) |
| A9 webhook ran but found no work item | The Time to SLA action sends issues in the "provided" format | Set the webhook trigger to "Issues provided in the webhook", not a JQL on `{{webhookData...}}` |
| Default Time to SLA action emailed assignees at 50% and failed | Fan-out tasks have no assignee | Disable the global default action or send to reporter |
| Joiner and Leaver cannot go back to Open for a re-run | The workflows have no backward transitions | Bulk-move the item to Task (Pending) and back with a status mapping; the key is kept |

