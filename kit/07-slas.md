# 07. SLAs: native JSM SLAs and Appfire Time to SLA

Two levels of clock. The **service promise** lives on the request as a native JSM SLA. The **operational clocks** live on the IT and Security fan-out tasks in ITF, using Appfire Time to SLA. A breach on a task rolls up to the Leaver through rule A9.

| Level | Where | Tool | Clock |
| --- | --- | --- | --- |
| Service promise | JML Leaver | Native JSM SLA "Deprovisioning verified" | 4 business hours: starts entering Deprovisioning, stops entering Verified |
| Service promise | JML Mover | Native JSM SLA "Revokes complete" | 1 business day (8 h): starts entering Revoking, stops entering Granting |
| Operational | ITF tasks | Time to SLA | Badge zones revoked, Identity disabled, Entitlements removed, Revoke access (below) |
| Roll-up | JML Leaver | Automation rule A9 | Time to SLA breach on an ITF task → comment on the linked Leaver, Deprovisioning status = Findings open |

## 7.1 Native JSM SLAs (JML)

Project settings → SLAs → Create SLA, twice:

| Name | Start | Stop | Goal | Calendar |
| --- | --- | --- | --- | --- |
| Deprovisioning verified | Entered Status: Deprovisioning | Entered Status: Verified | `type = "Employee offboarding"` → 4h | 9-5 business calendar |
| Revokes complete | Entered Status: Revoking | Entered Status: Granting | `type = "HR request (with approval)"` → 8h | 9-5 business calendar |

Leave "All remaining work items" without a goal.

By API (internal, what the UI uses): `POST $SITE/rest/servicedesk/1/servicedesk/agent/JML/sla/metrics` with header `X-Atlassian-Token: no-check`. Conditions are `{"pluginKey":"com.atlassian.servicedesk","factoryKey":"status-sla-condition-factory","conditionId":"<status id>","type":"Start|Stop","name":"Entered Status: <name>"}`; goals are `{"jqlQuery":..., "duration": <ms>, "calendarId": <id>}`. `GET` the same URL first to see your calendars and the exact shape.

## 7.2 Time to SLA definitions (ITF)

Install **Time to SLA** (Appfire) from the Marketplace and make sure app access rules allow it in ITF. Then SLAs → Create, four times. Common settings:

- **Scope:** project ITF. The per-SLA filter goes on the goal as a JQL ("Goal applies to: JQL").
- **Start:** Issue created (date field `created`).
- **Stop:** Status changed to Done.
- **Pause:** none. Nothing in ITF waits on a customer, and a pause would hide a breach on stage.
- **Calendars:** 24/7 (built in) and a business-hours calendar (Mon to Fri 09:00 to 17:00 in your time zone).

| SLA | Description | Goal name | Goal | Calendar | Goal JQL |
| --- | --- | --- | --- | --- | --- |
| Badge zones revoked | Time from creation of the Security badge-zone task to Done. Badge access, including decommissioned zones, must be removed fast. | Badge zones revoked within 15 min (demo; 30 min in production) | 15m | 24/7 | `project = ITF AND "Fan-out team" = Security AND summary ~ "revoke all badge zones"` |
| Identity disabled | Time from creation of the IT disable-identity task (SSO, MFA, directory set to Departed) to Done. | Identity disabled within 1 hour | 1h | 24/7 | `project = ITF AND summary ~ "disable identity"` |
| Entitlements removed | Time from creation of the IT remove-entitlements task (every Access Policy on the Role plus Approved Access drift) to Done. | Entitlements removed within 4 business hours | 4h | Business hours | `project = ITF AND summary ~ "remove entitlements"` |
| Revoke access | Time from creation of a Mover REVOKE task to Done. Grants stay blocked until revokes finish, so this clock bounds how long a transfer waits. | Revoke completed within 2 business hours | 2h | Business hours | `project = ITF AND "Lifecycle phase" = "REVOKE"` |

The 15-minute badge goal is deliberate: if nobody closes the badge task during the talk, it breaches and A9 flips the Leaver to Findings open on its own.

## 7.3 Breach action → A9

On each SLA: Actions → New action → **Trigger Jira automation**.

- Apply to: Single SLA (the one you are editing), All goals
- Trigger when SLA: **is breached**
- Run with permissions of: you
- Automation webhook URL and secret: from rule A9's Incoming webhook trigger (05)

Also consider disabling the app's global default action (email the assignee at 50%): fan-out tasks have no assignee, so it fails on every one.

## 7.4 Time to SLA REST API (optional)

