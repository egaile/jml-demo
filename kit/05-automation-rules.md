# 05. Automation rules A1 to A9 and Demo reset

Rules move things; agents reason. Each rule below has a plain-language spec table and a paste-ready **Create with Rovo** prompt. Build them in JML: Project settings → Automation → Create flow → Create with Rovo.



No API. In the JML project: Project settings → Automation → Create flow → **Create with Rovo**. Paste each prompt, review the draft against its table, fix the three things Rovo always gets wrong, Save, toggle Enabled. Rule actor: Automation for Jira. Scope: JML project.

**The three things Rovo always gets wrong**

1. Select-list values (Lifecycle phase, Fan-out team, Knowledge audit status, Deprovisioning status) come out as typed text and show "Error parsing template". Open each step and pick the option from the dropdown. No prompt wording avoids this.
2. Link steps are drafted with no link type. Choose "relates to" for fan-out links and "is blocked by" for revoke-before-grant.
3. "Allow rule trigger" is off by default. Turn it on for A2, A3, A4, A6, A7, A8 (rules that react to things other rules or agents do).

Other constraints we learned:

- Rovo cannot edit an existing flow. To change one, delete it and recreate from the prompt. Keep the prompts as source of truth.
- A "Work item created" trigger cannot create work items in the same project (loop protection). A1 triggers on the Fan out transition instead.
- Rovo's catalogue has no Manual trigger. Demo reset triggers on a comment containing `#reset`.
- Variable names must be alphabetic only: `revokeKey`, not `REVOKE_KEY`.
- On every web request step, turn on "Delay execution of subsequent rule actions until we've received a response" so `{{webResponse.body.confirmation}}` is available to the comment that follows.
- The `X-JML-Secret` header value is the `JML_SHARED_SECRET` env var on your badge console (see 08). Paste it by hand into A2, A7, and Demo reset after the draft. Never put it in a prompt, a doc, or a commit.
- Scheduled rules: put the JQL on the Scheduled trigger itself. Rovo drafts "Scheduled → Lookup work items → Branch", which fails with `issue in linkedIssues(, "relates to")` because the branch has no current work item.

### A1. Joiner fan-out

Trigger: Work item transitioned to Pre-Day-One. Condition: Work type = Employee onboarding. Creates five Tasks, each Lifecycle phase PRE-DAY-ONE, linked "relates to" the Joiner, then comments.

| # | Task summary | Fan-out team | Extra |
| --- | --- | --- | --- |
| 1 | IT: provision {{issue.Role}} entitlements for {{issue.Employee ID}} | IT | Description: Provision from Role Profile {{issue.Role}}. Policies and applications are on the Role object in Assets and the Confluence page labeled role-profile. Attach evidence per application. |
| 2 | Facilities: issue badge {{issue.Badge number}} and assign desk | Facilities | Description: Badge zones per Role Profile. Do not issue before Legal confirms signed agreements. |
| 3 | Legal: confirm signed agreements for {{issue.Employee ID}} | Legal | |
| 4 | Payroll: set up {{issue.Employee ID}} in Workday, start {{issue.Start date}} | Payroll | |
| 5 | Manager: orientation plan and required training for {{issue.Employee ID}} | Manager | Assignee {{issue.Manager}} |

Comment: "Fan-out created: IT, Facilities, Legal, Payroll, Manager. Badge {{issue.Badge number}} activates on {{issue.Start date}} once Legal and Facilities tasks are done."

Prompt:

```
Create a rule named "A1 Joiner fan-out". Trigger: work item transitioned to status Pre-Day-One. Condition: work type equals Employee onboarding. Then create five Task work items in this same project, each with Lifecycle phase set to the option PRE-DAY-ONE: (1) summary "IT: provision {{issue.Role}} entitlements for {{issue.Employee ID}}" with Fan-out team option IT and description "Provision from Role Profile {{issue.Role}}. Policies and applications are on the Role object in Assets and the Confluence page labeled role-profile. Attach evidence per application."; (2) summary "Facilities: issue badge {{issue.Badge number}} and assign desk" with Fan-out team option Facilities and description "Badge zones per Role Profile. Do not issue before Legal confirms signed agreements."; (3) summary "Legal: confirm signed agreements for {{issue.Employee ID}}" with Fan-out team option Legal; (4) summary "Payroll: set up {{issue.Employee ID}} in Workday, start {{issue.Start date}}" with Fan-out team option Payroll; (5) summary "Manager: orientation plan and required training for {{issue.Employee ID}}" with Fan-out team option Manager, assigned to {{issue.Manager}}. After each create, link the most recently created work item to the trigger work item with link type "relates to". Finally add a comment on the trigger work item: "Fan-out created: IT, Facilities, Legal, Payroll, Manager. Badge {{issue.Badge number}} activates on {{issue.Start date}} once Legal and Facilities tasks are done." Select Lifecycle phase and Fan-out team values from the field options, not as free text. Every Link step must have a link type chosen. Do not use a Work item created trigger.
```

