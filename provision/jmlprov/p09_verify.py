"""Phase 9: read-only checks of what a talk needs. Prints a table; never changes anything."""


def run(ctx):
    S, site = ctx.S, ctx.site; ok = True
    def check(label, cond, detail=""):
        nonlocal ok; ok &= bool(cond); print(f"  [{'ok' if cond else 'MISSING'}] {label}" + (f": {detail}" if detail else ""))
    seeds = S.get("seeds", {})
    if seeds:
        tl = site.transitions(seeds.get("leaver", "")); check("Leaver offers Request confirmation / Manager confirmed / Start deprovisioning", {"Request confirmation", "Manager confirmed", "Start deprovisioning"} <= set(tl), ", ".join(tl))
        tm = site.transitions(seeds.get("mover", "")); check("Mover offers Approve / Decline", {"Approve", "Decline"} <= set(tm), ", ".join(tm))
        s, r = site.get(f"/rest/api/3/issue/{seeds.get('joiner','')}?fields=status,issuelinks")
        check("Joiner in Pre-Day-One with 5 linked tasks", s == 200 and r["fields"]["status"]["name"] == "Pre-Day-One" and len(r["fields"]["issuelinks"]) >= 5, r["fields"]["status"]["name"] if s == 200 else "")
    else: check("seed work items", False)
    rules = S.get("automationRules", {})
    if rules:
        BASE = site.auto_base(); s, lst = site.post(f"{BASE}/{S['project']['id']}/rules", {"offset": 0, "limit": 200}); st = {v["name"]: v.get("state") for v in lst.get("values", [])} if s == 200 else {}
        for n in ctx.edition["automation"]:
            fallback = n in ctx.edition["automation_fallback"]
            check(f"rule {n} {'exists' if fallback else 'ENABLED'}", n in st and (fallback or st[n] == "ENABLED"), st.get(n, "absent"))
    if ctx.edition["jmwe"]: check("JMWE post-functions installed", S.get("jmwe", {}).get("postFunctions"), S.get("jmwe", {}).get("postFunctions", ""))
    check("JSM SLAs Deprovisioning verified / Revokes complete", {"Deprovisioning verified", "Revokes complete"} <= set(S.get("jsmSlas", {})))
    tts = S.get("timeToSla", {}).get("slas", {}); check("Time to SLA clocks (4)", len({"Badge zones revoked", "Identity disabled", "Entitlements removed", "Revoke access"} & set(tts)) == 4, ", ".join(tts) or "no token or not built")
    pages = S.get("confluence", {}).get("pages", {}); check("Confluence pages (9)", len(pages) == 9, f"{len(pages)} recorded")
    A = S.get("assets", {}); check("Assets objects", len(A.get("badges", {})) == 3 and len(A.get("people", {})) == 5, f"{len(A.get('people', {}))} people, {len(A.get('badges', {}))} badges")
    s, r = site.get(ctx.opts["console_url"].rstrip("/") + "/api/badge?badge_number=BADGE-1108", auth="")
    check("badge console reachable (BADGE-1108)", s == 200, str(r)[:80] if s == 200 else f"HTTP {s}")
    ctx.note("verify", "ok", ok)
    print("  verification " + ("passed" if ok else "has gaps; see the manual guide"))
