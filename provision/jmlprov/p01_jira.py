"""Phase 1: the two projects, statuses, the three lifecycle workflows, the workflow scheme, custom fields, screens, link types."""
import uuid, urllib.parse
from .api import ProvisionError

HR_TEMPLATE = "com.atlassian.servicedesk:simplified-hr-service-desk"
KANBAN_TEMPLATE = "com.pyxis.greenhopper.jira:gh-simplified-kanban-classic"
LIFECYCLE_TYPES = ["Employee onboarding", "HR request (with approval)", "Employee offboarding"]
NEEDED_TYPES = LIFECYCLE_TYPES + ["Task"]

STATUSES = [("Open", "TODO"), ("Pre-Day-One", "IN_PROGRESS"), ("Day One", "IN_PROGRESS"), ("Awaiting approval", "IN_PROGRESS"),
            ("Revoking", "IN_PROGRESS"), ("Granting", "IN_PROGRESS"), ("Declined", "DONE"), ("Awaiting Manager Confirmation", "IN_PROGRESS"),
            ("Knowledge Audit", "IN_PROGRESS"), ("Deprovisioning", "IN_PROGRESS"), ("Verified", "IN_PROGRESS"), ("Closed", "DONE"), ("Canceled", "DONE")]

WORKFLOWS = {
 "JML: Joiner": [("Create", None, "Open"), ("Fan out", ["Open"], "Pre-Day-One"), ("Day one", ["Pre-Day-One"], "Day One"),
                 ("Training confirmed", ["Day One"], "Closed"), ("Cancel", ["Open", "Pre-Day-One"], "Canceled")],
 "JML: Mover": [("Create", None, "Open"), ("Submit for approval", ["Open"], "Awaiting approval"), ("Approve", ["Awaiting approval"], "Revoking"),
                ("Decline", ["Awaiting approval"], "Declined"), ("Revokes complete", ["Revoking"], "Granting"), ("Grants complete", ["Granting"], "Closed"),
                ("Reopen", ["Closed", "Declined"], "Open")],
 "JML: Leaver": [("Create", None, "Open"), ("Request confirmation", ["Open", "Knowledge Audit"], "Awaiting Manager Confirmation"),
                 ("Manager confirmed", ["Open", "Awaiting Manager Confirmation"], "Knowledge Audit"),
                 ("Start deprovisioning", ["Open", "Awaiting Manager Confirmation", "Knowledge Audit"], "Deprovisioning"),
                 ("Verify", ["Deprovisioning"], "Verified"), ("Findings open", ["Verified"], "Deprovisioning"), ("Close", ["Verified"], "Closed"),
                 ("Cancel", ["Open", "Awaiting Manager Confirmation", "Knowledge Audit"], "Canceled")],
}
WF_DESC = {"JML: Joiner": "Northwind Labs Joiner lifecycle: Open, Pre-Day-One, Day One, Closed, Canceled.",
           "JML: Mover": "Northwind Labs Mover lifecycle: access shrinks before it grows. Open, Awaiting approval, Revoking, Granting, Closed, Declined.",
           "JML: Leaver": "Northwind Labs Leaver lifecycle: Open, Awaiting Manager Confirmation, Knowledge Audit, Deprovisioning, Verified, Closed, Canceled."}
WF_FOR_TYPE = {"Employee onboarding": "JML: Joiner", "HR request (with approval)": "JML: Mover", "Employee offboarding": "JML: Leaver"}
# template status name -> new status, when the HR template workflows are remapped (fallback: same name, then by category)
REMAP = {"Employee onboarding": {"To Do": "Open", "Work in progress": "Pre-Day-One", "Escalated": "Pre-Day-One", "New Employee Commenced": "Day One",
                                 "Onboarding Completed": "Closed", "Done": "Closed", "In Review": "Open", "Canceled": "Canceled"},
         "HR request (with approval)": {"To Do": "Open", "Waiting for approval": "Awaiting approval", "Escalated": "Awaiting approval", "In Review": "Awaiting approval",
                                        "Approved": "Revoking", "Done": "Closed", "Declined": "Declined", "Canceled": "Declined"},
         "Employee offboarding": {"To Do": "Open", "Waiting for approval": "Awaiting Manager Confirmation", "In Review": "Awaiting Manager Confirmation",
                                  "In Progress": "Knowledge Audit", "Done": "Closed", "Declined": "Canceled", "Canceled": "Canceled"}}