You can script all of 7.2 and 7.3. Create a token in Time to SLA → Settings → API Token and use your data-residency base URL (shown on that page, for example `https://tts-us.snapbytesapps.com`); cross-region calls are refused. The live API differs from the published Postman collection:

- `POST /api/sla`: scope is `slaScope: {"projectIds": [...]}` only; the JQL goes on the goal: `"goalIssues": "JQL", "jql": "..."`.
- Event rules are a tree: a `NODE` (`conditionType: "OR"`) with `LEAF` children. Start on created: `{"eventType":"START","sourceType":"DATE_TIME_FIELD","context":{"fieldId":"created"},"ruleType":"LEAF"}`. Stop on Done: `sourceType: "CHANGE_HISTORY"`, `fieldKey: "status"`, `fieldChangeType: "CHANGED_TO"`, values `[{"ids":["<done status ids>"],"label":"Done"}]`.
- Easiest path: build one SLA in the UI, `GET /api/sla/{id}`, and clone its JSON for the others.
- `POST /api/calendar` creates calendars; 24/7 is `calendarId: "7x24"`.
- `POST /api/notifier` creates the breach action: `actionType: "AUTOMATION"`, `thresholdType: "IS_BREACHED"` (not `HAS_BREACHED`, which is accepted but never fires), `slaNotifierActionContext: {"webhooksUrl": ..., "webhookSecret": ...}`, `slaConfiguration: "<sla id>"`.
- `GET /api/issue-sla/{issueId}` shows a work item's clocks (`slaStatus` `STILL` / `EXCEED`), handy for testing with a 1-minute goal.

## 7.5 Build it by API, end to end

Everything in 7.1 to 7.3 can be created with one script: [`scripts/build_slas.py`](scripts/build_slas.py) (Python 3, standard library only). It looks up the ITF project, the Done status ids and the JML statuses by name, then creates whatever is missing: the two JSM SLAs, a business-hours calendar, the four Time to SLA SLAs and their breach actions. It is safe to re-run; anything that already exists by name is skipped.

Before you run it: build rule A9 (05) and copy its webhook URL and secret, and create a Time to SLA API token (Time to SLA → Settings → API Token, which also shows your regional base URL).

```bash
export JIRA_SITE=https://<your-site>.atlassian.net JIRA_EMAIL=<you@example.com> JIRA_TOKEN=<atlassian api token>
export TTS_BASE=https://tts-us.snapbytesapps.com TTS_TOKEN=<time to sla token>
export A9_WEBHOOK_URL=<A9 webhook url> A9_WEBHOOK_SECRET=<A9 webhook secret> TIME_ZONE=America/New_York
```

```bash
python3 kit/scripts/build_slas.py
```

```bash
python3 kit/scripts/build_slas.py --apply
```

The first run only prints the plan. Options: `SKIP_JSM=1` builds only the Time to SLA part, `SLA_ENABLED=false` creates the SLAs disabled, and `NAME_PREFIX="TEST "` prefixes every name for a trial run you can delete afterwards. After creating, open each SLA's **Actions** tab: the app can add default reminder actions to new SLAs, so disable any you do not want (fan-out tasks have no assignee, so assignee emails fail).

### The requests, if you prefer curl

Native JSM SLA (repeat for "Revokes complete" with Revoking → Granting, `type = "HR request (with approval)"`, 28800000 ms). Status ids are from `GET $JIRA_SITE/rest/api/3/statuses/search?projectId=<JML id>`; calendar ids from `calendarRefs` in a `GET` of the same metrics URL:

```bash
curl -u "$JIRA_EMAIL:$JIRA_TOKEN" -H "Content-Type: application/json" -H "X-Atlassian-Token: no-check" \
  -X POST "$JIRA_SITE/rest/servicedesk/1/servicedesk/agent/JML/sla/metrics" -d '{
  "name": "Deprovisioning verified",
  "config": {
    "definition": {
      "start": [{"pluginKey": "com.atlassian.servicedesk", "factoryKey": "status-sla-condition-factory", "conditionId": "<Deprovisioning status id>", "type": "Start", "name": "Entered Status: Deprovisioning", "missing": false}],
      "pause": [],
      "stop":  [{"pluginKey": "com.atlassian.servicedesk", "factoryKey": "status-sla-condition-factory", "conditionId": "<Verified status id>", "type": "Stop", "name": "Entered Status: Verified", "missing": false}]
    },
    "goals": [
      {"jqlQuery": "type = \"Employee offboarding\"", "duration": 14400000, "calendarId": <business calendar id>, "defaultGoal": false, "subGoals": []},
      {"jqlQuery": "", "defaultGoal": true, "subGoals": []}
    ],
    "slaDisplayFormat": "NEW_SLA_FORMAT"
  }}'
```

