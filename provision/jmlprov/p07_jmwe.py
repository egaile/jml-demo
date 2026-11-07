"""Phase 7 (Appfire edition): JMWE post-functions and the revoke-before-grant validator, written onto the Jira workflows through
Jira's workflow API. JMWE event-based and scheduled actions (A5, A5b, A10) have no API and stay in the manual guide."""
import copy, json, uuid


def detect(ctx):
    """The JMWE Forge extension prefix, read from the workflow capabilities API; None when JMWE is not installed."""
    W = ctx.S.get("workflows", {}).get("JML: Joiner")
    if not W: return None
    s, r = ctx.site.get(f"/rest/api/3/workflows/capabilities?workflowId={W['id']}")
    for x in (r.get("forgeRules", []) if s == 200 else []):
        if x.get("id", "").endswith("/ScriptedPostFunction") and "JMWE" in x.get("name", ""): return x["id"].rsplit("/", 1)[0] + "/"
    return None


class Jmwe:
    def __init__(self, ctx, ext):
        self.ctx, self.site, self.EXT = ctx, ctx.site, ext
    def read(self, name):
        s, r = self.site.post("/rest/api/3/workflows?expand=values.transitions", {"workflowNames": [name]})
        self.ctx.need(s == 200 and r.get("workflows"), f"cannot read workflow {name}: {s}"); return r
    def pf(self, module, config): return {"ruleKey": "forge:workflow-post-function", "parameters": {"key": self.EXT + module, "config": json.dumps(config), "id": str(uuid.uuid4())}}
    def validator(self, module, config): return {"ruleKey": "forge:expression-validator", "parameters": {"key": self.EXT + module, "config": json.dumps(config), "id": str(uuid.uuid4())}}
    def write(self, r, edit, what):
        w = copy.deepcopy(r["workflows"][0]); edit(w)
        body = {"statuses": [{k: v for k, v in s.items() if k in ("id", "name", "statusCategory", "statusReference", "description")} for s in r["statuses"]],
                "workflows": [{k: w[k] for k in ("id", "version", "name", "description", "statuses", "transitions", "startPointLayout", "loopedTransitionContainerLayout") if k in w}]}
        res = self.ctx.do(what, self.site.post, "/rest/api/3/workflows/update", body)
        if res and res[0] != 200: self.ctx.warn(f"{what}: {res[0]} {str(res[1])[:400]}")
    @staticmethod
    def transition(w, name): return next(t for t in w["transitions"] if t["name"] == name)
    @staticmethod
    def transitions_to(r, status_name):
        ids = {s["statusReference"]: s["name"] for s in r["statuses"]}
        w = r["workflows"][0]; hits = [t for t in w["transitions"] if ids.get(t.get("toStatusReference")) == status_name and t["type"] != "INITIAL"]
        named = [t for t in hits if t["name"] in ("Mark as done", "Done")]
        return named or hits
    def create_issue(self, project, summary, fields, link, condition=None):
        cfg = {"navigateToNewIssue": False, "runAsType": "currentUser", "conditionalExecution": bool(condition), "scriptType": "Nunjucks", "project": project,
               "issuetype": str(self.ctx.S["issueTypes"]["Task"]), "selectedLinkType": link, "copyAllFields": False, "copyScreenFields": False, "ignoreInapplicableFields": True,
               "copySubtasks": False, "ignoreDeactivatedUsers": False, "fields": {"summary": {"action": "set", "value": summary}, **{k: {"action": "set", "value": v} for k, v in fields.items()}},
               "copyCommentToNewIssue": False, "copyAllCommentsToNewIssue": False, "copyCommentVisibility": "original-visibility", "commentAsType": "currentUser", "isUseCurrentUserForReporter": True}
        if condition: cfg["conditionalExecutionScript"] = condition
        return self.pf("CreateIssueFunction", cfg)
    def comment(self, text): return self.pf("CommentIssueFunction", {"targetIssue": "currentIssue:*", "comment": text, "conditionalExecution": False, "scriptType": "Nunjucks", "runAsType": "currentUser"})
    def set_fields(self, pairs): return self.pf("SetFieldValueFunction", {"runAsType": "currentUser", "fieldsConfig": [{"fieldId": f, "options": {}, "value": v} for f, v in pairs], "sendNotifications": True, "targetIssue": "currentIssue:*", "conditionalExecution": False, "scriptType": "Nunjucks"})
    def script(self, nunjucks, description): return self.pf("ScriptedPostFunction", {"scriptDescription": description, "script": nunjucks, "isDelayed": False})