T = "com.atlassian.jira.plugin.system.customfieldtypes:"
SEARCH = {T + "textfield": T + "textsearcher", T + "select": T + "multiselectsearcher", T + "datepicker": T + "daterange", T + "url": T + "exacttextsearcher",
          T + "multicheckboxes": T + "multiselectsearcher", T + "multiuserpicker": T + "userpickergroupsearcher",
          "com.atlassian.jira.plugins.cmdb:cmdb-object-cftype": "com.atlassian.jira.plugins.cmdb:cmdb-object-searcher"}
J, M, L, K = "Employee onboarding", "HR request (with approval)", "Employee offboarding", "Task"
# name, type, options, screens (JML issue types; "ITF" = the IT Fulfilment default screen), reuse an existing field of that name
FIELDS = [
 ("Badge number", T + "textfield", None, [J, M, L], False),
 ("Last day", T + "datepicker", None, [L], False),
 ("Effective date", T + "datepicker", None, [M], False),
 ("Lifecycle phase", T + "select", ["PRE-DAY-ONE", "REVOKE", "GRANT", "DEPROVISION", "STILL-RUNNING"], [K, "ITF"], False),
 ("Fan-out team", T + "select", ["IT", "Facilities", "Legal", "Payroll", "Security", "Recruiting", "Manager"], [K, "ITF"], False),
 ("Evidence", T + "url", None, [K, "ITF"], False),
 ("Immediate termination", T + "multicheckboxes", ["Yes"], [L], False),
 ("Knowledge audit status", T + "select", ["Not started", "In progress", "Complete"], [L], False),
 ("Deprovisioning status", T + "select", ["Not started", "In progress", "Verified", "Findings open"], [L], False),
 ("JML Employee", "com.atlassian.jira.plugins.cmdb:cmdb-object-cftype", None, [J, M, L], False),
 ("JML Badge", "com.atlassian.jira.plugins.cmdb:cmdb-object-cftype", None, [J, L], False),
 ("Target Role", "com.atlassian.jira.plugins.cmdb:cmdb-object-cftype", None, [M], False),
 ("Start date", T + "datepicker", None, [J], True),
 ("Manager", T + "multiuserpicker", None, [J, M, L], True),
 ("Employee ID", T + "textfield", None, [J, M, L], True),
 ("Role", T + "textfield", None, [J, M, L], True),
 ("Department", T + "select", None, [J, M, L], True),
]


def run(ctx):
    site, S = ctx.site, ctx.S
    ensure_projects(ctx)
    ensure_statuses(ctx)
    ensure_workflows(ctx)
    map_scheme(ctx)
    ensure_fields(ctx)
    ensure_screens(ctx)
    s, lt = site.get("/rest/api/3/issueLinkType")
    links = {x["name"]: x["id"] for x in lt.get("issueLinkTypes", [])}
    ctx.need("Relates" in links and "Blocks" in links, "link types Relates and Blocks must exist")
    ctx.state.set("linkTypes", Relates=links["Relates"], Blocks=links["Blocks"]); ctx.say(f"link types: Relates {links['Relates']}, Blocks {links['Blocks']}")


def _project(ctx, key, name, template, type_key):
    site = ctx.site
    s, p = site.get(f"/rest/api/3/project/{key}")
    if s == 200:
        ctx.say(f"project {key} ({p['name']}) exists, id {p['id']}"); return p
    body = {"key": key, "name": name, "projectTypeKey": type_key, "projectTemplateKey": template, "leadAccountId": site.me()["accountId"], "assigneeType": "UNASSIGNED"}
    r = ctx.do(f"create project {key} {name} from template {template}", site.post, "/rest/api/3/project", body)
    if r is None: return None
    s, x = r
    ctx.need(s in (200, 201), f"project {key}: {s} {str(x)[:300]}")
    s, p = site.get(f"/rest/api/3/project/{key}"); return p


