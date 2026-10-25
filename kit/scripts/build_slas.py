"""Build the JML demo SLAs by API: two native JSM SLAs on JML, and the Time to SLA calendar, four SLAs and their
A9 breach actions on ITF. Standard library only. Safe to re-run: anything that already exists (by name) is skipped.

Environment:
  JIRA_SITE           https://<your-site>.atlassian.net
  JIRA_EMAIL          your Atlassian account email
  JIRA_TOKEN          an Atlassian API token
  TTS_BASE            Time to SLA regional base URL, from Time to SLA → Settings → API Token (e.g. https://tts-us.snapbytesapps.com)
  TTS_TOKEN           Time to SLA API token (JWT) from the same page
  A9_WEBHOOK_URL      rule A9's incoming webhook URL (optional: without it, no breach actions are created)
  A9_WEBHOOK_SECRET   rule A9's incoming webhook secret
  TIME_ZONE           business-hours calendar time zone (default America/New_York)
  JSM_CALENDAR        name of the JSM calendar for the native SLAs (default: the first non-24/7 calendar)
  SLA_ENABLED         "false" to create the Time to SLA SLAs disabled (default true)
  NAME_PREFIX         prefix every created name (for a dry test); default none
  SKIP_JSM            "1" to skip the native JSM SLAs (they create a custom field each, so avoid them in tests)

Usage:  python3 build_slas.py            (shows the plan)
        python3 build_slas.py --apply    (creates what is missing)
"""
import base64, json, os, ssl, sys, urllib.error, urllib.parse, urllib.request

APPLY = "--apply" in sys.argv
E = os.environ.get
PREFIX = E("NAME_PREFIX", "")
SITE, TTS = E("JIRA_SITE", "").rstrip("/"), E("TTS_BASE", "").rstrip("/")
JIRA_AUTH = "Basic " + base64.b64encode(f"{E('JIRA_EMAIL', '')}:{E('JIRA_TOKEN', '')}".encode()).decode()
CTX = ssl.create_default_context()
CTX.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)   # Python 3.13 rejects some valid CA chains as "strict"

def call(method, url, auth, body=None, extra=None):
    h = {"Authorization": auth, "Accept": "application/json", **(extra or {})}
    data = None
    if body is not None: data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data, h, method=method), context=CTX) as r:
            t = r.read().decode(); return r.status, json.loads(t) if t else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
def jira(method, path, body=None, extra=None): return call(method, SITE + path, JIRA_AUTH, body, extra)
def tts(method, path, body=None): return call(method, TTS + path, f"Bearer {E('TTS_TOKEN', '')}", body)
def need(ok, what, s, r):
    if not ok: sys.exit(f"{what} failed: {s} {str(r)[:400]}")
def step(msg): print(("  " if APPLY else "  [plan] ") + msg)

# ---------- lookups ----------
s, itf = jira("GET", "/rest/api/3/project/ITF"); need(s == 200, "ITF project", s, itf)
s, jml = jira("GET", "/rest/api/3/project/JML"); need(s == 200, "JML project", s, jml)
def status_ids(project_id, name):
    s, r = jira("GET", f"/rest/api/3/statuses/search?projectId={project_id}&searchString={urllib.parse.quote(name)}&maxResults=50")
    need(s == 200, f"status {name}", s, r)
    return [x["id"] for x in r["values"] if x["name"].lower() == name.lower()]
DONE_IDS = status_ids(itf["id"], "Done"); need(DONE_IDS, "Done status in ITF", 0, "")
s, lt = jira("GET", "/rest/api/3/issueLinkType"); need(s == 200, "link types", s, lt)
RELATES = next((x["id"] for x in lt["issueLinkTypes"] if x["name"] == "Relates"), None); need(RELATES, "link type Relates", 0, "")