def has(t, marker, kind="actions"): return any(marker in a.get("parameters", {}).get("config", "") for a in t.get(kind, []))


def run(ctx):
    if not ctx.edition["jmwe"]: return
    S = ctx.S
    if not (S.get("workflows") and S.get("fields") and S.get("itf")): ctx.plan("install the JMWE post-functions (after the workflows and fields exist)"); return
    ext = detect(ctx)
    if not ext: ctx.note("jmwe", "missing", True); ctx.say("JMWE is not installed on this site: install it from the Marketplace, then rerun with --only jmwe"); return
    ctx.state.set("jmwe", extensionPrefix=ext); j = Jmwe(ctx, ext); F = S["fields"]
    LP, TEAM, EMP, BADGE, START, MGR, DP = F["Lifecycle phase"], F["Fan-out team"], F["Employee ID"], F["Badge number"], F["Start date"], F["Manager"], F["Deprovisioning status"]
    role, emp, badge, start = (f"{{{{ issue.fields.{F['Role']} }}}}", f"{{{{ issue.fields.{EMP} }}}}", f"{{{{ issue.fields.{BADGE} }}}}", f"{{{{ issue.fields.{START} }}}}")
    LINK = f"outward:{S['linkTypes']['Relates']}"
    # A1 Joiner fan-out
    r = j.read("JML: Joiner"); t = j.transition(r["workflows"][0], "Fan out")
    if has(t, '"PRE-DAY-ONE"'): ctx.say("JMWE A1 (Fan out) present")
    else:
        task = lambda project, summary, team, extra=None: j.create_issue(project, summary, {LP: "PRE-DAY-ONE", TEAM: team, **(extra or {})}, LINK)
        pfs = [task("ITF", f"IT: provision {role} entitlements for {emp}", "IT", {"description": f"Provision from Role Profile {role}. Policies and applications are on the Role object in Assets and the Confluence page labeled role-profile. Attach evidence per application."}),
               task("$sameAsCurrentIssue$", f"Facilities: issue badge {badge} and assign desk", "Facilities", {"description": "Badge zones per Role Profile. Do not issue before Legal confirms signed agreements."}),
               task("$sameAsCurrentIssue$", f"Legal: confirm signed agreements for {emp}", "Legal"),
               task("$sameAsCurrentIssue$", f"Payroll: set up {emp} in Workday, start {start}", "Payroll"),
               task("$sameAsCurrentIssue$", f"Manager: orientation plan and required training for {emp}", "Manager", {"assignee": f"{{{{ issue.fields.{MGR}[0].accountId if issue.fields.{MGR} else '' }}}}"}),
               j.comment(f"Fan-out created (JMWE): IT, Facilities, Legal, Payroll, Manager. Badge {badge} activates on {start} once Legal and Facilities tasks are done.")]
        def edit(w): tt = j.transition(w, "Fan out"); tt["actions"] = pfs; tt["validators"] = []
        j.write(r, edit, "JMWE A1: five Create issue post-functions + comment on JML: Joiner / Fan out")
    # A6 Leaver fan-out
    r = j.read("JML: Leaver"); t = j.transition(r["workflows"][0], "Start deprovisioning")
    if has(t, '"DEPROVISION"'): ctx.say("JMWE A6 (Start deprovisioning) present")
    else:
        task = lambda project, summary, team: j.create_issue(project, summary, {LP: "DEPROVISION", TEAM: team}, LINK)
        pfs = [task("ITF", f"Security: revoke all badge zones for {badge}, verify none remain including decommissioned zones", "Security"),
               task("ITF", f"IT: disable identity for {emp}: SSO, MFA, directory set to Departed", "IT"),
               task("ITF", f"IT: remove entitlements for {emp}: every Access Policy on the Role plus any Approved Access drift", "IT"),
               task("$sameAsCurrentIssue$", f"Successor: transfer Confluence ownership from {emp} (label owner-{emp})", "Manager"),
               task("$sameAsCurrentIssue$", f"Manager: reassign open Jira work items and automation rules owned by {emp}", "Manager"),
               task("$sameAsCurrentIssue$", "Facilities: collect laptop, phone, badge, keys; mark hardware Returned", "Facilities"),
               task("$sameAsCurrentIssue$", "Payroll and Legal: final pay, benefits, exit documents", "Payroll"),
               j.set_fields([(DP, "In progress")]),
               j.comment("Deprovisioning started per the Leaver Deprovisioning Runbook (SECOPS). Badge first, identity second, entitlements third. (JMWE)")]
        def edit(w): j.transition(w, "Start deprovisioning")["actions"] = pfs
        j.write(r, edit, "JMWE A6: seven Create issue post-functions + field + comment on JML: Leaver / Start deprovisioning")
    # A3 Mover revoke before grant (one script: separate post-functions do not see each other's results)
    r = j.read("JML: Mover"); t = j.transition(r["workflows"][0], "Approve")
    if has(t, "A3:"): ctx.say("JMWE A3 (Approve) present")
    else:
        TASK = S["issueTypes"]["Task"]
        script = f"""{{#- Rules learned: "}}}}" ends an expression, so nested objects need "}} }}"; callJira does not work inside macros, so every call is inline. -#}}
{{%- set emp = issue.fields.{EMP} -%}}
{{%- set revoke = ("/rest/api/3/issue" | callJira(verb="POST", body={{"fields": {{"project": {{"key": "ITF"}}, "issuetype": {{"id": "{TASK}"}}, "summary": "REVOKE: Standard Sales Access (Salesforce.com) for " ~ emp, "{LP}": {{"value": "REVOKE"}}, "{TEAM}": {{"value": "IT"}} }} }})).key -%}}
{{%- set _l = "/rest/api/3/issueLink" | callJira(verb="POST", body={{"type": {{"name": "Relates"}}, "inwardIssue": {{"key": revoke}}, "outwardIssue": {{"key": issue.key}} }}) -%}}
{{%- for g in [["ITF", "GRANT: Advanced Support Services (JSM admin) for " ~ emp, "IT"],
              ["ITF", "GRANT: Standard Developer (Jira Align, JSM, Jira Software) for " ~ emp, "IT"],
              ["JML", "Facilities: badge " ~ issue.fields.{BADGE} ~ " zones, add Lab 2A and 24/7 floors", "Facilities"] ] -%}}
{{%- set k = ("/rest/api/3/issue" | callJira(verb="POST", body={{"fields": {{"project": {{"key": g[0]}}, "issuetype": {{"id": "{TASK}"}}, "summary": g[1], "{LP}": {{"value": "GRANT"}}, "{TEAM}": {{"value": g[2]}} }} }})).key -%}}
{{%- set _r = "/rest/api/3/issueLink" | callJira(verb="POST", body={{"type": {{"name": "Relates"}}, "inwardIssue": {{"key": k}}, "outwardIssue": {{"key": issue.key}} }}) -%}}
{{%- set _b = "/rest/api/3/issueLink" | callJira(verb="POST", body={{"type": {{"name": "Blocks"}}, "inwardIssue": {{"key": revoke}}, "outwardIssue": {{"key": k}} }}) -%}}
{{%- endfor -%}}"""
        pfs = [j.script(script, "A3: create REVOKE, then GRANT and Facilities tasks blocked by it, all related to the Mover"),
               j.comment("Access audit complete. REVOKE: Standard Sales Access. GRANT: Advanced Support Services, Standard Developer. RETAINED: Standard Employee (Workday, GSuite, JSM, Loom). Grants are blocked until revokes are done. (JMWE)")]
        def edit(w): j.transition(w, "Approve")["actions"] = pfs
        j.write(r, edit, "JMWE A3: scripted post-function + comment on JML: Mover / Approve")
    # A4 / A8 and the revoke-before-grant guard, on the task Done transitions of JML and ITF
    TAG = "A4/A8: advance the Mover or verify the Leaver when its last REVOKE / DEPROVISION task closes"
    SCRIPT = f"""{{#- Rules: no "}}}}" inside expressions (use "}} }}"); no callJira inside macros. -#}}
{{%- set phase = issue.fields.{LP}.value if issue.fields.{LP} else "" -%}}
{{%- if phase == "REVOKE" or phase == "DEPROVISION" -%}}
{{%- for p in issue.key | issue(["issuelinks"]) | linkedIssues("relates to", ["issuetype", "status"]) -%}}
{{%- set isMover = phase == "REVOKE" and p.fields.issuetype.name == "HR request (with approval)" and p.fields.status.name == "Revoking" -%}}
{{%- set isLeaver = phase == "DEPROVISION" and p.fields.issuetype.name == "Employee offboarding" and p.fields.status.name == "Deprovisioning" -%}}
{{%- if isMover or isLeaver -%}}
{{%- set open = [] -%}}
{{%- for s in p.key | issue(["issuelinks"]) | linkedIssues("relates to", ["status", "{LP}"]) -%}}
{{%- if s.fields.{LP} and s.fields.{LP}.value == phase and s.fields.status.statusCategory.key != "done" and s.key != issue.key -%}}{{% set _o = open.push(s.key) %}}{{%- endif -%}}
{{%- endfor -%}}
{{%- if open.length == 0 -%}}
{{%- set want = "Revokes complete" if isMover else "Verify" -%}}
{{%- set msg = "All revokes done. Access is now clear to grow. GRANT tasks are unblocked. (JMWE)" if isMover else "All deprovisioning tasks done. Run the Deprovisioning agent for the closure report. (JMWE)" -%}}
{{%- set _c = "/rest/api/2/issue/:k/comment" | callJira(verb="POST", params={{"k": p.key}}, body={{"body": msg}}) -%}}
{{%- for tr in ("/rest/api/3/issue/:k/transitions" | callJira(params={{"k": p.key}})).transitions -%}}
{{%- if tr.name == want -%}}{{% set _t = "/rest/api/3/issue/:k/transitions" | callJira(verb="POST", params={{"k": p.key}}, body={{"transition": {{"id": tr.id}} }}) %}}{{%- endif -%}}
{{%- endfor -%}}
{{%- endif -%}}
{{%- endif -%}}
{{%- endfor -%}}
{{%- endif -%}}"""
    MSG = "Revoke before grant: this GRANT task is blocked by a REVOKE task that is not Done yet."
    EXPR = f'issue.{LP}?.value != "GRANT" || issue.links.filter(l => l.type.name == "Blocks" && l.direction == "inward").every(l => l.linkedIssue.status.category.key == "done")'
    V = j.validator("ScriptedValidator", {"errorMessage": MSG, "script": EXPR, "expression": EXPR, "type": "code"})
    for wf in (S["jmlDefaultWorkflow"]["name"], S["itf"]["workflow"]):
        r = j.read(wf); targets = j.transitions_to(r, "Done")
        if not targets: ctx.warn(f"{wf}: no transition into Done; A4/A8 and the guard need one"); continue
        names = [t["name"] for t in targets]
        if all(has(t, TAG) and has(t, MSG, "validators") for t in targets): ctx.say(f"JMWE A4/A8 + guard present on {wf} / {names}"); continue
        def edit(w, names=names):
            for t in w["transitions"]:
                if t["name"] in names:
                    t["actions"] = [a for a in t.get("actions", []) if TAG not in a.get("parameters", {}).get("config", "")] + [j.script(SCRIPT, TAG)]
                    t["validators"] = [v for v in t.get("validators", []) if MSG not in v.get("parameters", {}).get("config", "")] + [V]
        j.write(r, edit, f"JMWE A4/A8 script + revoke-before-grant validator on {wf} / {names}")
    ctx.state.set("jmwe", postFunctions="A1, A3, A4/A8, A6, guard")