### A2. Joiner day one (event-driven; the stage version)

Trigger: Work item transitioned to Done. Condition: Work type = Task AND Lifecycle phase = PRE-DAY-ONE. Branch: linked work items, relates to. Branch condition: Work type = Employee onboarding AND status = Pre-Day-One, plus Related work items condition (linked, relates to) all match `statusCategory = Done`. Actions on the branch item: web request (activate badge), transition "Day one", comment. On stage: close the last PRE-DAY-ONE task and the badge card turns green.

| # | Action | Values |
| --- | --- | --- |
| 1 | Send web request | POST https://<your-console>.vercel.app/api/badge. Headers Content-Type: application/json; X-JML-Secret: (paste). Custom body `{"badge_number":"{{issue.Badge number}}","action":"activate","reference":"{{issue.key}}","source":"Jira Automation (Joiner day one)"}`. Delay until response: on |
| 2 | Transition | Day one |
| 3 | Comment | Day one for {{issue.Start date}}. Badge {{issue.Badge number}} activated. SENTRIA confirmation {{webResponse.body.confirmation}}. |

Prompt:

```
Create a rule named "A2 Joiner day one" with Allow rule trigger enabled. Trigger: work item transitioned to status Done. Condition: work type equals Task and Lifecycle phase equals the option PRE-DAY-ONE, selected from the field options. Then branch for each linked work item with link type "relates to". Inside the branch, condition: work type equals "Employee onboarding" and status equals Pre-Day-One, and a Related work items condition that all work items linked with "relates to" match the JQL statusCategory = Done. Then send a web request: method POST, URL https://<your-console>.vercel.app/api/badge, headers Content-Type application/json and X-JML-Secret (leave the value empty, I will paste it), body as custom data {"badge_number":"{{issue.Badge number}}","action":"activate","reference":"{{issue.key}}","source":"Jira Automation (Joiner day one)"}, and wait for the response before continuing. Then transition the branch work item using "Day one". Then comment on it: "Day one for {{issue.Start date}}. Badge {{issue.Badge number}} activated. SENTRIA confirmation {{webResponse.body.confirmation}}." Do not use a scheduled trigger and do not add a Lookup work items step.
```

Optional production variant "A2s Joiner day one (nightly)": Scheduled daily 06:00 with the JQL on the trigger (`project = JML AND type = "Employee onboarding" AND status = "Pre-Day-One" AND "Start date" <= now()`), same condition and actions. Keep it disabled during the talk.

### A3. Mover revoke before grant

Trigger: Work item transitioned to Revoking (the Approve transition lands here). Condition: Work type = HR request (with approval). Preferred: a Rovo agent action invoking **Access Audit** with "Audit {{issue.key}}. Produce REVOKE, GRANT, RETAINED, DRIFT and create the tasks with blocking links." Fallback (what we built): the rule creates the tasks itself for Marcus's known diff.

| # | Action | Values |
| --- | --- | --- |
| 1 | Create Task | REVOKE: Standard Sales Access (Salesforce.com) for {{issue.Employee ID}}. Fan-out team IT. Lifecycle phase REVOKE. Link relates to trigger. Then Create variable `revokeKey` = {{createdIssue.key}} |
| 2 | Create Task | GRANT: Advanced Support Services (JSM admin) for {{issue.Employee ID}}. IT. GRANT. Link is blocked by {{revokeKey}}; relates to trigger |
| 3 | Create Task | GRANT: Standard Developer (Jira Align, JSM, Jira Software) for {{issue.Employee ID}}. IT. GRANT. Same links |
| 4 | Create Task | Facilities: badge {{issue.Badge number}} zones, add Lab 2A and 24/7 floors. Facilities. GRANT. Same links |
| 5 | Comment | Access audit complete. REVOKE: Standard Sales Access. GRANT: Advanced Support Services, Standard Developer. RETAINED: Standard Employee (Workday, GSuite, JSM, Loom). Grants are blocked until revokes are done. |