# ---------- 1. native JSM SLAs on JML ----------
print("== JSM SLAs (JML)")
METRICS = "/rest/servicedesk/1/servicedesk/agent/JML/sla/metrics"
XSRF = {"X-Atlassian-Token": "no-check"}
s, m = jira("GET", METRICS); need(s == 200, "read JSM SLAs", s, m)
cals = m["calendarRefs"]
cal = next((c for c in cals if c["name"] == E("JSM_CALENDAR")), None) or next((c for c in cals if c["id"] != -1), None)
need(cal, "a JSM business-hours calendar (create one in Project settings → SLAs → Calendars)", 0, "")
have = {x["name"] for x in m["timeMetrics"]}
def entered(kind, status):
    sid = status_ids(jml["id"], status); need(sid, f"JML status {status}", 0, "")
    return {"pluginKey": "com.atlassian.servicedesk", "factoryKey": "status-sla-condition-factory", "conditionId": sid[0],
            "type": kind, "name": f"Entered Status: {status}", "missing": False}
for name, start, stop, jql, hours in [] if E("SKIP_JSM") == "1" else [
        ("Deprovisioning verified", "Deprovisioning", "Verified", 'type = "Employee offboarding"', 4),
        ("Revokes complete", "Revoking", "Granting", 'type = "HR request (with approval)"', 8)]:
    name = PREFIX + name
    if name in have: print(f"  {name}: exists"); continue
    body = {"name": name, "config": {"definition": {"start": [entered("Start", start)], "pause": [], "stop": [entered("Stop", stop)]},
            "goals": [{"jqlQuery": jql, "duration": hours * 3600000, "calendarId": cal["id"], "defaultGoal": False, "subGoals": []},
                      {"jqlQuery": "", "defaultGoal": True, "subGoals": []}], "slaDisplayFormat": "NEW_SLA_FORMAT"}}
    step(f"create JSM SLA {name}: {start} → {stop}, {hours}h on '{cal['name']}' for {jql}")
    if APPLY: s, r = jira("POST", METRICS, body, XSRF); need(s == 200, name, s, r)

