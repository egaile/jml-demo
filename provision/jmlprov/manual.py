"""Writes the per-site manual guide: everything the APIs cannot do, with this site's ids already filled in, in the order to do it."""
import datetime, json, re

# ids of the reference site (one-atlas-eplm), as they appear in the kit, the agent instructions and the dashboard descriptors
OLD_FIELDS = {"customfield_10741": "Badge number", "customfield_10742": "Last day", "customfield_10743": "Effective date", "customfield_10744": "Lifecycle phase",
              "customfield_10745": "Fan-out team", "customfield_10746": "Evidence", "customfield_10747": "Immediate termination", "customfield_10748": "Knowledge audit status",
              "customfield_10749": "Deprovisioning status", "customfield_10752": "JML Employee", "customfield_10753": "JML Badge", "customfield_10754": "Target Role",
              "customfield_10015": "Start date", "customfield_10058": "Manager", "customfield_10714": "Employee ID", "customfield_10727": "Role", "customfield_10713": "Department"}
OLD_JSM = {"customfield_10755": "Deprovisioning verified", "customfield_10756": "Revokes complete"}
OLD_ROLES = {"PPL-276": "Marketing Associate", "PPL-283": "Sales Advocate", "PPL-288": "Senior Support Engineer", "PPL-279": "Operations Manager"}
OLD_HOST = "one-atlas-eplm.atlassian.net"
AGENTS = [  # name, backup file (published instructions), kit block, knowledge, actions, starters
 ("People Ops Concierge", None, "B.1", "EO, SECOPS spaces; JML project", "Jira create, search, comment, transition; Confluence read",
  ["Start onboarding for a new hire.", "Transfer an employee to a new team.", "Lawrence Barnes is leaving in three weeks, start the offboarding.", "What access does a Marketing Associate get?"]),
 ("Access Audit", "Access_Audit.json", "B.2", "EO space; JML and ITF projects; People schema", "Jira get, search, create, edit, comment; Confluence read; Assets search",
  ["Audit JML-2.", "What changes when a Sales Advocate becomes a Senior Support Engineer?", "Show drift for Marcus Webb."]),
 ("Knowledge Audit Agent", "Knowledge_Audit_Agent.json", "B.3", "ITO, EO, SECOPS spaces; JML and ITF projects; People and Facilities schemas", "Jira get, search, create, edit, comment; Confluence search, read, comment; Assets search",
  ["Audit JML-1. What does Lawrence Barnes own?", "Which runbooks lose their owner when Lawrence leaves?", "Who should take over the Legacy Data Center runbook?"]),
 ("Deprovisioning", "Deprovisioning.json", "B.4", "SECOPS, EO spaces; JML and ITF projects; People and Facilities schemas", "Jira get, search, create, edit, comment, transition; Confluence read, search; Assets search",
  ["Verify JML-1.", "Is anything still running for Lawrence Barnes?", "Write the closure report for JML-1."]),
]


def localizer(ctx):
    S = ctx.S; F = S.get("fields", {}); host = ctx.site.url.split("//")[-1]
    rep = {old: F[name] for old, name in OLD_FIELDS.items() if F.get(name) and F[name] != old}
    for old, name in OLD_JSM.items():
        cf = S.get("jsmSlas", {}).get(name, {}).get("customFieldId")
        if cf: rep[old] = f"customfield_{cf}" if not str(cf).startswith("customfield") else cf
    for old, name in OLD_ROLES.items():
        k = S.get("assets", {}).get("roleKeys", {}).get(name)
        if k and k != old: rep[old] = k
    task = str(S.get("issueTypes", {}).get("Task", "10002"))
    seeds = S.get("seeds", {}); keys = {"JML-1": seeds.get("leaver"), "JML-2": seeds.get("mover"), "JML-3": seeds.get("joiner")}
    def loc(text):
        for old, new in rep.items():
            text = text.replace(old, new)
            if old.startswith("customfield_"): text = text.replace("cf[" + old[12:] + "]", "cf[" + new[12:] + "]")
        text = text.replace(OLD_HOST, host)
        if task != "10002": text = re.sub(r"\b10002\b", task, text)
        for old, new in keys.items():
            if new and new != old: text = re.sub(rf"\b{old}\b", new, text)
        return text
    return loc


