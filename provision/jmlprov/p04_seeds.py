"""Phase 4: the three seed work items (Lawrence, Marcus, Riley), their Assets references, and the Mover sitting in Awaiting approval."""
import urllib.parse


def adf(text): return {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


def user(site, name):
    s, r = site.get(f"/rest/api/3/user/search?query={urllib.parse.quote(name)}")
    r = [u for u in (r or []) if s == 200 and u.get("accountType") == "atlassian" and u.get("active")]
    return r[0]["accountId"] if r else None


def run(ctx):
    site, S = ctx.site, ctx.S; F, IT = S.get("fields", {}), S.get("issueTypes", {})
    need = ["Badge number", "Last day", "Effective date", "Employee ID", "Role", "Manager", "Knowledge audit status", "Deprovisioning status", "Start date"]
    if not S.get("project") or any(n not in F for n in need): ctx.plan("create the seed work items (after the project and fields exist)"); return
    me = site.me()["accountId"]; mitch = user(site, "Mitch Davis") or me
    LAST, EFF, START = ctx.opts["last_day"], ctx.opts["effective_date"], ctx.opts["start_date"]
    opt = lambda f, v: {"id": str(F[f + " options"][v])}
    seeds = [
     ("leaver", "Offboarding: Lawrence Barnes (Operations Manager, IT Operations)", {"issuetype": {"id": str(IT["Employee offboarding"])},
       "description": adf(f"Lawrence Barnes is leaving after 25 years. Last day is {LAST}. Manager: Mitch Davis. Badge BADGE-1108 carries Server room, Network closets, and the Legacy data center [DECOMMISSIONED] zone. Owns runbooks in the ITO space (label owner-lbarnes)."),
       F["Last day"]: LAST, F["Employee ID"]: "lbarnes", F["Role"]: "Operations Manager", F["Manager"]: [{"accountId": mitch}], F["Badge number"]: "BADGE-1108",
       F["Knowledge audit status"]: opt("Knowledge audit status", "Not started"), F["Deprovisioning status"]: opt("Deprovisioning status", "Not started")}),
     ("mover", "Transfer: Marcus Webb, Sales Advocate to Senior Support Engineer (Solution Engineering)", {"issuetype": {"id": str(IT["HR request (with approval)"])},
       "description": adf(f"Marcus Webb is moving from Sales (Sales Advocate) to Solution Engineering (Senior Support Engineer), effective {EFF}. Current manager: Bruce Banner. New manager: Mitch Davis. Access must shrink before it grows: Access Audit agent to produce REVOKE, GRANT, RETAINED, DRIFT."),
       F["Effective date"]: EFF, F["Employee ID"]: "mwebb", F["Role"]: "Sales Advocate", F["Manager"]: [{"accountId": me}], F["Badge number"]: "BADGE-3417"}),
     ("joiner", "Onboarding: Riley Chen, Marketing Associate (Sales & Marketing)", {"issuetype": {"id": str(IT["Employee onboarding"])},
       "description": adf(f"Riley Chen starts {START} as a Marketing Associate reporting to Bruce Banner. Provision from Role Profile: Marketing Associate (Standard Employee, Standard Creative). Badge BADGE-4471: Floors 1-3 business hours, Marketing storage."),
       F["Start date"]: START, F["Employee ID"]: "rchen", F["Role"]: "Marketing Associate", F["Manager"]: [{"accountId": me}], F["Badge number"]: "BADGE-4471"}),
    ]
    seeds_state = ctx.state.sec("seeds")
    for role, summary, fields in seeds:
        hit = site.search(f'project = JML AND summary ~ "\\"{summary.split(" (")[0].split(",")[0]}\\"" ORDER BY created ASC', max_results=5)
        if hit: seeds_state[role] = hit[0]["key"]; ctx.say(f"{role}: {hit[0]['key']} exists ({hit[0]['fields']['status']['name']})"); continue
        res = ctx.do(f"create {role}: {summary}", site.post, "/rest/api/3/issue", {"fields": {"project": {"key": "JML"}, "summary": summary, **fields}})
        if res: s, x = res; ctx.need(s == 201, f"{role}: {s} {str(x)[:400]}"); seeds_state[role] = x["key"]
    ctx.state.save()
    if not all(r in seeds_state for r, _, _ in seeds): return
    # Department (template select) if its options exist
    dept = {"leaver": "Information Technology", "mover": "Sales", "joiner": "Marketing"}; opts = F.get("Department options", {})
    cur = {}
    for role in seeds_state:
        s, r = site.get(f"/rest/api/3/issue/{seeds_state[role]}?fields=" + ",".join(F[n] for n in ("Department", "JML Employee", "JML Badge", "Target Role") if n in F)); cur[role] = r.get("fields", {}) if s == 200 else {}
    for role, v in dept.items():
        if v in opts and not (cur[role].get(F["Department"]) or {}).get("value") == v: ctx.do(f"{seeds_state[role]}: Department = {v}", site.put, f"/rest/api/3/issue/{seeds_state[role]}", {"fields": {F["Department"]: {"id": str(opts[v])}}})
    # Assets references
    A = S.get("assets", {}); ws = A.get("workspaceId")
    ov = lambda oid: [{"workspaceId": ws, "id": f"{ws}:{oid}", "objectId": str(oid)}]
    refs = {"leaver": {"JML Employee": A.get("people", {}).get("Lawrence Barnes"), "JML Badge": A.get("badges", {}).get("BADGE-1108")},
            "mover": {"JML Employee": A.get("people", {}).get("Marcus Webb"), "Target Role": A.get("roles", {}).get("Senior Support Engineer")},
            "joiner": {"JML Employee": A.get("people", {}).get("Riley Chen"), "JML Badge": A.get("badges", {}).get("BADGE-4471")}}
    for role, m in refs.items():
        fields = {F[f]: ov(oid) for f, oid in m.items() if oid and f in F and not cur[role].get(F[f])}
        if not fields and all(cur[role].get(F.get(f, "")) for f in m): continue
        if len(fields) < len(m): ctx.warn(f"{seeds_state[role]}: some Assets references unknown yet (run phase 2 first)")
        if fields:
            res = ctx.do(f"{seeds_state[role]}: set {', '.join(m)}", site.put, f"/rest/api/3/issue/{seeds_state[role]}", {"fields": fields})
            if res and res[0] != 204: ctx.warn(f"{seeds_state[role]} Assets fields: {res[0]} {str(res[1])[:200]}")
    # the Mover waits for approval; the stage act is Approve
    k = seeds_state["mover"]; s, r = site.get(f"/rest/api/3/issue/{k}?fields=status")
    if s == 200 and r["fields"]["status"]["name"] == "Open": ctx.do(f"{k}: Submit for approval", site.transition, k, "Submit for approval")
