# 11. End-to-end demo walkthrough

A step-by-step run of the whole demo, with what to do, what you should see, and how to check it. Use it for your first run after building, and for every rehearsal. Chapter 09 has the condensed stage run-sheet; this chapter is the long form.

Times are typical. Agents answer in 20 to 120 seconds; rules fire in 5 to 15 seconds.

## 0. Start state

| Check | Expected |
| --- | --- |
| JML-1 (Leaver, Lawrence Barnes) | Status **Open**, no comments, Deprovisioning status and Knowledge audit status **Not started** |
| JML-2 (Mover, Marcus Webb) | Status **Awaiting approval**, no linked tasks |
| JML-3 (Joiner, Riley Chen) | Status **Pre-Day-One**, five linked tasks: four Done, **Legal** open |
| ITF board | Empty |
| Badge console | BADGE-4471 (Riley) **INACTIVE**; BADGE-1108 (Lawrence) and BADGE-3417 (Marcus) **ACTIVE**; event feed clear of earlier runs (08, 8.5) |

## Act 1: Joiner

### Step 1. The Concierge
**Do:** Rovo chat → **People Ops Concierge**:
```
We hired Riley Chen as a Marketing Associate in Sales and Marketing, starting November 3, reporting to Bruce Banner. Badge BADGE-4471.
```
**Expect:** the agent searches first, finds **JML-3** for Riley Chen and gives its key, and does **not** create a second onboarding item.
**Verify:** JQL `project = JML AND type = "Employee onboarding" AND summary ~ "Riley Chen"` returns only JML-3, and `project in (JML, ITF) AND created >= -10m` returns nothing.
**Reference run:** "An open work item already exists for Riley Chen's onboarding: **JML-3**. The fan-out process is already underway, and the item will close once the manager confirms training is complete." (about 20 s)

### Step 2. The fan-out
**Do:** open **JML-3** and its linked work items.
**Expect:** five tasks linked "relates to": **IT: provision Marketing Associate entitlements…** (in ITF if the seed was created after the reroute, otherwise JML), Facilities, Legal, Payroll and Manager. Four are Done and **Legal: confirm signed agreements for rchen** is Open. There's one A1 comment: "Fan-out created: IT, Facilities, Legal, Payroll, Manager…".
**Say:** one transition, Fan out, and automation created a task for every team. The badge waits for Legal.
**Reference run:** JML-3 in Pre-Day-One. JML-4 IT, JML-5 Facilities, JML-7 Payroll and JML-8 Manager were Done, and JML-6 Legal was Open. The SLA panel showed the template's "Time to resolution" goal, which you can ignore.

### Step 3. Day one: close the Legal task
**Do:** put the badge console on screen. Open the **Legal** task (JML-6) and transition it to **Done** (Mark as done), then switch to the console.
**Expect (5 to 15 s):**
- On the console, **BADGE-4471 (Riley Chen)** turns **ACTIVE** (green) and an **ACTIVATED** event appears in the feed with source "Jira Automation (Joiner day one)".
- JML-3 moves to **Day One**.
- A2 adds a comment on JML-3: "Day one for 2026-11-03. Badge BADGE-4471 activated. SENTRIA confirmation BA-…".

**Verify:** `GET <console>/api/badge?badge_number=BADGE-4471` returns status ACTIVE with the newest event ACTIVATED. If nothing happens, check JML → Automation → Audit log for "A2 Joiner day one".
**Reference run:** JML-6 Done → about 10 s later (A2 waits 8 s so the linked-items check sees the new status) BADGE-4471 was ACTIVE, with event ACTIVATED, reference JML-3, source "Jira Automation (Joiner day one)". JML-3 was in Day One with the comment "Day one for 2026-11-03. Badge BADGE-4471 activated. SENTRIA confirmation BA-20261026-4928."

## Act 2: Mover

### Step 4. Approve the transfer
**Do:** open **JML-2** (Transfer: Marcus Webb, Sales Advocate to Senior Support Engineer) and click **Approve**. Wait about 10 s and refresh.
**Expect:**
- JML-2 moves to **Revoking**.
- A3 creates four linked tasks:
  - **REVOKE: Standard Sales Access (Salesforce.com) for mwebb** in ITF
  - **GRANT: Advanced Support Services (JSM admin)** and **GRANT: Standard Developer** in ITF
  - **Facilities: badge BADGE-3417 zones, add Lab 2A and 24/7 floors** in JML
- Each GRANT/Facilities task shows **is blocked by** the REVOKE task.
- A3 comment: "Access audit complete. REVOKE: … GRANT: … RETAINED: … Grants are blocked until revokes are done."
- The JSM SLA **Revokes complete** (1 business day) starts on JML-2.