def kit_block(kit_dir, chapter, heading):
    """The fenced block right after '### <heading>' in a kit chapter."""
    txt = (kit_dir / chapter).read_text()
    m = re.search(rf"^#{{3,4}} {re.escape(heading)}[^\n]*\n+```\n(.*?)\n```", txt, re.S | re.M)
    return m.group(1) if m else ""


def agent_instructions(ctx, name, backup, block):
    build = ctx.opts["build_dir"]; kit = ctx.opts["kit_dir"]
    if backup and (build / "agent-backups" / backup).exists():
        d = json.loads((build / "agent-backups" / backup).read_text())
        try: return d["scenarios"][0]["instruction"], "published instructions, exported from Rovo Studio on the reference site"
        except (KeyError, IndexError): pass
    txt = (kit / "06-rovo-agents.md").read_text()
    m = re.search(rf"^### {re.escape(block)} .*?\n```\n(.*?)\n```", txt, re.S | re.M)
    base = m.group(1) if m else "(see kit/06-rovo-agents.md)"
    extra = ""
    if name != "People Ops Concierge":
        extra = "\n\n" + kit_block(kit, "06-rovo-agents.md", "All three task-creating agents")
        only = {"Access Audit": "Access Audit only", "Knowledge Audit Agent": "Knowledge Audit Agent only", "Deprovisioning": "Deprovisioning only"}[name]
        extra += "\n\n" + kit_block(kit, "06-rovo-agents.md", only)
    return base + extra, "kit chapter 06 instructions plus the guardrail additions"


