"""Phase 5: Jira Automation rules through the automation gateway API (no public API exists). Which rules are created and which
are enabled depends on the edition. Rules that call the badge console or Assets carry a secure header the person pastes in the UI."""
import uuid
from .editions import SECRET_RULES

SEL = "com.atlassian.jira.plugin.system.customfieldtypes:select"
URLT = "com.atlassian.jira.plugin.system.customfieldtypes:url"
TEXT = "com.atlassian.jira.plugin.system.customfieldtypes:textfield"
CREATED = {"type": "COPY", "value": "created"}; TRIGGER_ISSUE = {"type": "COPY", "value": "trigger"}


class Rules:
    def __init__(self, ctx):
        S = ctx.S; self.ctx = ctx; site = ctx.site
        self.C = site.cloud_id(); self.ED = site.me()["accountId"]; self.TZ = site.me().get("timeZone", "America/New_York")
        self.F, self.IT = S["fields"], S["issueTypes"]; self.JML, self.ITF = str(S["project"]["id"]), str(S["itf"]["id"])
        self.JML_ARI, self.ITF_ARI = f"ari:cloud:jira:{self.C}:project/{self.JML}", f"ari:cloud:jira:{self.C}:project/{self.ITF}"
        self.BASE = site.auto_base(); self.BADGE_URL = ctx.opts["console_url"].rstrip("/") + "/api/badge"; self.CONSOLE = ctx.opts["console_url"].rstrip("/")
        self.LINK_RELATES = f"inward:{S['linkTypes']['Relates']}"; self.LINK_BLOCKED_BY = f"inward:{S['linkTypes']['Blocks']}"
        A = S.get("assets", {}); self.A = A

    # ---- components
    def comp(self, component, typ, value, children=None, conditions=None, schema=1):
        return {"id": str(uuid.uuid4()), "parentId": None, "conditionParentId": None, "component": component, "type": typ, "value": value,
                "children": children or [], "conditions": conditions or [], "schemaVersion": schema}
    def trig_transition(self, to_status, both=False):
        return self.comp("TRIGGER", "jira.issue.event.trigger:transitioned", {"eventFilters": [self.JML_ARI, self.ITF_ARI] if both else [self.JML_ARI], "fromStatus": [],
                         "toStatus": [{"type": "NAME", "value": to_status}], "eventKey": "jira:issue_updated", "issueEvent": "issue_generic"})
    def trig_comment(self): return self.comp("TRIGGER", "jira.issue.event.trigger:commented", {"eventTypes": [], "eventFilters": [self.JML_ARI]})
    def trig_created(self): return self.comp("TRIGGER", "jira.issue.event.trigger:created", {"eventFilters": [self.JML_ARI, self.ITF_ARI], "eventKey": "jira:issue_created", "issueEvent": "issue_created"})
    def trig_webhook(self): return self.comp("TRIGGER", "jira.incoming.webhook", {"webhookToken": None, "searchOrProvide": "provide", "jql": None})
    def trig_sched(self, jql):
        return self.comp("TRIGGER", "jira.jql.scheduled", {"schedule": {"cronExpression": "", "method": "BASIC", "rate": 0, "rateInterval": 86400,
                         "rRule": f"BEGIN:VEVENT\nDTSTART;TZID={self.TZ}:20261023T070000\nRRULE:FREQ=DAILY;BYHOUR=7;BYMINUTE=0;BYSECOND=0;INTERVAL=1\nEND:VEVENT\n"},
                         "jql": jql, "executionMode": "jql", "onlyUpdatedIssues": False})
    def cond_issuetype(self, itid): return self.comp("CONDITION", "jira.issue.condition", {"selectedField": {"type": "ID", "value": "issuetype"}, "selectedFieldType": "issuetype",
        "comparison": "EQUALS", "compareValue": {"type": "ID", "modifier": None, "value": str(itid), "multiValue": False, "source": None}}, schema=3)
    def cond_status(self, name): return self.comp("CONDITION", "jira.issue.condition", {"selectedField": {"type": "ID", "value": "status"}, "selectedFieldType": "status",
        "comparison": "EQUALS", "compareValue": {"type": "NAME", "modifier": None, "value": name, "multiValue": False, "source": None}}, schema=3)
    def cond_select(self, fid, option): return self.comp("CONDITION", "jira.issue.condition", {"selectedField": {"type": "ID", "value": fid}, "selectedFieldType": SEL,
        "comparison": "EQUALS", "compareValue": {"type": "NAME", "modifier": None, "value": option, "multiValue": False, "source": None}}, schema=3)
    def cond_notempty(self, fid, ftype): return self.comp("CONDITION", "jira.issue.condition", {"selectedField": {"type": "ID", "value": fid}, "selectedFieldType": ftype, "comparison": "NOT_EMPTY", "compareValue": None}, schema=3)
    def cond_cmp(self, first, second, op): return self.comp("CONDITION", "jira.comparator.condition", {"first": first, "second": second, "operator": op})
    def cond_related_all(self, link, jql): return self.comp("CONDITION", "jira.issues.related.condition",
        {"relatedType": "linked", "linkTypes": [link], "operator": "allmatch", "relatedJql": "", "compareJql": jql, "compareValue": 0, "similarityLimit": 40, "jql": ""})
    def op_set(self, fid, ftype, value): return {"field": {"type": "ID", "value": fid}, "fieldType": ftype, "type": "SET", "value": value}
    def act_create(self, summary, team, phase, project="JML", description=None, assignee_smart=None, evidence=None):
        F = self.F; pid = self.ITF if project == "ITF" else self.JML
        ops = [self.op_set("project", "project", {"type": "ID", "value": pid}), self.op_set("issuetype", "issuetype", {"type": "ID", "value": str(self.IT["Task"])}),
               self.op_set("summary", "summary", summary), self.op_set(F["Lifecycle phase"], SEL, {"type": "NAME", "value": phase}), self.op_set(F["Fan-out team"], SEL, {"type": "NAME", "value": team})]
        if description: ops.append(self.op_set("description", "description", description))
        if assignee_smart: ops.append(self.op_set("assignee", "assignee", {"type": "SMART", "value": assignee_smart}))
        if evidence: ops.append(self.op_set(F["Evidence"], URLT, evidence))
        return self.comp("ACTION", "jira.issue.create", {"operations": ops, "advancedFields": None, "sendNotifications": True}, schema=12)
    def act_link(self, link_type, target): return self.comp("ACTION", "jira.issue.link", {"linkType": link_type, "issue": target}, schema=2)
    def smart_issue(self, sv): return {"type": "SMART", "value": sv}
    def act_comment(self, text): return self.comp("ACTION", "jira.issue.comment", {"comment": text, "publicComment": False, "commentVisibility": None, "sendNotifications": True, "addCommentOnce": False}, schema=2)
    def act_transition(self, status): return self.comp("ACTION", "jira.issue.transition", {"operations": [], "advancedFields": None, "sendNotifications": True, "destinationStatus": {"type": "NAME", "value": status}, "transitionMatch": ""}, schema=11)
    def act_edit(self, ops): return self.comp("ACTION", "jira.issue.edit", {"operations": ops, "advancedFields": None, "sendNotifications": True}, schema=12)
    def act_var(self, name, sv): return self.comp("ACTION", "jira.create.variable", {"id": "_customsmartvalue_id_" + uuid.uuid4().hex[:12], "name": {"type": "FREE", "value": name}, "type": "SMART", "query": {"type": "SMART", "value": sv}, "lazy": False})
    def act_webhook(self, body, url=None, method="POST", secret_header="X-JML-Secret", continue_on_error=False):
        return self.comp("ACTION", "jira.issue.outgoing.webhook", {"url": url or self.BADGE_URL, "urlSecure": False,
            "headers": [{"id": "_header_" + uuid.uuid4().hex[:10], "name": "Content-Type", "value": "application/json", "headerSecure": False},
                        {"id": "_header_" + uuid.uuid4().hex[:10], "name": secret_header, "value": "", "headerSecure": True}],
            "sendIssue": False, "contentType": "custom", "customBody": body, "method": method, "responseEnabled": True, "continueOnErrorEnabled": continue_on_error})
    def act_wait(self, sec=8): return self.comp("ACTION", "action.wait.for.time.duration", {"waitTimeInSeconds": sec, "randomWaitInterval": None})
    def act_delete(self): return self.comp("ACTION", "jira.issue.delete", None)
    def act_lookup(self, schema_id, schema_label, aql):
        return self.comp("ACTION", "cmdb.lookup.objects", {"workspaceId": self.A["workspaceId"], "schemaId": str(schema_id), "schemaLabel": schema_label,
            "customSmartValue": {"id": "_customsmartvalue_id_" + uuid.uuid4().hex[:12], "name": {"type": "FREE", "value": "lookupObjects"}, "type": "IQL", "query": {"type": "SMART", "value": aql}, "lazy": False}, "searchResultsLimit": 1})
    def branch_linked(self, link, children): return self.comp("BRANCH", "jira.issue.related", {"relatedType": "linked", "jql": "", "linkTypes": [link], "onlyUpdatedIssues": False, "similarityLimit": 40, "compareValue": 0}, children=children)
    def branch_created(self, children): return self.comp("BRANCH", "jira.issue.related", {"relatedType": "recentlycreated", "jql": "", "linkTypes": [], "onlyUpdatedIssues": False, "similarityLimit": 40, "compareValue": 0}, children=children)
    def branch_jql(self, jql, children): return self.comp("BRANCH", "jira.issue.related", {"relatedType": "jql", "jql": jql, "linkTypes": [], "onlyUpdatedIssues": False, "similarityLimit": 40, "compareValue": 0}, children=children)
    def rule(self, name, trigger, components, allow_trigger=False, description="", both=False):
        return {"name": name, "state": "DISABLED", "description": description, "authorAccountId": self.ED, "actor": {"type": "ACCOUNT_ID", "value": self.ED},
                "trigger": trigger, "components": components, "canOtherRuleTrigger": allow_trigger, "notifyOnError": "FIRSTERROR", "projects": [], "labels": [],
                "ruleScope": {"resources": [self.JML_ARI, self.ITF_ARI] if both else [self.JML_ARI]}, "writeAccessType": "UNRESTRICTED", "readAccessType": "UNRESTRICTED", "collaborators": []}

    # ---- the rules
    def build(self):
        F, IT = self.F, self.IT; TASK, ONB, OFF, MOV = IT["Task"], IT["Employee onboarding"], IT["Employee offboarding"], IT["HR request (with approval)"]
        c, R = self, {}
        R["A1 Joiner fan-out"] = c.rule("A1 Joiner fan-out", c.trig_transition("Pre-Day-One"), [c.cond_issuetype(ONB),
            c.act_create("IT: provision {{issue.Role}} entitlements for {{issue.Employee ID}}", "IT", "PRE-DAY-ONE", "ITF", "Provision from Role Profile {{issue.Role}}. Policies and applications are on the Role object in Assets and the Confluence page labeled role-profile. Attach evidence per application."), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("Facilities: issue badge {{issue.Badge number}} and assign desk", "Facilities", "PRE-DAY-ONE", "JML", "Badge zones per Role Profile. Do not issue before Legal confirms signed agreements."), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("Legal: confirm signed agreements for {{issue.Employee ID}}", "Legal", "PRE-DAY-ONE"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("Payroll: set up {{issue.Employee ID}} in Workday, start {{issue.Start date}}", "Payroll", "PRE-DAY-ONE"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("Manager: orientation plan and required training for {{issue.Employee ID}}", "Manager", "PRE-DAY-ONE", assignee_smart="{{issue.Manager.first.accountId}}"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_comment("Fan-out created: IT, Facilities, Legal, Payroll, Manager. Badge {{issue.Badge number}} activates on {{issue.Start date}} once Legal and Facilities tasks are done.")])
        R["A2 Joiner day one"] = c.rule("A2 Joiner day one", c.trig_transition("Done", both=True), [c.cond_issuetype(TASK), c.cond_select(F["Lifecycle phase"], "PRE-DAY-ONE"),
            c.branch_linked("relates to", [c.act_wait(), c.cond_issuetype(ONB), c.cond_status("Pre-Day-One"), c.cond_related_all("relates to", "statusCategory = Done"),
                c.act_webhook('{"badge_number":"{{issue.Badge number}}","action":"activate","reference":"{{issue.key}}","source":"Jira Automation (Joiner day one)"}'),
                c.act_transition("Day One"), c.act_comment("Day one for {{issue.Start date}}. Badge {{issue.Badge number}} activated. SENTRIA confirmation {{webResponse.body.confirmation}}.")])], allow_trigger=True, both=True)
        R["A3 Mover revoke before grant"] = c.rule("A3 Mover revoke before grant", c.trig_transition("Revoking"), [c.cond_issuetype(MOV),
            c.act_create("REVOKE: Standard Sales Access (Salesforce.com) for {{issue.Employee ID}}", "IT", "REVOKE", "ITF"), c.act_link(c.LINK_RELATES, CREATED), c.act_var("revokeKey", "{{createdIssue.key}}"),
            c.act_create("GRANT: Advanced Support Services (JSM admin) for {{issue.Employee ID}}", "IT", "GRANT", "ITF"), c.branch_created([c.act_link(c.LINK_BLOCKED_BY, c.smart_issue("{{revokeKey}}")), c.act_link(c.LINK_RELATES, TRIGGER_ISSUE)]),
            c.act_create("GRANT: Standard Developer (Jira Align, JSM, Jira Software) for {{issue.Employee ID}}", "IT", "GRANT", "ITF"), c.branch_created([c.act_link(c.LINK_BLOCKED_BY, c.smart_issue("{{revokeKey}}")), c.act_link(c.LINK_RELATES, TRIGGER_ISSUE)]),
            c.act_create("Facilities: badge {{issue.Badge number}} zones, add Lab 2A and 24/7 floors", "Facilities", "GRANT"), c.branch_created([c.act_link(c.LINK_BLOCKED_BY, c.smart_issue("{{revokeKey}}")), c.act_link(c.LINK_RELATES, TRIGGER_ISSUE)]),
            c.act_comment("Access audit complete. REVOKE: Standard Sales Access. GRANT: Advanced Support Services, Standard Developer. RETAINED: Standard Employee (Workday, GSuite, JSM, Loom). Grants are blocked until revokes are done.")], allow_trigger=True)
        R["A4 Mover advances"] = c.rule("A4 Mover advances", c.trig_transition("Done", both=True), [c.cond_issuetype(TASK), c.cond_select(F["Lifecycle phase"], "REVOKE"),
            c.branch_linked("relates to", [c.act_wait(), c.cond_issuetype(MOV), c.cond_status("Revoking"), c.cond_related_all("relates to", '"Lifecycle phase" != "REVOKE" OR "Lifecycle phase" is EMPTY OR status = Done'),
                c.act_transition("Granting"), c.act_comment("All revokes done. Access is now clear to grow. GRANT tasks are unblocked.")])], allow_trigger=True, both=True)
        R["A5 Leaver countdown"] = c.rule("A5 Leaver countdown", c.trig_sched('project = JML AND type = "Employee offboarding" AND status in (Open, "Knowledge Audit") AND ("Last day" = startOfDay("+21d") OR "Last day" = startOfDay("+7d"))'),
            [c.act_comment("{{issue.Manager}} The last day on record is {{issue.Last day}}. Reply confirmed if that is still correct, or give the new date. Deprovisioning will not run without confirmation."), c.act_transition("Awaiting Manager Confirmation")])
        R["A5b Manager confirmation received"] = c.rule("A5b Manager confirmation received", c.trig_comment(), [c.cond_issuetype(OFF), c.cond_status("Awaiting Manager Confirmation"), c.cond_cmp("{{comment.body}}", "confirmed", "CONTAINS"),
            c.act_transition("Knowledge Audit"), c.act_edit([c.op_set(F["Knowledge audit status"], SEL, {"type": "NAME", "value": "In progress"})]),
            c.act_comment("Confirmed by {{comment.author.displayName}}. Knowledge Audit agent is inventorying owned pages, runbooks, and work items.")])
        R["A6 Leaver fan-out"] = c.rule("A6 Leaver fan-out", c.trig_transition("Deprovisioning"), [c.cond_issuetype(OFF),
            c.act_create("Security: revoke all badge zones for {{issue.Badge number}}, verify none remain including decommissioned zones", "Security", "DEPROVISION", "ITF"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("IT: disable identity for {{issue.Employee ID}}: SSO, MFA, directory set to Departed", "IT", "DEPROVISION", "ITF"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("IT: remove entitlements for {{issue.Employee ID}}: every Access Policy on the Role plus any Approved Access drift", "IT", "DEPROVISION", "ITF"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("Successor: transfer Confluence ownership from {{issue.Employee ID}} (label owner-{{issue.Employee ID}})", "Manager", "DEPROVISION"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("Manager: reassign open Jira work items and automation rules owned by {{issue.Employee ID}}", "Manager", "DEPROVISION"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("Facilities: collect laptop, phone, badge, keys; mark hardware Returned", "Facilities", "DEPROVISION"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_create("Payroll and Legal: final pay, benefits, exit documents", "Payroll", "DEPROVISION"), c.act_link(c.LINK_RELATES, CREATED),
            c.act_edit([c.op_set(F["Deprovisioning status"], SEL, {"type": "NAME", "value": "In progress"})]),
            c.act_comment("Deprovisioning started per the Leaver Deprovisioning Runbook (SECOPS). Badge first, identity second, entitlements third.")], allow_trigger=True)
        R["A7 Badge deactivation"] = c.rule("A7 Badge deactivation", c.trig_transition("Deprovisioning"), [c.cond_issuetype(OFF), c.cond_notempty(F["Badge number"], TEXT),
            c.act_webhook('{"badge_number":"{{issue.Badge number}}","action":"deactivate","reference":"{{issue.key}}","source":"Jira Automation (Badge deactivation)"}'),
            c.act_comment("SENTRIA: badge {{issue.Badge number}} set to INACTIVE. Confirmation {{webResponse.body.confirmation}}. Door controller updated."),
            c.act_create("Security: confirm badge {{issue.Badge number}} INACTIVE in SENTRIA", "Security", "DEPROVISION", "ITF", evidence=c.CONSOLE), c.act_link(c.LINK_RELATES, CREATED),
            c.branch_created([c.act_transition("Done")])], allow_trigger=True)
        R["A8 Leaver verified"] = c.rule("A8 Leaver verified", c.trig_transition("Done", both=True), [c.cond_issuetype(TASK), c.cond_select(F["Lifecycle phase"], "DEPROVISION"),
            c.branch_linked("relates to", [c.act_wait(), c.cond_issuetype(OFF), c.cond_status("Deprovisioning"), c.cond_related_all("relates to", '"Lifecycle phase" != "DEPROVISION" OR "Lifecycle phase" is EMPTY OR status = Done'),
                c.act_comment("All deprovisioning tasks done. Run the Deprovisioning agent for the closure report."), c.act_transition("Verified")])], allow_trigger=True, both=True)
        R["A9 SLA breach escalation"] = c.rule("A9 SLA breach escalation", c.trig_webhook(), [
            c.act_edit([{"field": {"type": "ID", "value": "labels"}, "fieldType": "labels", "type": "ADD", "value": [{"type": "FREE", "value": "sla-breach-flagged"}]}]),
            c.branch_linked("relates to", [c.cond_issuetype(OFF), c.act_comment("SLA breached on {{triggerIssue.summary}}, owner {{triggerIssue.Fan-out team}}"),
                c.act_edit([c.op_set(F["Deprovisioning status"], SEL, {"type": "NAME", "value": "Findings open"})])])],
            description="Called by the Time to SLA 'Trigger Jira automation' action on each SLA (is breached). Labels the task, then flags the linked Leaver.", both=True)
        R["A10 Link agent tasks"] = c.rule("A10 Link agent tasks", c.trig_created(), [c.cond_cmp("{{issue.summary}}", "(Handover:|STILL RUNNING:).*", "REGEX_MATCHES"),
            c.act_var("empId", '{{issue.summary.match(".*(?:from|for) ([A-Za-z0-9._-]+).*")}}'),
            c.branch_jql('project = JML AND type = "Employee offboarding" AND text ~ "{{empId}}" AND statusCategory != Done', [c.act_link(c.LINK_RELATES, TRIGGER_ISSUE)])],
            description="Links Handover and STILL RUNNING tasks created by Rovo agents to the open Leaver whose Employee ID is in the summary. Rovo has no Jira link tool.", both=True)
        R["Demo reset"] = c.rule("Demo reset", c.trig_comment(), [c.cond_issuetype(OFF), c.cond_cmp("{{comment.body}}", "#reset", "CONTAINS"),
            c.act_webhook('{"badge_number":"{{issue.Badge number}}","action":"activate","reference":"Demo reset","source":"Demo reset"}'),
            c.branch_jql('type = Task AND "Lifecycle phase" in ("DEPROVISION", "REVOKE", "GRANT", "PRE-DAY-ONE", "STILL-RUNNING") AND issue in linkedIssues("{{issue.key}}")', [c.act_delete()]),
            c.act_edit([c.op_set(F["Deprovisioning status"], SEL, {"type": "NAME", "value": "Not started"}), c.op_set(F["Knowledge audit status"], SEL, {"type": "NAME", "value": "Not started"})]),
            c.act_comment("Demo reset complete. Badge {{issue.Badge number}} reactivated (confirmation {{webResponse.body.confirmation}}) and fan-out tasks removed.")], both=True)
        R["Demo: teams done"] = self.teams_done()
        return R

    def teams_done(self):
        c, F, A = self, self.F, self.A
        if not A.get("objectTypes") or not A.get("attrs"): return None
        ws = A["workspaceId"]; ASSETS = f"https://api.atlassian.com/jsm/assets/workspace/{ws}/v1/object/{{{{lookupObjects.id}}}}"
        at = A["attrs"]; OT = A["objectTypes"]; SCH = A["schemas"]
        def close_with(comment): return [c.act_edit([c.op_set(F["Evidence"], URLT, c.CONSOLE)]), c.act_comment("Evidence: " + comment), c.act_transition("Done")]
        def assets_put(body):
            import json
            return c.act_webhook(json.dumps(body), url=ASSETS, method="PUT", secret_header="Authorization", continue_on_error=True)
        LINKED = 'issue in linkedIssues("{{issue.key}}", "relates to") AND statusCategory != Done AND summary !~ "\\"STILL RUNNING\\""'
        return c.rule("Demo: teams done", c.trig_comment(), [c.cond_issuetype(self.IT["Employee offboarding"]), c.cond_cmp("{{comment.body}}", "#teams-done", "CONTAINS"),
            c.branch_jql(LINKED + ' AND summary ~ "\\"remove entitlements\\""', close_with(
                "Removed every Access Policy on the {{triggerIssue.Role}} role and any Approved Access drift: Standard Employee (Workday, GSuite, JSM, Loom), People Manager (Workday), Advanced Support Services (JSM admin). Approved Access cleared in Assets.")),
            c.branch_jql(LINKED + ' AND summary !~ "\\"remove entitlements\\"" AND summary !~ "\\"revoke all badge zones\\""', close_with(
                "{{issue.summary}}: completed per the Leaver Deprovisioning Runbook. Change ref CHG-{{now.format(\"MMddHHmm\")}}.")),
            c.act_lookup(SCH["Facilities"], "Facilities", f'objectTypeId = {OT["Badge"]} AND "Badge Number" = "{{{{issue.{F["Badge number"]}}}}}"'),
            assets_put({"attributes": [{"objectTypeAttributeId": at["Badge:Status"], "objectAttributeValues": [{"value": "INACTIVE"}]},
                                       {"objectTypeAttributeId": at["Badge:Deactivation Ref"], "objectAttributeValues": [{"value": "{{issue.key}}"}]},
                                       {"objectTypeAttributeId": at["Badge:Zones"], "objectAttributeValues": [{"value": "Legacy data center [DECOMMISSIONED]"}]}]}),
            c.act_lookup(SCH["People"], "People", f'objectTypeId = {OT["People"]} AND "Employee ID" = "{{{{issue.{F["Employee ID"]}}}}}"'),
            assets_put({"attributes": [{"objectTypeAttributeId": at["People:Approved Access"], "objectAttributeValues": []}]}),
            c.act_comment("Team updates received: identity, entitlements, ownership, hardware and payroll tasks closed with evidence. Badge {{issue.Badge number}} INACTIVE in Assets.")],
            description="Demo helper. Comment #teams-done on a Leaver after Start deprovisioning: closes the team tasks with evidence (not the Security badge-zones task) and updates Assets. Needs the Assets credential pasted into both Authorization headers.", both=True)


def run(ctx):
    S, site, ed = ctx.S, ctx.site, ctx.edition
    if not (S.get("project") and S.get("itf") and S.get("fields") and S.get("linkTypes")): ctx.plan("create the Automation rules (after projects, fields and link types exist)"); return
    rb = Rules(ctx); R = rb.build(); BASE, JML = rb.BASE, rb.JML
    s, lst = site.post(f"{BASE}/{JML}/rules", {"offset": 0, "limit": 200}); ctx.need(s == 200, f"cannot list Automation rules: {s} {str(lst)[:200]}")
    existing = {v["name"]: v for v in lst.get("values", [])}
    ids = ctx.state.sec("automationRules")
    for name in ed["automation"]:
        body = R.get(name)
        if body is None: ctx.plan(f"create rule {name} (after the Assets ids are known)"); continue
        if name in existing:
            v = existing[name]; ids[name] = v["id"]; ctx.say(f"rule {name} exists ({v.get('state')})")
        else:
            res = ctx.do(f"create rule {name}" + (" (DISABLED: paste the secret, then enable)" if name in SECRET_RULES else ""), site.post, f"{BASE}/{JML}/rule", {"ruleConfigBean": body})
            if not res: continue
            s, x = res; ctx.need(s in (200, 201), f"rule {name}: {s} {str(x)[:600]}"); ids[name] = x["ruleConfigBean"]["id"]; existing[name] = {"id": ids[name], "state": "DISABLED"}
        want_on = name not in SECRET_RULES and name not in ed["automation_fallback"]
        if want_on and existing[name].get("state") != "ENABLED":
            set_state(ctx, ids[name], "ENABLED", name)
    ctx.state.save()
    secrets = [n for n in ed["automation"] if n in SECRET_RULES]
    ctx.note("automation", "secrets", secrets)
    if "A9 SLA breach escalation" in ed["automation"]: ctx.note("automation", "a9", ids.get("A9 SLA breach escalation"))


def set_state(ctx, rule_id, state, name=""):
    site = ctx.site; BASE = site.auto_base()
    s, x = site.get(f"{BASE}/GLOBAL/rule/{rule_id}")
    if s != 200: ctx.warn(f"cannot read rule {name} {rule_id}: {s}"); return
    res = ctx.do(f"{state.lower()} rule {name}", site.patch, f"{BASE}/GLOBAL/rule/{x['idUuid']}", [{"op": "replace", "path": "/state", "value": state}])
    if res and res[0] != 200: ctx.warn(f"{state} {name}: {res[0]} {str(res[1])[:200]}")