def ensure_projects(ctx):
    site = ctx.site
    p = _project(ctx, "JML", "People Operations", HR_TEMPLATE, "service_desk")
    if p:
        types = {t["name"]: t["id"] for t in p.get("issueTypes", [])}
        missing = [t for t in NEEDED_TYPES if t not in types]
        ctx.need(not missing, f"JML is missing work types {missing}: the HR service management template should provide them (rename yours to these names)")
        s, sd = site.get("/rest/api/3/project/JML"); sdid = None
        s, r = site.get("/rest/servicedeskapi/servicedesk?projectKey=JML")
        if s == 200: sdid = next((x["id"] for x in r.get("values", []) if x.get("projectKey") == "JML"), None)
        ctx.state.set("project", id=int(p["id"]), key="JML", name=p["name"], serviceDeskId=sdid)
        ctx.state.set("issueTypes", **{k: int(v) for k, v in types.items()})
    p2 = _project(ctx, "ITF", "IT Fulfilment", KANBAN_TEMPLATE, "software")
    if p2:
        types = {t["name"]: t["id"] for t in p2.get("issueTypes", [])}
        ctx.need("Task" in types, "ITF has no Task work type")
        s, ws = site.post("/rest/api/3/workflowscheme/read", {"projectIds": [str(p2["id"])]})
        wf = ws[0]["defaultWorkflow"]["name"] if s == 200 else None
        for m in (ws[0]["workflowsForIssueTypes"] if s == 200 else []):
            if str(types["Task"]) in m["issueTypeIds"]: wf = m["workflow"]["name"]
        s, st = site.get(f"/rest/api/3/statuses/search?projectId={p2['id']}&searchString=Done&maxResults=50")
        done = next((x for x in st.get("values", []) if x["name"] == "Done"), None)
        ctx.need(done, "ITF workflow has no status named Done (A4/A8 and the Time to SLA stop rule need it)")
        ctx.state.set("itf", id=int(p2["id"]), key="ITF", issueTypes={k: int(v) for k, v in types.items()}, workflow=wf, doneStatusId=done["id"])
        ctx.say(f"ITF workflow: {wf}, Done status {done['id']}")


def _global_status(site, name):
    s, r = site.get(f"/rest/api/3/statuses/search?searchString={urllib.parse.quote(name)}&maxResults=200")
    for x in r.get("values", []) if s == 200 else []:
        if x["name"].lower() == name.lower() and x.get("scope", {}).get("type", "GLOBAL") == "GLOBAL": return x
    return None


def ensure_statuses(ctx):
    site = ctx.site; ids = ctx.state.sec("statuses")
    missing = []
    for name, cat in STATUSES:
        x = _global_status(site, name)
        if x: ids[name] = x["id"]
        else: missing.append({"name": name, "statusCategory": cat, "description": "JML demo"})
    if missing:
        r = ctx.do(f"create global statuses {[m['name'] for m in missing]}", site.post, "/rest/api/3/statuses", {"scope": {"type": "GLOBAL"}, "statuses": missing})
        if r:
            s, x = r; ctx.need(s == 200, f"statuses: {s} {str(x)[:300]}")
            for st in x: ids[st["name"]] = st["id"]
    ctx.state.save(); ctx.say(f"statuses: {len(ids)} known" + (f", {len(missing)} to create" if missing and not ctx.apply else ""))


def _read_workflow(site, name, expand=False):
    s, r = site.post("/rest/api/3/workflows" + ("?expand=values.transitions" if expand else ""), {"workflowNames": [name]})
    return r if s == 200 and r.get("workflows") else None


def ensure_workflows(ctx):
    site, ST = ctx.site, ctx.state.sec("statuses"); out = ctx.state.sec("workflows")
    cat = {n: c for n, c in STATUSES}
    for name, trans in WORKFLOWS.items():
        r = _read_workflow(site, name)
        if r:
            w = r["workflows"][0]; out[name] = {"id": w["id"], "version": w.get("version")}; ctx.say(f"workflow {name} exists"); continue
        if any(n not in ST for _, f, t in trans for n in (f or []) + [t]):
            ctx.plan(f"create workflow {name} (after the statuses exist)"); continue
        used = []
        for _, frm, to in trans:
            for n in (frm or []) + [to]:
                if n not in used: used.append(n)
        ref = {n: str(uuid.uuid4()) for n in used}
        statuses = [{"id": str(ST[n]), "name": n, "statusCategory": cat[n], "statusReference": ref[n]} for n in used]
        wstatuses = [{"statusReference": ref[n], "layout": {"x": 200 * i, "y": 0}} for i, n in enumerate(used)]
        transitions = []
        for i, (tn, frm, to) in enumerate(trans):
            t = {"id": str(i + 1), "name": tn, "type": "INITIAL" if frm is None else "DIRECTED", "toStatusReference": ref[to],
                 "links": [{"fromStatusReference": ref[f], "fromPort": 0, "toPort": 1} for f in (frm or [])], "actions": [], "validators": [], "triggers": []}
            if frm is not None: t["conditions"] = {"operation": "ALL", "conditions": []}
            transitions.append(t)
        wf = {"name": name, "description": WF_DESC[name], "statuses": wstatuses, "transitions": transitions, "startPointLayout": {"x": -100, "y": 0}}
        res = ctx.do(f"create workflow {name} ({len(transitions)} transitions)", site.post, "/rest/api/3/workflows/create", {"scope": {"type": "GLOBAL"}, "statuses": statuses, "workflows": [wf]})
        if res:
            s, x = res; ctx.need(s == 200, f"workflow {name}: {s} {str(x)[:500]}")
            w = x["workflows"][0]; out[name] = {"id": w["id"], "version": w.get("version")}
    ctx.state.save()


