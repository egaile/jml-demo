#!/usr/bin/env python3
"""Build the JML Agentic ESM demo (Atlassian or Appfire edition) on an Atlassian Cloud site.

  python3 provision/provision.py --site https://<site>.atlassian.net --edition appfire            # plan only
  python3 provision/provision.py --site https://<site>.atlassian.net --edition appfire --apply    # build what is missing

Everything is find-or-create, so rerunning is safe. Phases: jira, assets, confluence, seeds, automation, jmwe, slas, stage, verify.
The run ends by writing provision/state/<host>-MANUAL.md: the steps that need a person, with this site's ids filled in."""
import argparse, datetime, pathlib, sys, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from jmlprov import api, editions, manual, p01_jira, p02_assets, p03_confluence, p04_seeds, p05_automation, p06_slas, p07_jmwe, p08_stage, p09_verify

PHASES = [("jira", p01_jira), ("assets", p02_assets), ("confluence", p03_confluence), ("seeds", p04_seeds), ("automation", p05_automation),
          ("jmwe", p07_jmwe), ("slas", p06_slas), ("stage", p08_stage), ("verify", p09_verify)]
ROOT = pathlib.Path(__file__).resolve().parent


def read_secret(path):
    p = pathlib.Path(path).expanduser()
    return p.read_text().strip() if p.exists() else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", required=True, help="https://<site>.atlassian.net")
    ap.add_argument("--edition", required=True, choices=list(editions.EDITIONS))
    ap.add_argument("--email", required=True, help="your Atlassian account email")
    ap.add_argument("--token-file", default="~/.confluence-token", help="Atlassian API token (account-wide)")
    ap.add_argument("--tts-base", default="https://tts-us.snapbytesapps.com", help="Time to SLA regional API base")
    ap.add_argument("--tts-token-file", default=None, help="Time to SLA API token for this site (default ~/.tts-token-<host>)")
    ap.add_argument("--a9-webhook-file", default=None, help="rule A9's webhook URL and secret, two lines (default ~/.a9-webhook-<host>)")
    ap.add_argument("--console-url", default="https://jml-badge-console.vercel.app")
    ap.add_argument("--apply", action="store_true", help="make changes (default: print the plan)")
    ap.add_argument("--only", default="", help="comma-separated phases to run")
    ap.add_argument("--skip", default="", help="comma-separated phases to skip")
    ap.add_argument("--state", default=None, help="state file (default provision/state/<host>.json)")
    ap.add_argument("--kit-dir", default=str(ROOT.parent / "kit")); ap.add_argument("--build-dir", default=str(ROOT.parent / "build"))
    ap.add_argument("--last-day", default=None, help="Leaver's last day (default today + 21 days)")
    ap.add_argument("--start-date", default=None, help="Joiner start / Mover effective date (default the Monday at least a week out)")
    ap.add_argument("--enable-secret-rules", action="store_true", help="enable A2, A7, Demo reset and Demo: teams done after their secrets were pasted")
    ap.add_argument("--guide-only", action="store_true", help="only regenerate the manual guide from the state file")
    a = ap.parse_args()

    host = urllib.parse.urlparse(a.site).hostname or a.site
    token = read_secret(a.token_file)
    if not token: sys.exit(f"no API token in {a.token_file}")
    legacy = host == "one-atlas-eplm.atlassian.net"
    tts_token = read_secret(a.tts_token_file or f"~/.tts-token-{host}") or (read_secret("~/.tts-token") if legacy else "")
    a9 = read_secret(a.a9_webhook_file or f"~/.a9-webhook-{host}") or (read_secret("~/.a9-webhook") if legacy else "")
    a9 = tuple(a9.split("\n")[:2]) if a9 and "\n" in a9 else None
    today = datetime.date.today(); monday = today + datetime.timedelta(days=(7 - today.weekday()) % 7 + 7)
    opts = {"token": token, "console_url": a.console_url, "kit_dir": pathlib.Path(a.kit_dir), "build_dir": pathlib.Path(a.build_dir), "edition_name": a.edition,
            "last_day": a.last_day or str(today + datetime.timedelta(days=21)), "start_date": a.start_date or str(monday), "a9_webhook": a9}
    opts["effective_date"] = opts["start_date"]; opts["tts_calendar"] = "Business Hours 9-5 ET" if legacy else "Business Hours 9-5"
    site = api.Site(a.site, a.email, token, a.tts_base, tts_token)
    state = api.State(a.state or ROOT / "state" / f"{host}.json"); state.set("site", url=site.url, edition=a.edition)
    ctx = api.Ctx(site, state, editions.EDITIONS[a.edition], a.apply, opts)
    guide = ROOT / "state" / f"{host}-MANUAL.md"
    print(f"== {host} · {editions.EDITIONS[a.edition]['label']} · {'APPLY' if a.apply else 'PLAN ONLY (add --apply)'}")
    try:
        print(f"   signed in as {site.me().get('displayName')} ({site.me().get('emailAddress')}), cloudId {site.cloud_id()}")
        if a.enable_secret_rules:
            for name in editions.SECRET_RULES:
                rid = state.d.get("automationRules", {}).get(name)
                if rid: ctx.apply = True; p05_automation.set_state(ctx, rid, "ENABLED", name)
                else: print(f"  rule {name} not in the state file")
            return
        if not a.guide_only:
            only = [x for x in a.only.split(",") if x]; skip = [x for x in a.skip.split(",") if x]
            for name, mod in PHASES:
                if (only and name not in only) or name in skip: continue
                print(f"\n== phase {name}")
                mod.run(ctx)
        manual.write(ctx, guide); print(f"\nManual guide: {guide}")
        if not a.apply: print("Plan only. Rerun with --apply to build what is missing.")
    except api.ProvisionError as e:
        print(f"\nSTOPPED: {e}"); manual.write(ctx, guide); sys.exit(1)
    finally:
        state.save()


if __name__ == "__main__":
    main()