**Reference run:** JML-2 in Revoking. ITF-44 REVOKE "blocks" ITF-45 and ITF-46 (GRANT) and JML-125 (Facilities). The A3 comment was present, and "Revokes complete" had an ongoing cycle from the moment of approval.

**Check the Time to SLA clock now.** In the reference run the REVOKE task got **no** Time to SLA clock on its own: the app was not processing newly created work items, even though the task matched the SLA's JQL. A recalculation attached it immediately (counted from creation):

```bash
curl -H "Authorization: Bearer $TTS_TOKEN" -H "Content-Type: application/json" -X POST "$TTS_BASE/api/sla-recalculation" \
  -d '{"jql": "project = ITF AND created >= -1h", "slaIds": [], "excludeFinishedSlas": true}'
```

Or in the app: Time to SLA → Recalculation → new recalculation with that JQL. Before the talk, create a test ITF task and confirm a clock appears on its own within a minute. If it doesn't, plan to run the recalculation right after each fan-out (Approve, Start deprovisioning).

### Step 5. The ITF board and the operational clock
**Do:** open the **IT Fulfilment** board, then **ITF-44** (the REVOKE task). Scroll to the **SLA Panel**.
**Expect:** ITF-44, ITF-45 and ITF-46 are in To Do. ITF-44's SLA Panel shows **Revoke access** running, with about 1h50m remaining on the 2-hour business-hours goal, and a "Linked Issue SLAs of JML-2" section below it. GRANT tasks have no clock, which is by design.
**Say:** two clocks. The service promise is on the request; the operational clock is on the IT team's task, in their own project.
**Reference run:** after the recalculation, ITF-44 showed "Revoke access", elapsed 9m, remaining 1h 50m (8%).

### Step 6. Drift
**Do:** Rovo chat → **Access Audit**: `Show drift for Marcus Webb.`
**Expect (30 to 60 s):** **DRIFT: Legacy Archive Reader** (Payroll archive, rack C-10). It is held by Marcus but in neither the Sales Advocate nor the Senior Support Engineer profile, and is revoked unless the new manager approves an exception within 5 business days.
**Verify:** if the agent says it created or updated anything, open those keys. A question like "Show drift" should create nothing.
**Reference run:** the drift finding was correct, but the agent also claimed it had updated JML-2 and created "ITF-47 REVOKE (drift)". Neither happened: ITF-47 does not exist and JML-2 was unchanged. The fix is in 06 (the "Questions are read-only" and "Never claim an action you did not complete" lines in the Access Audit instructions).

### Step 7. Clear the revoke (optional)
**Do:** set the REVOKE task (ITF-44) to **Done**. Wait about 10 s and refresh JML-2.
**Expect:**
- JML-2 moves to **Granting**, with the A4 comment "All revokes done. Access is now clear to grow. GRANT tasks are unblocked."
- The JSM SLA **Revokes complete** shows as met (green tick).
- The REVOKE task's **Revoke access** clock stops with SUCCESS.

**Reference run:** Granting, A4 comment and "Revokes complete" met at 03:40 PM all happened on cue. The Time to SLA clock kept running (the same event problem as step 4) until a recalculation on `key = ITF-44` with `excludeFinishedSlas: false` set it to SUCCESS, 36 min elapsed.

## Act 3: Leaver

### Step 8. What does he own?
**Do:** Rovo chat → **Knowledge Audit Agent**, in a new chat: `Audit JML-1.` Rovo shows every write as a review card (**Create** / **Create all** / **Confirm selected**). Click to approve each one; that's the "agent proposes, a human approves" moment.
**Expect:**
- The inventory finds the two ITO runbooks (RB - Network Closet Access Procedure, RB - Legacy Data Center Decommission), Jira work "none found", and badge BADGE-1108 in Assets. The successor is **Mitch Davis**, and the highest risk is the **Legacy Data Center** runbook (the breaker map, breaker 23).
- Handover tasks in JML, Fan-out team Manager, Lifecycle phase DEPROVISION, each **relates to** JML-1 and with **no parent**.
- A summary comment on JML-1 with the Group / Items / Successor / Task key table and the highest-risk line.
- Knowledge audit status = **Complete**.

**Verify:** JML-1's linked items list the handover tasks under "relates to". The comment is present and Knowledge audit status is Complete.

**Reference run (before the instruction fixes in 06):**
- The first answer gave the inventory and a "Task not created" column. It only proposes; nothing is written until you approve the cards.
- The create card set **Parent: JML-1**, which fails ("Please select valid parent issue"): a Leaver can't be a parent. *Refine*: `Do not set a parent. Create the task with no parent, then link it to JML-1 with the link type "relates to".` Then *Create all* made JML-126/127/128, all linked "relates to" JML-1.
- Step 5 needed a nudge: `Now do Step 5: post the summary comment on JML-1 with the table (Group, Items, Successor, Task key) and the highest-risk line, and set Knowledge audit status to Complete.` The comment posted, but the field update targeted the wrong field ("customfield_10113 is not editable"). Knowledge audit status was set by hand.
- The fixes are the linking rule and the exact field id in the instructions (06).

