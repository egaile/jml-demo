# Provisioner: build the JML demo on a new Atlassian Cloud site

This copy is for the public kit: use `--edition atlassian`. The `appfire` edition (JMWE, Dashboard Hub Pro) needs content that lives in the private jml-demo-appfire repository, where this tool is maintained.

One command builds everything the APIs can build, keeps a per-site state file of every id, and writes a guide for the rest:

```bash
python3 provision/provision.py --site https://<new-site>.atlassian.net --edition appfire
```

```bash
python3 provision/provision.py --site https://<new-site>.atlassian.net --edition appfire --apply
```

The first run only prints the plan. `--apply` creates what is missing; everything is find-or-create by name, so rerunning is safe and is how you continue after a manual step. The run ends by writing `provision/state/<host>-MANUAL.md`: the steps that need a person, in order, with this site's ids, keys and links already filled in.

## Editions

| | `atlassian` | `appfire` |
| --- | --- | --- |
| Rules that move the work | Jira Automation A1 to A10, Demo reset, Demo: teams done | JMWE post-functions on the workflows (A1, A3, A4, A6, A8, the revoke-before-grant validator); JMWE actions A5, A5b, A10 (UI); Automation keeps A2, A7, A9, Demo reset, Demo: teams done |
| Reporting | none | Dashboard Hub Pro, four Custom Reports descriptors |
| Apps to install first | Time to SLA | Time to SLA, JMWE, Dashboard Hub Pro |

Both editions share the rest: JSM project People Operations (JML) from the HR template, Jira project IT Fulfilment (ITF), statuses, the three workflows, fields, Assets (People and Facilities), Confluence pages, seed work items, JSM SLAs, Time to SLA clocks, Rovo agents (manual), the badge console (reused).

## Phases

| Phase | What it does | API |
| --- | --- | --- |
| `jira` | JML (HR service management template) and ITF (Kanban) projects, 13 statuses, workflows JML: Joiner / Mover / Leaver, scheme mapping, 17 custom fields with options, screens, link types | Jira platform |
| `assets` | People (PPL) and Facilities (FAC) schemas, object types, attributes, 23 objects, the three Assets custom fields' configuration. Works on top of Atlassian's template schemas or from nothing | Assets, cmdb fieldconfig |
| `confluence` | spaces EO, SECOPS, ITO and the nine pages verbatim from `kit/03-confluence.md`, labelled, Role object keys filled in | Confluence v2 |
| `seeds` | Lawrence (Leaver), Marcus (Mover, in Awaiting approval), Riley (Joiner), with Assets references | Jira |
| `automation` | the Automation rules of the edition through the automation gateway; secret-bearing rules stay disabled until the secret is pasted | gateway (internal) |
| `jmwe` | (appfire) post-functions and validator written onto the workflows; detects JMWE through the workflow capabilities API | Jira workflows |
| `slas` | JSM SLAs on JML, Time to SLA calendar, four clocks and A9 breach actions, via `kit/scripts/build_slas.py` | JSM, Time to SLA |
| `stage` | fans out the Joiner and closes four of five tasks (Legal stays open) | Jira |
| `verify` | read-only checks of the stage state, rules, SLAs, pages, Assets, console | all |

`--only jmwe,slas` runs a subset; `--skip stage` skips one; `--guide-only` regenerates the guide from the state file; `--enable-secret-rules` enables A2, A7, Demo reset and Demo: teams done once their headers are pasted.

## What stays manual, and why

- **Secrets in Automation rules** (badge console `X-JML-Secret`, Assets `Authorization`): pasted in the rule editor so they never pass through a script or a repo.
- **Rule A9's webhook URL and secret**: the automation API never returns the secret. Copy it into `~/.a9-webhook-<host>`, rerun `--only slas`.
- **Time to SLA token**: per site, created in the app's settings; `~/.tts-token-<host>`.
- **Rovo agents**: no API. The guide carries the published instructions with the site's field ids and Role keys substituted.
- **JMWE event-based and scheduled actions** (A5, A5b, A10): no API; the guide carries the scripts.
- **Dashboard Hub Pro**: no API for dashboards or gadgets; the guide writes site-specific descriptors to paste.
- **Marketplace installs, Rovo enablement, users**: org admin, UI.

## Files

- `provision.py`: the CLI. `jmlprov/`: one module per phase, `api.py` (client and state), `editions.py`, `manual.py` (guide writer).
- `state/<host>.json`: every id on that site (the new `jml-ids.json`). `state/<host>-MANUAL.md`: the guide. `state/<host>/dashboard-hub/`: localized descriptors.
- Content comes from the repo itself: `kit/03-confluence.md` (pages), `kit/06-rovo-agents.md` and `build/agent-backups/` (agent instructions), `build/JMWE-ACTIONS.md`, `build/dashboard-hub/*.json`, `kit/scripts/build_slas.py`.

## Tokens

An Atlassian API token is account-wide, so `~/.confluence-token` works on every site you are a member of. Time to SLA tokens and A9 webhooks are per site. Nothing secret is written to the state file or the guide.

## Tested

Discovery mode against the reference site (one-atlas-eplm, both editions): every phase finds what the original build created and plans nothing new. Creation of the two projects from their templates was exercised on throwaway projects (deleted afterwards). The other creation paths are the same calls the original build used, module by module, but a full build on an empty site has not been run yet: expect the first one to need a fix or two, and read the plan before `--apply`.