Prompt:

```
Create a rule named "A3 Mover revoke before grant" with Allow rule trigger enabled. Trigger: work item transitioned to status Revoking. Condition: work type equals "HR request (with approval)". Then create a Task in this same project with summary "REVOKE: Standard Sales Access (Salesforce.com) for {{issue.Employee ID}}", Fan-out team option IT, Lifecycle phase option REVOKE; link it to the trigger work item with link type "relates to"; then create a variable named revokeKey with value {{createdIssue.key}}. Then create three more Tasks, and after each one link the most recently created work item to {{revokeKey}} with link type "is blocked by" and to the trigger work item with "relates to": summary "GRANT: Advanced Support Services (JSM admin) for {{issue.Employee ID}}" with Fan-out team option IT and Lifecycle phase option GRANT; summary "GRANT: Standard Developer (Jira Align, JSM, Jira Software) for {{issue.Employee ID}}" with Fan-out team option IT and Lifecycle phase option GRANT; summary "Facilities: badge {{issue.Badge number}} zones, add Lab 2A and 24/7 floors" with Fan-out team option Facilities and Lifecycle phase option GRANT. Then comment on the trigger work item: "Access audit complete. REVOKE: Standard Sales Access. GRANT: Advanced Support Services, Standard Developer. RETAINED: Standard Employee (Workday, GSuite, JSM, Loom). Grants are blocked until revokes are done." Select all Lifecycle phase and Fan-out team values from the field options, not as free text. Every Link step must have a link type chosen.
```

If the Create variable step comes out as "Variable name {{createdIssue.key}}, Smart value revokeKey" (Rovo swapped them once), correct it: name `revokeKey`, smart value `{{createdIssue.key}}`.

### A4. Mover advances

Trigger: Work item transitioned to Done. Condition: Work type = Task AND Lifecycle phase = REVOKE. Branch: linked work items, link type "blocks". Branch condition: Work type = HR request (with approval) AND status = Revoking AND Related work items (linked, is blocked by) all match status = Done. Actions: transition "Revokes complete"; comment "All revokes done. Access is now clear to grow. GRANT tasks are unblocked."

```
Create a rule named "A4 Mover advances" with Allow rule trigger enabled. Trigger: work item transitioned to status Done. Condition: work type equals Task and Lifecycle phase equals the option REVOKE (select it from the field options). Then branch for each linked work item where the link type is "blocks". Inside the branch, condition: work type equals "HR request (with approval)" and status equals Revoking, and a related work items condition that all work items linked with "is blocked by" are in status Done. Then transition the branch work item using "Revokes complete" and comment: "All revokes done. Access is now clear to grow. GRANT tasks are unblocked."
```

Note: the REVOKE task is linked to the Mover with "relates to" and to the GRANT tasks with "blocks". Branching on "blocks" from the REVOKE task reaches the GRANT tasks, not the Mover. If the branch finds nothing, change the branch to "relates to" and keep the condition on work type, which filters out the Tasks.

### A5. Leaver countdown

Trigger: Scheduled, daily 07:00, JQL on the trigger: `project = JML AND type = "Employee offboarding" AND status in (Open, "Knowledge Audit") AND ("Last day" = startOfDay("+21d") OR "Last day" = startOfDay("+7d"))`. Actions: comment "{{issue.Manager}} The last day on record is {{issue.Last day}}. Reply "confirmed" if that is still correct, or give the new date. Deprovisioning will not run without confirmation." then transition "Request confirmation".

```
Create a scheduled rule named "A5 Leaver countdown" that runs every day at 7:00 AM. Put the JQL on the Scheduled trigger itself using the option to run a JQL search and execute actions for each work item: project = JML AND type = "Employee offboarding" AND status in (Open, "Knowledge Audit") AND ("Last day" = startOfDay("+21d") OR "Last day" = startOfDay("+7d")). Do not add a separate Lookup work items step. For each work item, add a comment: "{{issue.Manager}} The last day on record is {{issue.Last day}}. Reply confirmed if that is still correct, or give the new date. Deprovisioning will not run without confirmation." Then transition the work item using "Request confirmation".
```

### A5b. Manager confirmation received

Trigger: Work item commented. Condition: Work type = Employee offboarding AND status = Awaiting Manager Confirmation AND comment body contains "confirmed". Actions: transition "Manager confirmed"; edit Knowledge audit status = In progress; comment "Confirmed by {{comment.author.displayName}}. Knowledge Audit agent is inventorying owned pages, runbooks, and work items."