# ---------- 2. Time to SLA calendar ----------
print("== Time to SLA (ITF)")
CAL_NAME = PREFIX + "Business Hours 9-5"
s, tcals = tts("GET", "/api/calendar"); need(s == 200, "read calendars (check TTS_BASE region and token)", s, tcals)
bh = next((c["id"] for c in tcals if c["calendarName"] == CAL_NAME), None)
if bh: print(f"  calendar {CAL_NAME}: exists")
else:
    tz = E("TIME_ZONE", "America/New_York")
    cbody = {"calendarName": CAL_NAME, "businessDayInfo": {"calculationType": "CALENDAR", "isCustom": False},
             "currentBusinessHours": [{"day": d, "start": "09:00", "end": "17:00"} for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")],
             "timeZone": {"id": tz, "label": tz}, "holidays": [], "sharedHolidays": [], "exceptions": [], "sharedExceptions": [],
             "exceptionsPrecedence": "exceptions_override_holidays"}
    step(f"create calendar {CAL_NAME} (Mon-Fri 09:00-17:00 {tz})")
    if APPLY: s, r = tts("POST", "/api/calendar", cbody); need(s == 200, "calendar", s, r); bh = r["id"]
    else: bh = "<new calendar id>"

# ---------- 3. Time to SLA SLAs ----------
def sla_body(name, desc, goal_name, duration, calendar, jql):
    leaf_start = {"eventType": "START", "sourceType": "DATE_TIME_FIELD", "context": {"fieldId": "created"}, "eventContext": None, "ruleType": "LEAF", "childRules": None}
    leaf_stop = {"eventType": "STOP", "sourceType": "CHANGE_HISTORY", "context": {"fieldType": "SYSTEM", "fieldKey": "status", "fieldValueType": "STATUS",
                 "fieldChangeType": "CHANGED_TO", "fieldValueCondition": "EQUALS", "values": [{"ids": DONE_IDS, "label": "Done"}]},
                 "eventContext": None, "ruleType": "LEAF", "childRules": None}
    node = lambda kind, leaf: {"eventType": kind, "context": None, "eventContext": None, "ruleType": "NODE", "conditionType": "OR", "childRules": [leaf]}
    return {"name": name, "description": desc, "criticalThresholdPercentage": 80, "enabled": E("SLA_ENABLED", "true") != "false",
            "calculationMethod": "ALL_CYCLES", "slaScope": {"projectIds": [itf["id"]]},
            "goals": [{"name": goal_name, "goalType": "FIXED_DURATION", "context": {"duration": duration}, "calendarId": calendar,
                       "goalIssues": "JQL", "jql": jql, "order": 1, "defaultGoal": True, "enabled": True,
                       "priorityIdList": [], "requestTypes": [], "issueTypes": [], "assignees": []}],
            "eventRules": [node("START", leaf_start), node("STOP", leaf_stop)], "intervalRules": [],
            "updateTargetCustomField": False, "displayLinkedIssueEnabled": True, "shareSlaType": "SHARE_THIS_SLA",
            "displayLinkedIssuesTypes": [{"direction": "inward", "id": RELATES, "label": "relates to", "value": f"{RELATES}-inward"}],
            "overrideDefaultEventCardinality": False, "eventCardinalityMap": None}
SLAS = [
 ("Badge zones revoked", "Time from creation of the Security badge-zone task to Done. Badge access, including decommissioned zones, must be removed fast.",
  "Badge zones revoked within 15 min (demo; 30 min in production)", "15m", "7x24", 'project = ITF AND "Fan-out team" = Security AND summary ~ "revoke all badge zones"'),
 ("Identity disabled", "Time from creation of the IT disable-identity task (SSO, MFA, directory set to Departed) to Done.",
  "Identity disabled within 1 hour", "1h", "7x24", 'project = ITF AND summary ~ "disable identity"'),
 ("Entitlements removed", "Time from creation of the IT remove-entitlements task (every Access Policy on the Role plus Approved Access drift) to Done.",
  "Entitlements removed within 4 business hours", "4h", bh, 'project = ITF AND summary ~ "remove entitlements"'),
 ("Revoke access", "Time from creation of a Mover REVOKE task to Done. Grants stay blocked until revokes finish, so this clock bounds how long a transfer waits.",
  "Revoke completed within 2 business hours", "2h", bh, 'project = ITF AND "Lifecycle phase" = "REVOKE"'),
]
s, existing = tts("GET", "/api/sla/"); need(s == 200, "read SLAs", s, existing)
by_name = {x["name"]: x["id"] for x in existing}
url, secret = E("A9_WEBHOOK_URL"), E("A9_WEBHOOK_SECRET")
for name, desc, goal, dur, calendar, jql in SLAS:
    name = PREFIX + name
    sid = by_name.get(name)
    if sid: print(f"  SLA {name}: exists (id {sid})")
    else:
        step(f"create SLA {name}: {dur} on {'24/7' if calendar == '7x24' else CAL_NAME}, start created, stop Done, goal JQL {jql}")
        if APPLY: s, r = tts("POST", "/api/sla", sla_body(name, desc, goal, dur, calendar, jql)); need(s == 200, name, s, r); sid = r["id"]
    # ---------- 4. breach action → A9 ----------
    if not url: continue
    if sid:
        s, acts = tts("GET", f"/api/notifier/sla/{sid}")
        if s == 200 and any(a.get("actionType") == "AUTOMATION" for a in (acts or [])): print(f"    breach action: exists"); continue
    step(f"  add breach action on {name}: Trigger Jira automation → A9 when the SLA is breached")
    if APPLY and sid:
        s, r = tts("POST", "/api/notifier", {"enabled": True, "thresholdType": "IS_BREACHED", "duration": None, "actionType": "AUTOMATION",
                 "description": "A9 SLA breach escalation", "slaNotifierActionContext": {"webhooksUrl": url, "webhookSecret": secret},
                 "appliedToAllGoals": True, "appliedGoals": None, "slaConfiguration": str(sid)})
        need(s == 200, f"breach action on {name}", s, r)
print("\nDone." if APPLY else "\nPlan only. Re-run with --apply to create what is missing.")