Time to SLA business-hours calendar (the response `id` is used by the 4h and 2h SLAs):

```bash
curl -H "Authorization: Bearer $TTS_TOKEN" -H "Content-Type: application/json" -X POST "$TTS_BASE/api/calendar" -d '{
  "calendarName": "Business Hours 9-5",
  "businessDayInfo": {"calculationType": "CALENDAR", "isCustom": false},
  "currentBusinessHours": [
    {"day": "Monday", "start": "09:00", "end": "17:00"}, {"day": "Tuesday", "start": "09:00", "end": "17:00"},
    {"day": "Wednesday", "start": "09:00", "end": "17:00"}, {"day": "Thursday", "start": "09:00", "end": "17:00"},
    {"day": "Friday", "start": "09:00", "end": "17:00"}],
  "timeZone": {"id": "America/New_York", "label": "America/New_York"},
  "holidays": [], "sharedHolidays": [], "exceptions": [], "sharedExceptions": [],
  "exceptionsPrecedence": "exceptions_override_holidays"}'
```

Time to SLA SLA (this is "Revoke access"; for the others change `name`, `description`, the goal `name`, `duration`, `calendarId` (`"7x24"` for 24/7) and `jql` as in the 7.2 table). `<ITF project id>` is from `GET $JIRA_SITE/rest/api/3/project/ITF`; the Done ids are every status named Done from `GET $JIRA_SITE/rest/api/3/statuses/search?projectId=<ITF id>&searchString=Done`:

```bash
curl -H "Authorization: Bearer $TTS_TOKEN" -H "Content-Type: application/json" -X POST "$TTS_BASE/api/sla" -d '{
  "name": "Revoke access",
  "description": "Time from creation of a Mover REVOKE task to Done. Grants stay blocked until revokes finish, so this clock bounds how long a transfer waits.",
  "criticalThresholdPercentage": 80,
  "enabled": true,
  "calculationMethod": "ALL_CYCLES",
  "slaScope": {"projectIds": ["<ITF project id>"]},
  "goals": [{
    "name": "Revoke completed within 2 business hours",
    "goalType": "FIXED_DURATION", "context": {"duration": "2h"}, "calendarId": "<business calendar id>",
    "goalIssues": "JQL", "jql": "project = ITF AND \"Lifecycle phase\" = \"REVOKE\"",
    "order": 1, "defaultGoal": true, "enabled": true,
    "priorityIdList": [], "requestTypes": [], "issueTypes": [], "assignees": []}],
  "eventRules": [
    {"eventType": "START", "context": null, "eventContext": null, "ruleType": "NODE", "conditionType": "OR", "childRules": [
      {"eventType": "START", "sourceType": "DATE_TIME_FIELD", "context": {"fieldId": "created"}, "eventContext": null, "ruleType": "LEAF", "childRules": null}]},
    {"eventType": "STOP", "context": null, "eventContext": null, "ruleType": "NODE", "conditionType": "OR", "childRules": [
      {"eventType": "STOP", "sourceType": "CHANGE_HISTORY", "context": {"fieldType": "SYSTEM", "fieldKey": "status", "fieldValueType": "STATUS",
        "fieldChangeType": "CHANGED_TO", "fieldValueCondition": "EQUALS", "values": [{"ids": ["<Done status id>"], "label": "Done"}]},
        "eventContext": null, "ruleType": "LEAF", "childRules": null}]}],
  "intervalRules": [],
  "updateTargetCustomField": false,
  "displayLinkedIssueEnabled": true,
  "shareSlaType": "SHARE_THIS_SLA",
  "displayLinkedIssuesTypes": [{"direction": "inward", "id": "<relates link type id>", "label": "relates to", "value": "<relates link type id>-inward"}],
  "overrideDefaultEventCardinality": false,
  "eventCardinalityMap": null}'
```

Breach action on that SLA (use the `id` the SLA call returned):

```bash
curl -H "Authorization: Bearer $TTS_TOKEN" -H "Content-Type: application/json" -X POST "$TTS_BASE/api/notifier" -d '{
  "enabled": true, "thresholdType": "IS_BREACHED", "duration": null, "actionType": "AUTOMATION",
  "description": "A9 SLA breach escalation",
  "slaNotifierActionContext": {"webhooksUrl": "<A9 webhook url>", "webhookSecret": "<A9 webhook secret>"},
  "appliedToAllGoals": true, "appliedGoals": null, "slaConfiguration": "<sla id>"}'
```

To check a clock while testing: `GET $TTS_BASE/api/issue-sla/<work item id>` (the numeric id, not the key). `slaStatus` is `STILL` while running and `EXCEED` once breached.
