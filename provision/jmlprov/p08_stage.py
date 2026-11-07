"""Phase 8: the stage state. The Joiner is fanned out and four of its five tasks are closed (Legal stays open for the
'close the last task, badge turns green' moment); the Leaver and Mover stay where phase 4 left them."""
import time


def run(ctx):
    S, site = ctx.S, ctx.site; seeds = S.get("seeds", {})
    if "joiner" not in seeds: ctx.plan("fan out the Joiner and close four tasks (after the seeds exist)"); return
    k = seeds["joiner"]; s, r = site.get(f"/rest/api/3/issue/{k}?fields=status,issuelinks")
    fanout_ready = ("A1 Joiner fan-out" in S.get("automationRules", {})) or S.get("jmwe", {}).get("postFunctions")
    if r["fields"]["status"]["name"] == "Open":
        if not fanout_ready: ctx.say("Joiner left in Open: nothing would fan it out yet (Automation A1 or JMWE)"); return
        res = ctx.do(f"{k}: Fan out", site.transition, k, "Fan out")
        if not res: return
        for _ in range(12):
            time.sleep(5); s, r = site.get(f"/rest/api/3/issue/{k}?fields=status,issuelinks")
            if len(r["fields"]["issuelinks"]) >= 5: break
    linked = [(l.get("outwardIssue") or l.get("inwardIssue")) for l in r["fields"]["issuelinks"]]
    tasks = [o for o in linked if o["fields"]["issuetype"]["name"] == "Task"]
    if len(tasks) < 5: ctx.warn(f"{k} has {len(tasks)} fan-out tasks (expected 5)"); return
    for o in tasks:
        name = o["fields"]["summary"]; st = o["fields"]["status"]["statusCategory"]["key"]
        if name.startswith("Legal:") or st == "done": continue
        tr = site.transitions(o["key"]); tname = next((n for n in ("Mark as done", "Done") if n in tr), None)
        if tname: ctx.do(f"{o['key']} ({name[:40]}): {tname}", site.transition, o["key"], tname)
        else: ctx.warn(f"{o['key']}: no Done transition ({list(tr)})")
    ctx.say("stage: Joiner fanned out, Legal task open, the other four closed")