```
Create a rule named "A5b Manager confirmation received". Trigger: work item commented. Condition: work type equals "Employee offboarding", status equals "Awaiting Manager Confirmation", and the comment body contains "confirmed". Then transition the work item using "Manager confirmed". Then edit the work item and set Knowledge audit status to the option "In progress", selected from the field options. Then comment: "Confirmed by {{comment.author.displayName}}. Knowledge Audit agent is inventorying owned pages, runbooks, and work items."
```

### A6. Leaver fan-out

Trigger: Work item transitioned to Deprovisioning. Condition: Work type = Employee offboarding. Seven Tasks, all Lifecycle phase DEPROVISION, linked relates to the Leaver (runbook steps 2 to 8; step 1 is A7):

| # | Summary | Fan-out team |
| --- | --- | --- |
| 1 | Security: revoke all badge zones for {{issue.Badge number}}, verify none remain including decommissioned zones | Security |
| 2 | IT: disable identity for {{issue.Employee ID}}: SSO, MFA, directory set to Departed | IT |
| 3 | IT: remove entitlements for {{issue.Employee ID}}: every Access Policy on the Role plus any Approved Access drift | IT |
| 4 | Successor: transfer Confluence ownership from {{issue.Employee ID}} (label owner-{{issue.Employee ID}}) | Manager |
| 5 | Manager: reassign open Jira work items and automation rules owned by {{issue.Employee ID}} | Manager |
| 6 | Facilities: collect laptop, phone, badge, keys; mark hardware Returned | Facilities |
| 7 | Payroll and Legal: final pay, benefits, exit documents | Payroll |

Then edit Deprovisioning status = In progress; comment "Deprovisioning started per the Leaver Deprovisioning Runbook (SECOPS). Badge first, identity second, entitlements third."

```
Create a rule named "A6 Leaver fan-out" with Allow rule trigger enabled. Trigger: work item transitioned to status Deprovisioning. Condition: work type equals "Employee offboarding". Then create seven Task work items in this same project, each with Lifecycle phase option DEPROVISION, and after each one link the most recently created work item to the trigger work item with link type "relates to": (1) "Security: revoke all badge zones for {{issue.Badge number}}, verify none remain including decommissioned zones" with Fan-out team option Security; (2) "IT: disable identity for {{issue.Employee ID}}: SSO, MFA, directory set to Departed" with Fan-out team option IT; (3) "IT: remove entitlements for {{issue.Employee ID}}: every Access Policy on the Role plus any Approved Access drift" with Fan-out team option IT; (4) "Successor: transfer Confluence ownership from {{issue.Employee ID}} (label owner-{{issue.Employee ID}})" with Fan-out team option Manager; (5) "Manager: reassign open Jira work items and automation rules owned by {{issue.Employee ID}}" with Fan-out team option Manager; (6) "Facilities: collect laptop, phone, badge, keys; mark hardware Returned" with Fan-out team option Facilities; (7) "Payroll and Legal: final pay, benefits, exit documents" with Fan-out team option Payroll. Then edit the trigger work item and set Deprovisioning status to the option "In progress". Then comment: "Deprovisioning started per the Leaver Deprovisioning Runbook (SECOPS). Badge first, identity second, entitlements third." Select all Lifecycle phase, Fan-out team, and Deprovisioning status values from the field options, not as free text. Every Link step must have a link type chosen.
```

### A7. Badge deactivation (the live moment)