def map_scheme(ctx):
    site, S = ctx.site, ctx.S
    if not S.get("project") or any(n not in S.get("workflows", {}) for n in WORKFLOWS): ctx.plan("map the three workflows to the JML scheme (after they exist)"); return
    pid = str(S["project"]["id"]); IT = S["issueTypes"]; W = S["workflows"]; ST = S["statuses"]
    s, sch = site.post("/rest/api/3/workflowscheme/read", {"projectIds": [pid]}); ctx.need(s == 200, f"read JML workflow scheme: {s}")
    sch = sch[0]
    current = {it: m["workflow"]["name"] for m in sch["workflowsForIssueTypes"] for it in m["issueTypeIds"]}
    default_wf = sch["defaultWorkflow"]
    ctx.state.set("jmlDefaultWorkflow", name=current.get(str(IT["Task"]), default_wf["name"]))
    todo = {t: WF_FOR_TYPE[t] for t in LIFECYCLE_TYPES if current.get(str(IT[t])) != WF_FOR_TYPE[t]}
    if not todo: ctx.say("workflow scheme already maps Joiner, Mover, Leaver"); return
    new = {str(IT[t]): W[w]["id"] for t, w in WF_FOR_TYPE.items()}
    wfit = {}
    for m in sch["workflowsForIssueTypes"]:
        for it in m["issueTypeIds"]: wfit.setdefault(new.get(it, m["workflow"]["id"]), []).append(it)
    overrides = []
    for t, wname in todo.items():
        old = _read_workflow(site, current[str(IT[t])]); ctx.need(old, f"cannot read current workflow for {t}")
        old_st = {x["name"]: x["id"] for x in old["statuses"]}
        new_names = {n for _, f, to in WORKFLOWS[wname] for n in (f or []) + [to]}
        maps = []
        for oname, oid in old_st.items():
            target = REMAP[t].get(oname) or (oname if oname in new_names else None)
            if not target:
                ocat = next((x["statusCategory"] for x in old["statuses"] if x["name"] == oname), "TODO")
                target = {"TODO": "Open", "DONE": "Closed"}.get(ocat) or next(n for n in new_names if dict(STATUSES)[n] == "IN_PROGRESS")
            if str(oid) != str(ST[target]): maps.append({"oldStatusId": str(oid), "newStatusId": str(ST[target])})
        overrides.append({"issueTypeId": str(IT[t]), "statusMappings": maps})
    body = {"id": sch["id"], "version": sch["version"], "defaultWorkflowId": default_wf["id"],
            "workflowsForIssueTypes": [{"workflowId": k, "issueTypeIds": v} for k, v in wfit.items()],
            "statusMappingsByIssueTypeOverride": overrides, "description": "Workflow scheme for People Operations (JML): Joiner, Mover, Leaver workflows"}
    r = ctx.do(f"map {', '.join(f'{t} -> {w}' for t, w in todo.items())} on scheme {sch['id']}", site.post, "/rest/api/3/workflowscheme/update", body)
    if r: s, x = r; ctx.need(s in (200, 204), f"workflow scheme update: {s} {str(x)[:600]}")


def _find_field(site, name, ftype):
    s, r = site.get(f"/rest/api/3/field/search?query={urllib.parse.quote(name)}&type=custom&maxResults=50")
    return [f for f in r.get("values", []) if s == 200 and f["name"] == name and f.get("schema", {}).get("custom") == ftype]


