"""Phase 6: the two native JSM SLAs on JML and the four Time to SLA clocks on ITF, via the kit's build_slas.py (standard library,
idempotent). Time to SLA needs its own per-site API token; the A9 breach actions need rule A9's webhook URL and secret."""
import os, subprocess, sys


def run(ctx):
    S, site = ctx.S, ctx.site
    if not (S.get("project") and S.get("itf") and S.get("statuses")): ctx.plan("create the SLAs (after the projects exist)"); return
    script = ctx.opts["kit_dir"] / "scripts" / "build_slas.py"
    env = dict(os.environ, JIRA_SITE=site.url, JIRA_EMAIL=site.email, JIRA_TOKEN=ctx.opts["token"], TTS_BASE=site.tts_base or "https://tts-us.snapbytesapps.com",
               TTS_TOKEN=site.tts_token or "", TTS_CALENDAR=ctx.opts.get("tts_calendar", "Business Hours 9-5"), TIME_ZONE=site.me().get("timeZone", "America/New_York"))
    url, secret = ctx.opts.get("a9_webhook") or ("", "")
    if url: env.update(A9_WEBHOOK_URL=url, A9_WEBHOOK_SECRET=secret)
    else: ctx.note("slas", "a9_webhook_missing", True)
    if not site.tts_token: ctx.note("slas", "tts_token_missing", True)
    cmd = [sys.executable, "-I", str(script)] + (["--apply"] if ctx.apply else [])
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    for line in (r.stdout + r.stderr).strip().splitlines(): print("    | " + line)
    if r.returncode != 0:
        if "read calendars" in r.stdout + r.stderr: ctx.say("Time to SLA part skipped: no working Time to SLA token for this site (the JSM SLAs above are done)")
        else: ctx.warn(f"build_slas.py exited {r.returncode}")
    # record the JSM SLA metric fields (the dashboard descriptors use them)
    s, m = site.get("/rest/servicedesk/1/servicedesk/agent/JML/sla/metrics")
    if s == 200:
        ctx.state.set("jsmSlas", **{x["name"]: {"id": x["id"], "customFieldId": x.get("customFieldId")} for x in m.get("timeMetrics", []) if x["name"] in ("Deprovisioning verified", "Revokes complete")})
    if site.tts_token:
        s, slas = site.tts("GET", "/api/sla/")
        if s == 200:
            ctx.state.set("timeToSla", base=site.tts_base, slas={x["name"]: x["id"] for x in slas})
            want = {"Badge zones revoked", "Identity disabled", "Entitlements removed", "Revoke access"}
            have = {x["name"] for x in slas}
            if want - have and ctx.apply: ctx.warn(f"Time to SLA definitions missing: {sorted(want - have)}")
            if url:
                missing = [x["name"] for x in slas if x["name"] in want and not any(a.get("actionType") == "AUTOMATION" for a in (site.tts("GET", f"/api/notifier/sla/{x['id']}")[1] or []))]
                if missing: ctx.note("slas", "actions_missing", missing)