### Step 9. Start deprovisioning
**Do:** put the badge console on screen. On JML-1 click **Start deprovisioning** and switch to the console.
**Expect:**
- Within about 5 s **BADGE-1108 turns INACTIVE** (red) with a DEACTIVATED event, source "Jira Automation (Badge deactivation)".
- JML-1 moves to Deprovisioning with Deprovisioning status In progress, the comment "SENTRIA: badge BADGE-1108 set to INACTIVE. Confirmation BA-…", and the A6 comment.
- Eight new linked tasks:
  - In ITF: badge zones, badge confirm (already Done), identity, entitlements.
  - In JML: successor, manager, facilities, payroll and legal.
- The JSM SLA **Deprovisioning verified** starts.
- Time to SLA clocks appear on the ITF badge-zones (15 min), identity (1 h) and entitlements (4 business h) tasks. The badge-confirm task gets none.

**Reference run:** all of the above on cue (BA-20261026-1557). The Time to SLA clocks needed a recalculation (see step 4).

### Step 10. Verify
**Do:** Rovo chat → **Deprovisioning**, new chat: `Verify JML-1.` Approve the cards.
**Expect:** a **Closure report** comment on JML-1 (Step / Owner / Task / Evidence / Result), STILL RUNNING tasks in ITF linked "relates to" JML-1, Deprovisioning status **Findings open**, and JML-1 **not** Verified.

**Reference run (immediately after step 9, before the fixes in 06):**
- The agent proposed 8 STILL RUNNING tasks (every runbook step was still open). The first card failed on **Parent: JML-1**, and *Refine* with the no-parent line fixed it.
- The tasks were created **without links** (the agent had no link tool) and were linked by hand.
- The Step 4/5 nudge (`Now do Step 4 and Step 5: post the Closure report comment on JML-1 …, and set Deprovisioning status to Findings open. Do not transition JML-1.`) produced the report and set Findings open correctly.
- Every step was reported as a Finding, the Assets badge still said ACTIVE, and the decommissioned zone was not named.

**To get the single-finding story on stage:**
1. Before Verify, close the identity, entitlement and team tasks with evidence, but not every DEPROVISION task: if they are all Done, A8 verifies the Leaver.
2. Have A7 also set the Assets Badge Status to INACTIVE.
3. Add to the Deprovisioning instructions: name every zone still on the badge.

### Step 11. The breach (A9)
**Expect:** about 15 min after step 9, if ITF's badge-zones task is still open, its clock breaches and Time to SLA's "Trigger Jira automation" action fires A9 within 1 to 2 min:
- The ITF task gets the label `sla-breach-flagged`.
- JML-1 gets the comment "SLA breached on Security: revoke all badge zones …, owner Security".
- Deprovisioning status becomes Findings open.

**Reference run:** the clock breached (status EXCEED) but the app did not fire the action, even after a recalculation; this is the same Time to SLA processing problem as step 4. Posting the app's payload to A9's webhook by hand proved the rule end to end (label, comment, Findings open). The manual call:

```bash
curl -X POST "<A9 webhook url>" -H "X-Automation-Webhook-Token: <A9 webhook secret>" -H "Content-Type: application/json" -d '{"issues":["ITF-52"]}'
```

## Close

### Step 12. Outside the platform
**Do:** in a normal **Claude desktop** chat with the Atlassian connector authorized for your site: `Is anything still running for Lawrence Barnes?`
**Expect:** JML-1 in Deprovisioning with its open tasks, the decommissioned zone on BADGE-1108, and the Legacy Data Center runbook risk.
**Reference run:** the answer listed every open task and also found that the Assets badge (FAC-932) and person record still showed ACTIVE, although the deactivation task was Done: "closed is not done". In that run the connector was not authorized for the site and the session fell back to the REST API, so test the connector in a plain chat before the talk.

## After the run

Reset the seeds (09, 9.3, or the reseed script), set BADGE-4471 back to INACTIVE and clear the console feed (08, 8.5).

## Known issues from the reference run

| Area | Issue | Fix |
| --- | --- | --- |
| Rovo agents | Parent set on created tasks; wrong status field; links missing; invented work item key | Guardrail additions and a link tool (06) |
| Deprovisioning | Eight findings and the decommissioned zone not named when run straight after the fan-out | Close the team tasks with evidence first (but not all DEPROVISION tasks, or A8 verifies); A7 also updates the Assets badge |
| Time to SLA | No clocks on new tasks, no updates on transitions, no breach actions (app-side) | Recalculate after each fan-out; trigger A9 by hand if needed |
| Claude desktop | Connector not authorized for the site | Authorize it and test in a plain chat |