Trigger: Work item transitioned to Deprovisioning. Condition: Work type = Employee offboarding AND Badge number is not empty. Actions: web request deactivate (delay until response), comment "SENTRIA: badge {{issue.Badge number}} set to INACTIVE. Confirmation {{webResponse.body.confirmation}}. Door controller updated.", create Task "Security: confirm badge {{issue.Badge number}} INACTIVE in SENTRIA" (Security, DEPROVISION, Evidence https://<your-console>.vercel.app, relates to trigger) and transition it to Done. If the builder offers "Edit Assets object", also set the JML Badge object's Status to INACTIVE and Deactivation Ref to {{issue.key}} between the web request and the comment.

```
Create a rule named "A7 Badge deactivation" with Allow rule trigger enabled. Trigger: work item transitioned to status Deprovisioning. Condition: work type equals "Employee offboarding" and the field "Badge number" is not empty. Then send a web request: method POST, URL https://<your-console>.vercel.app/api/badge, headers Content-Type application/json and X-JML-Secret (leave the value empty, I will paste it), body as custom data {"badge_number":"{{issue.Badge number}}","action":"deactivate","reference":"{{issue.key}}","source":"Jira Automation (Badge deactivation)"}, and wait for the response before continuing. Then comment on the trigger work item: "SENTRIA: badge {{issue.Badge number}} set to INACTIVE. Confirmation {{webResponse.body.confirmation}}. Door controller updated." Then create a Task in this same project with summary "Security: confirm badge {{issue.Badge number}} INACTIVE in SENTRIA", Fan-out team option Security, Lifecycle phase option DEPROVISION, Evidence https://<your-console>.vercel.app; link the most recently created work item to the trigger work item with link type "relates to"; then transition the most recently created work item to Done. Select Fan-out team and Lifecycle phase from the field options, not as free text. Every Link step must have a link type chosen.
```

### A8. Leaver verified

Trigger: Work item transitioned to Done. Condition: Work type = Task AND Lifecycle phase = DEPROVISION. Branch: linked work items, relates to. Branch condition: Work type = Employee offboarding AND all related Tasks with Lifecycle phase DEPROVISION are Done. Preferred action: Rovo agent action invoking **Deprovisioning** with "Verify {{issue.key}} against the Leaver Deprovisioning Runbook and post the closure report as a comment. Create STILL-RUNNING tasks for any finding." Fallback: comment "All deprovisioning tasks done. Run the Deprovisioning agent for the closure report." and transition "Verify".

```
Create a rule named "A8 Leaver verified" with Allow rule trigger enabled. Trigger: work item transitioned to status Done. Condition: work type equals Task and Lifecycle phase equals the option DEPROVISION (select it from the field options). Then branch for linked work items with link type "relates to". Inside the branch, condition: work type equals "Employee offboarding" and a related work items condition that all work items linked with "relates to" that are Tasks with Lifecycle phase DEPROVISION are in status Done. Then, if a Rovo agent action is available, invoke the agent named "Deprovisioning" with the prompt "Verify {{issue.key}} against the Leaver Deprovisioning Runbook and post the closure report as a comment. Create STILL-RUNNING tasks for any finding." If no Rovo agent action is available, instead comment "All deprovisioning tasks done. Run the Deprovisioning agent for the closure report." and transition the branch work item using "Verify".
```

### Demo reset

Trigger: Work item commented, body contains `#reset`. Condition: Work type = Employee offboarding. Actions: web request activate badge (reference "Demo reset"); branch JQL `type = Task AND "Lifecycle phase" in (DEPROVISION, REVOKE, GRANT, PRE-DAY-ONE, STILL-RUNNING) AND issue in linkedIssues("{{issue.key}}")` and delete each; edit Deprovisioning status = Not started and Knowledge audit status = Not started; comment "Demo reset complete. Badge {{issue.Badge number}} reactivated (confirmation {{webResponse.body.confirmation}}) and fan-out tasks removed."

```
Create a rule named "Demo reset". Trigger: work item commented. Condition: work type equals "Employee offboarding" and the comment body contains "#reset". Then send a web request: method POST, URL https://<your-console>.vercel.app/api/badge, headers Content-Type application/json and X-JML-Secret (leave the value empty, I will paste it), body as custom data {"badge_number":"{{issue.Badge number}}","action":"activate","reference":"Demo reset","source":"Demo reset"}, and wait for the response. Then branch over work items matching the JQL: type = Task AND "Lifecycle phase" in (DEPROVISION, REVOKE, GRANT, PRE-DAY-ONE, STILL-RUNNING) AND issue in linkedIssues("{{issue.key}}"), and delete each of them. Then edit the trigger work item and set Deprovisioning status to the option "Not started" and Knowledge audit status to the option "Not started", selected from the field options. Then comment on the trigger work item: "Demo reset complete. Badge {{issue.Badge number}} reactivated (confirmation {{webResponse.body.confirmation}}) and fan-out tasks removed."
```

After a reset also: transition the Leaver back toward Open (Cancel then recreate, or edit status if allowed), set the Assets Badge object Status back to ACTIVE, and clear `badge_events` rows with source like 'Jira Automation%' in Supabase so the console feed starts clean.

## Routing IT and Security tasks to ITF (after the drafts)

The prompts create every task "in this same project". After Rovo drafts each rule, change the **Project** on these create steps to **IT Fulfilment (ITF)** and set the rule scope to **JML + ITF**:

| Rule | Create steps that go to ITF |
| --- | --- |
| A1 | IT: provision ... |
| A3 | REVOKE: ..., both GRANT: ... (the Facilities task stays in JML) |
| A6 | Security: revoke all badge zones ..., IT: disable identity ..., IT: remove entitlements ... |
| A7 | Security: confirm badge ... INACTIVE |

A2, A4, A8 and Demo reset trigger on tasks that may now be in ITF: set their scope to JML + ITF too. Demo reset's JQL has no `project = JML` clause for the same reason.

## A9. SLA breach escalation (Time to SLA)

Trigger: **Incoming webhook**, option "Issues provided in the webhook". The webhook is called by a Time to SLA "Trigger Jira automation" action on each SLA (see 07), which sends the breached work item.

| # | Action | Values |
| --- | --- | --- |
| 1 | Edit work item | Labels: add `sla-breach-flagged` |
| 2 | Branch | Linked work items, relates to |
| 3 | Condition (in branch) | Work type = Employee offboarding |
| 4 | Comment (in branch) | SLA breached on {{triggerIssue.summary}}, owner {{triggerIssue.Fan-out team}} |
| 5 | Edit (in branch) | Deprovisioning status = Findings open |

Scope JML + ITF. After saving the trigger, copy its webhook URL and secret into the Time to SLA action. Breaches on Mover REVOKE tasks only get the label (the linked item is not an Employee offboarding).

```
Create a rule named "A9 SLA breach escalation". Trigger: incoming webhook, with the issues provided in the webhook. Then edit the work item and add the label sla-breach-flagged. Then branch for each linked work item with link type "relates to". Inside the branch, condition: work type equals "Employee offboarding". Then comment: "SLA breached on {{triggerIssue.summary}}, owner {{triggerIssue.Fan-out team}}". Then edit the branch work item and set Deprovisioning status to the option "Findings open", selected from the field options.
```

## A10. Link agent tasks

Rovo agents cannot link work items (there is no link tool), so this rule does it. Trigger: **Work item created**, scope JML + ITF. Condition: `{{issue.summary}}` matches the regex `(Handover:|STILL RUNNING:).*`. Then create the variable `empId` = `{{issue.summary.match(".*(?:from|for) ([A-Za-z0-9._-]+).*")}}`. Then branch over JQL `project = JML AND type = "Employee offboarding" AND text ~ "{{empId}}" AND statusCategory != Done` and **link** the branch item to the trigger item with "relates to".

`text ~` is used because a Short text custom field like Employee ID may not be JQL-searchable; the seeds carry the employee ID in their description. The agents' instructions must keep the summary formats "Handover: [group] from [employee ID] to [successor]" and "STILL RUNNING: [what] for [employee ID]".

## Demo: teams done (stage helper)

Days pass between "Start deprovisioning" and "Verify" in real life; on stage they pass in one comment. Trigger: **Work item commented**, condition work type = Employee offboarding and the comment contains `#teams-done`.
- Branch over `issue in linkedIssues("{{issue.key}}", "relates to") AND statusCategory != Done AND summary !~ "\"STILL RUNNING\""`, minus the Security "revoke all badge zones" task. For each one, set Evidence, comment "Evidence: …" (the entitlements task names every Access Policy on the role), and transition to Done.
- **Lookup objects** (Facilities, `objectTypeId = <Badge type id> AND "Badge Number" = "{{issue.customfield_<badge number field id>}}"`), then **Send web request** PUT `https://api.atlassian.com/jsm/assets/workspace/<workspace id>/v1/object/{{lookupObjects.id}}`. The body sets Status = INACTIVE, Deactivation Ref = {{issue.key}} and Zones = only the decommissioned zone.
- **Lookup objects** (People, by Employee ID), then the same kind of PUT clearing **Approved Access**.
- Each web request has a hidden **Authorization** header `Basic <base64 of email:api-token>` that you paste in the UI.

Why web requests: Jira's **Edit object** action fails with "can't run" in a rule triggered by a work item, because no Assets object is in context. It also stops the rest of the rule. Lookup objects plus the Assets REST API works.

Leaving the badge-zones task open is deliberate: it is the runbook step that missed the legacy zone, and an open DEPROVISION task stops A8 from verifying the Leaver.