def write(ctx, path):
    S, site, ed = ctx.S, ctx.site, ctx.edition; loc = localizer(ctx); N = ctx.notes; host = site.url.split("//")[-1]
    F = S.get("fields", {}); rules = S.get("automationRules", {}); pid = S.get("project", {}).get("id")
    rule_url = lambda name: f"{site.url}/jira/servicedesk/projects/JML/settings/automate#/rule/{rules.get(name, '')}"
    L = []; w = L.append
    w(f"# Manual steps for {host}: {ctx.opts['edition_name']} edition\n")
    w(f"Generated {datetime.date.today()} by provision.py. Everything below is what the APIs cannot do. Do the steps in order; where a step says *rerun*, run the provisioner again afterwards (it only adds what is missing):\n")
    w(f"```bash\npython3 provision/provision.py --site {site.url} --edition {ctx.opts['edition_name']} --apply\n```\n")
    w("## 0. Before the build (once per site)\n")
    w("- Jira Service Management **Premium** (Assets, approvals), Confluence and Rovo on the site; you are org admin and site admin.")
    w("- Install from the Marketplace (org admin): " + ", ".join(f"**{a}**" for a in ed["apps"]) + ".")
    w("- An Atlassian API token for your account in `~/.confluence-token` (tokens are account-wide, so the one you already use works on a new site).")
    w("- Optional: users **Mitch Davis** and **Bruce Banner** on the site (the Leaver's manager falls back to you when Mitch does not exist).")
    w("- The badge console at " + ctx.opts["console_url"] + " is independent of the site and is reused as it is.\n")
    n = 1
    from .editions import SECRET_RULES
    secrets = [r for r in ed["automation"] if r in SECRET_RULES and r in rules]
    if secrets:
        w(f"## {n}. Automation rules: paste the secrets, then enable\n"); n += 1
        w("These rules are created **disabled** because they carry a secret. For each one that is still disabled: open it, edit the **Send web request** action(s), paste the hidden header value, save. Then enable them all with one command.\n")
        for name in secrets:
            what = "`Authorization` = `Basic <base64 of your-email:api-token>` (two web requests, both headers)" if name == "Demo: teams done" else "`X-JML-Secret` = the badge console secret (Vercel env `JML_SECRET`)"
            w(f"- **{name}**: {rule_url(name)} → {what}")
        w(f"\n```bash\npython3 provision/provision.py --site {site.url} --edition {ctx.opts['edition_name']} --enable-secret-rules\n```\n")
    if "A9 SLA breach escalation" in rules:
        w(f"## {n}. Rule A9: copy its webhook into a file\n"); n += 1
        w(f"Open **A9 SLA breach escalation** ({rule_url('A9 SLA breach escalation')}), click the **Incoming webhook** trigger and copy the **Webhook URL** and the **Secret** into `~/.a9-webhook-{host}` (URL on line 1, secret on line 2). The API never returns the secret, so this is a copy step. Then *rerun* with `--only slas` so the Time to SLA breach actions can point at it.\n")
    w(f"## {n}. Time to SLA\n"); n += 1
    if not S.get("timeToSla", {}).get("slas"):
        w(f"- With Time to SLA installed, open **Apps → Time To SLA → Settings → API Token**, create a token and save it to `~/.tts-token-{host}`. Note the regional base URL shown there (US: `https://tts-us.snapbytesapps.com`, EU: `https://tts-eu.snapbytesapps.com`); pass it with `--tts-base` if it is not the US one.")
        w("- *Rerun* with `--only slas`: it creates the business-hours calendar, the four clocks and (once the A9 webhook file exists) the breach actions.")
    else:
        w("- The four clocks exist" + (f" ({', '.join(S.get('timeToSla', {}).get('slas', {}))})" if S.get("timeToSla") else "") + ".")
        if N.get("slas.actions_missing"): w(f"- Breach actions still missing on: {', '.join(N['slas.actions_missing'])} (rerun `--only slas` after the A9 webhook file exists).")
    w("- In Time to SLA → **Actions** (global): disable the default *email the assignee at 50%* action (fan-out tasks have no assignee, so it fails). Keep or add a global **Add comment** on *is breached* with `SLA breached: ${slaDescription} on ${issue.key}`; it is the visible trace on the task.")
    w("- Open each SLA's **Actions** tab and disable any reminder the app added by default.\n")
    w(f"## {n}. Rovo agents (Rovo Studio → Agents → Create agent)\n"); n += 1
    w("Create the four agents below. Names are load-bearing. For each: paste the instructions verbatim, restrict **Knowledge** as listed, enable only the listed **Actions**, add the conversation starters, then run the test prompt from kit chapter 06. Field ids, the Task work type id and the Role object keys in the instructions are already this site's.\n")
    for name, backup, block, knowledge, actions, starters in AGENTS:
        text, src = agent_instructions(ctx, name, backup, block)
        w(f"### {name}\n"); w(f"- **Knowledge:** {knowledge}"); w(f"- **Actions:** {actions}"); w("- **Conversation starters:** " + " | ".join(loc(s) for s in starters))
        w(f"- **Instructions** ({src}):\n"); w("```\n" + loc(text).strip() + "\n```\n")
    w("Rules of thumb from the reference build: the agents reason on the first prompt and write on the second; every write shows as a review card; if there is no card, nothing happened.\n")
    if ed["jmwe"]:
        w(f"## {n}. JMWE actions (Jira admin → Apps → JMWE)\n"); n += 1
        if N.get("jmwe.missing") or not S.get("jmwe", {}).get("postFunctions"): w("**JMWE is not installed yet.** Install it, then *rerun* with `--only jmwe` to put the post-functions and the revoke-before-grant validator on the workflows. Then come back here.\n")
        else: w(f"The workflow post-functions are installed by API ({S.get('jmwe', {}).get('postFunctions', '')}). The three actions below have no API; create them in the JMWE UI with one **Build-your-own (Nunjucks)** post-function each, paste the script, enable, and then **disable the Automation fallback rule** of the same name in Project settings → Automation.\n")
        src = ctx.opts["build_dir"] / "JMWE-ACTIONS.md"
        if src.exists():
            txt = src.read_text(); cut = txt.find("## A9 ·")
            body = txt[txt.find("## A5b"):cut if cut > 0 else None]
            w(re.sub(r"(?m)^## ", "### ", loc(body).strip()) + "\n")
        w(f"Automation fallbacks to disable once the JMWE actions are enabled: " + ", ".join(f"[{r}]({rule_url(r)})" for r in ed["automation_fallback"]) + ".\n")
    if ed["dashboard_hub"]:
        w(f"## {n}. Dashboard Hub Pro: the JML Lifecycle dashboard\n"); n += 1
        dh = ctx.opts["build_dir"] / "dashboard-hub"; out = path.parent / host / "dashboard-hub"
        files = sorted(dh.glob("*.json")) if dh.exists() else []
        if files:
            out.mkdir(parents=True, exist_ok=True)
            for f in files: (out / f.name).write_text(loc(f.read_text()))
            w(f"Descriptors with this site's field ids are in `{out.relative_to(path.parent.parent)}/`. Then:\n")
        w("1. In Dashboard Hub, **… → Add Datasource → Custom Report**: name `jira`, URL `" + site.url + "/`, Basic Auth with your email and API token.")
        w("2. Create a dashboard **JML Lifecycle**.")
        w("3. For each file: **Edit → Add gadget → Custom Reports → Getting Started → blank report**, select the `jira` datasource, **Open Editor**, paste the file, **Add**.")
        w("4. Layout: Lifecycle pipeline and Closed is not done on top, Fan-out work and Service clocks below.\n")
    w(f"## {n}. Badge console (SENTRIA)\n"); n += 1
    w("- Reused as it is. Before a talk set BADGE-4471 (Riley) inactive so A2's 'card turns green' moment shows a change: in Supabase run `update badges set status = 'INACTIVE', updated_at = now(), deactivated_at = null, deactivation_ref = null where badge_number = 'BADGE-4471';`")
    w("- Clear rehearsal rows: `delete from badge_events where source like 'Jira Automation%' or source = 'Demo reset';`\n")
    w(f"## {n}. Claude desktop\n"); n += 1
    w("Authorize the Atlassian MCP connector for this site in Claude desktop (Settings → Connectors) so the closing question, 'Is anything still running for Lawrence Barnes?', can read Jira, Confluence and Assets.\n")
    w(f"## {n}. Checks before calling it done\n"); n += 1
    seeds = S.get("seeds", {})
    w(f"1. {seeds.get('leaver', 'the Leaver')} offers Request confirmation, Manager confirmed, Start deprovisioning, Cancel; {seeds.get('mover', 'the Mover')} offers Approve and Decline; {seeds.get('joiner', 'the Joiner')} is in Pre-Day-One with the Legal task open.")
    w(f"2. Approve {seeds.get('mover', 'the Mover')}: one REVOKE and three GRANT tasks appear, GRANTs blocked by the REVOKE. Close the REVOKE: the Mover moves to Granting.")
    w(f"3. Start deprovisioning on {seeds.get('leaver', 'the Leaver')}: seven tasks plus the Security confirmation task; BADGE-1108 goes INACTIVE on the console within seconds.")
    w("4. Comment `#teams-done`, then ask the Deprovisioning agent to verify: one finding, the decommissioned zone; status Findings open.")
    w("5. Comment `#reset` (or run `build/scripts/reseed.py --apply`) to put the seeds back.")
    w("6. The verify phase of the provisioner prints the same list from the API: `python3 provision/provision.py ... --only verify`.\n")
    if ctx.warnings:
        w("## Warnings from the last run\n"); [w(f"- {x}") for x in ctx.warnings]; w("")
    path.write_text("\n".join(L)); return path
