# 09. Verification, stage script, reset

## 9.1 Checks before calling the build done

1. `GET /rest/api/3/issue/JML-1/transitions` lists Request confirmation, Manager confirmed, Start deprovisioning, Cancel.
2. `GET /rest/api/3/issue/JML-2/transitions` from Awaiting approval lists Approve and Decline.
3. Fan out on JML-3 creates five tasks within 10 seconds (A1).
4. Close all five; A2 fires: `GET https://<your-console>.vercel.app/api/badge?badge_number=BADGE-4471` shows ACTIVE with a new ACTIVATED event, JML-3 is in Day One.
5. Approve JML-2; A3 creates one REVOKE and three GRANT tasks (REVOKE and the two IT GRANTs in ITF), GRANT tasks show "is blocked by".
6. Close the REVOKE task; A4 moves JML-2 to Granting.
7. Start deprovisioning on JML-1; A6 creates seven tasks (Security and IT in ITF) and A7 adds an eighth; A7 flips BADGE-1108 to INACTIVE and comments a BA- confirmation; the console card turns red within 3 seconds.
8. Deprovisioning agent "Verify JML-1" produces a closure report with one finding and does not transition to Verified.
9. Comment `#reset` on JML-1 and confirm the badge is ACTIVE again and the tasks are gone.
10. From Claude desktop with the Atlassian MCP connector: "Is anything still running for Lawrence Barnes?" returns the zone and breaker 23.
11. Shorten "Identity disabled" to 1 minute, create an ITF task "IT: disable identity for test" linked (relates to) to a test Leaver: within about 2 minutes A9 labels the task `sla-breach-flagged`, comments on the Leaver and sets Findings open. Restore the goal.

## 9.2 Stage script (the talk)

| Act | Where | You say | Audience sees |
| --- | --- | --- | --- |
| Joiner | Rovo chat, People Ops Concierge | "We hired Riley Chen as a Marketing Associate in Sales and Marketing, starting {date}, reporting to Bruce Banner. Badge BADGE-4471." | Agent finds JML-3 already exists. Open it: five fan-out tasks, four Done |
| Joiner | JML, the Legal task | Close it | A2 fires, badge card turns green, JML-3 moves to Day One |
| Mover | JML-2, Approve | Approve the transfer | A3 fires, REVOKE/GRANT/RETAINED comment, GRANT task blocked by REVOKE |
| Mover | Rovo chat, Access Audit | "Show drift for Marcus Webb." | DRIFT: Legacy Archive Reader |
| Leaver | Rovo chat, Knowledge Audit | "Audit JML-1." | Two runbooks, successor Mitch Davis, breaker 23 highest risk, handover tasks |
| Leaver | JML-1, Start deprovisioning | Transition it | Eight tasks (ITF board shows the Security and IT ones with Time to SLA clocks), badge card turns red, SENTRIA confirmation comment |
| Leaver | Rovo chat, Deprovisioning | "Verify JML-1." | Closure report, one finding, Findings open, not Verified |
| After | Claude desktop, Atlassian MCP | "Is anything still running for Lawrence Barnes?" | The zone and breaker 23. Closing line: the platform did not change; what "done" means did |

**Timing note.** "Badge zones revoked" has a 15-minute 24/7 goal. About 15 to 17 minutes after "Start deprovisioning", A9 comments on JML-1 and sets Findings open, unless the Security task is closed first. Decide whether that lands before or after "Verify JML-1" and pace the Leaver act accordingly.

**Closing act.** The Claude desktop question needs the Atlassian MCP connector (mcp.atlassian.com) authorized against your site.

## 9.3 Reset after a rehearsal

Rehearsing consumes the seeds: Approve, Start deprovisioning and Day one move JML-1/2/3 forward, and the Joiner and Leaver workflows have no way back.

1. Comment `#reset` on JML-1: Demo reset reactivates the badge, deletes linked fan-out tasks (JML and ITF) and sets both status fields to Not started.
2. Delete any remaining rehearsal tasks linked to JML-1 and JML-2 (REVOKE/GRANT, handover, STILL-RUNNING). Keep JML-3's original five tasks.
3. Put the seeds back without changing their keys, using Jira's bulk move (`POST /rest/api/3/bulk/issues/move`): move the item to work type Task with its status mapped to **Pending**, then back to its own work type with Pending mapped to the stage status (JML-1 → Open, JML-2 → Open then "Submit for approval", JML-3 → Pre-Day-One). A bulk move only remaps statuses the target workflow lacks, which is why the item parks in Pending (a Task status no parent workflow has).
4. Landing JML-3 in Pre-Day-One counts as a transition, so A1 fans out again: wait 30 s and delete the five new tasks.
5. Reopen JML-3's Legal task (Reopen issue → Start progress → Back to open).
6. Delete rehearsal comments, and reset the badge console (08, 8.5).