def ensure_fields(ctx):
    site = ctx.site; F = ctx.state.sec("fields"); screens = _jml_screens(ctx) if ctx.S.get("project") else {}
    joiner_fields = set()
    if screens.get(J):
        s, r = site.get(f"/rest/api/3/screens/{screens[J][0]}/tabs/{screens[J][1]}/fields"); joiner_fields = {x["id"] for x in (r or [])} if s == 200 else set()
    for name, ftype, options, _, reuse in FIELDS:
        cands = _find_field(site, name, ftype)
        if len(cands) > 1: cands.sort(key=lambda f: (f["id"] not in joiner_fields, f["id"]))
        if cands:
            fid = cands[0]["id"]; F[name] = fid; ctx.say(f"field {name}: {fid}" + (" (reused template field)" if reuse else ""))
        else:
            r = ctx.do(f"create custom field {name} ({ftype.split(':')[-1]})", site.post, "/rest/api/3/field", {"name": name, "type": ftype, "searcherKey": SEARCH[ftype]})
            if not r: continue
            s, x = r; ctx.need(s in (200, 201), f"field {name}: {s} {str(x)[:300]}"); fid = x["id"]; F[name] = fid
        s, cx = site.get(f"/rest/api/3/field/{fid}/context"); ctxs = cx.get("values", []) if s == 200 else []
        if ctxs:
            cid = next((c["id"] for c in ctxs if c.get("isGlobalContext")), ctxs[0]["id"]); F[name + " contextId"] = cid
            if options or reuse and ftype.endswith("select"):
                s, o = site.get(f"/rest/api/3/field/{fid}/context/{cid}/option"); have = {x["value"]: x["id"] for x in o.get("values", [])} if s == 200 else {}
                missing = [v for v in (options or []) if v not in have]
                if missing:
                    r = ctx.do(f"add options {missing} to {name}", site.post, f"/rest/api/3/field/{fid}/context/{cid}/option", {"options": [{"value": v, "disabled": False} for v in missing]})
                    if r:
                        s, x = r; ctx.need(s in (200, 201), f"options {name}: {s} {str(x)[:300]}")
                        for x2 in x.get("options", []): have[x2["value"]] = x2["id"]
                if have: F[name + " options"] = have
    ctx.state.save()


def _jml_screens(ctx):
    """{issue type name: (screenId, tabId)} for the JML project's screens, plus "ITF" for the IT Fulfilment default screen."""
    site, S = ctx.site, ctx.S; out = {}
    def scheme_screens(pid):
        s, r = site.get(f"/rest/api/3/issuetypescreenscheme/project?projectId={pid}")
        if s != 200 or not r.get("values"): return {}
        iid = r["values"][0]["issueTypeScreenScheme"]["id"]
        s, mp = site.get(f"/rest/api/3/issuetypescreenscheme/mapping?issueTypeScreenSchemeId={iid}&maxResults=100")
        m = {x["issueTypeId"]: x["screenSchemeId"] for x in mp.get("values", [])}
        s, ss = site.get("/rest/api/3/screenscheme?maxResults=100&id=" + "&id=".join(sorted(set(m.values()))))
        screens = {str(x["id"]): x["screens"].get("default") for x in ss.get("values", [])}
        return {it: screens.get(str(sid)) for it, sid in m.items()}
    if S.get("project"):
        m = scheme_screens(S["project"]["id"])
        for t in NEEDED_TYPES:
            sid = m.get(str(S["issueTypes"][t]), m.get("default"))
            if sid: out[t] = (sid, _tab(site, sid))
    if S.get("itf"):
        m = scheme_screens(S["itf"]["id"]); sid = m.get(str(S["itf"]["issueTypes"]["Task"]), m.get("default"))
        if sid: out["ITF"] = (sid, _tab(site, sid))
    return out


def _tab(site, screen_id):
    s, r = site.get(f"/rest/api/3/screens/{screen_id}/tabs"); return r[0]["id"] if s == 200 and r else None


def ensure_screens(ctx):
    site, F = ctx.site, ctx.S.get("fields", {}); screens = _jml_screens(ctx)
    if not screens: ctx.plan("add the fields to the JML and ITF screens (after the projects exist)"); return
    sc = ctx.state.sec("screens"); sc.update({k: {"screenId": v[0], "tabId": v[1]} for k, v in screens.items()}); ctx.state.save()
    for target, (sid, tid) in screens.items():
        s, r = site.get(f"/rest/api/3/screens/{sid}/tabs/{tid}/fields"); have = {x["id"] for x in (r or [])} if s == 200 else set()
        for name, ftype, _, where, _ in FIELDS:
            if target not in where or name not in F or F[name] in have: continue
            r = ctx.do(f"add {name} to the {target} screen {sid}", site.post, f"/rest/api/3/screens/{sid}/tabs/{tid}/fields", {"fieldId": F[name]})
            if r and r[0] not in (200, 201): ctx.warn(f"could not add {name} to screen {sid}: {r[0]} {str(r[1])[:200]}")
