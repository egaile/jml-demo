# JML Agentic ESM: build kit

Everything you need to rebuild the "Joiner, Mover, Leaver: ESM in the Agentic Era" demo on your own Atlassian Cloud site: Jira Service Management, Jira Automation, Rovo agents, Assets, Confluence, Appfire Time to SLA, and a fake badge system to switch off live.

**The idea.** Rules move things; agents reason. A request is not done when the ticket closes; it is done when nothing is still running. The platform did not change. What "done" means did.

The whole kit is also one PDF: [JML-Demo-Build-Kit.pdf](JML-Demo-Build-Kit.pdf). To get everything, use **Code → Download ZIP** on the repo page.

![QR code for this repo](qr-jml-demo.png)

## The story

Northwind Labs, three employees, three acts:

| Act | Character | What happens |
| --- | --- | --- |
| Joiner | Riley Chen, Marketing Associate | The People Ops Concierge agent takes a plain-language request; automation fans out five tasks; closing the last one activates the badge |
| Mover | Marcus Webb, Sales Advocate → Senior Support Engineer | Approval triggers revoke-before-grant: GRANT tasks are blocked until the REVOKE is done; the Access Audit agent finds access drift |
| Leaver | Lawrence Barnes, 25 years, Operations Manager | The Knowledge Audit agent finds what he owns; deprovisioning fans out eight tasks and kills the badge in seconds; Time to SLA clocks run on each task and a breach escalates; the Deprovisioning agent verifies against the runbook and finds a decommissioned door zone still on the badge |

## Chapters

| # | Chapter | What you build |
| --- | --- | --- |
| 01 | [Projects, workflows, fields](01-projects-workflows-fields.md) | JSM project People Operations (JML), Jira project IT Fulfilment (ITF), statuses, three workflows, custom fields, link types |
| 02 | [Assets](02-assets.md) | People schema (people, roles, access policies) and Facilities schema (badges), objects, Assets fields |
| 03 | [Confluence](03-confluence.md) | EO, SECOPS, ITO spaces; policy, four role profiles, three runbooks (verbatim) |
| 04 | [Seed work items](04-seed-work-items.md) | The three characters' requests |
| 05 | [Automation rules](05-automation-rules.md) | A1 to A9 and Demo reset: spec tables and paste-ready "Create with Rovo" prompts |
| 06 | [Rovo agents](06-rovo-agents.md) | People Ops Concierge, Access Audit, Knowledge Audit, Deprovisioning: instructions, knowledge, tools, test prompts |
| 07 | [SLAs](07-slas.md) | Native JSM SLAs on the requests, Time to SLA clocks on the tasks, breach escalation; UI steps or one API script ([scripts/build_slas.py](scripts/build_slas.py)) |
| 08 | [Badge console](08-badge-console.md) | The SENTRIA badge system: deploy this repo or build your own with the AI prompt |
| 09 | [Stage script and reset](09-stage-script-and-reset.md) | Verification checks, the talk run-sheet, resetting after a rehearsal |
| 10 | [Lessons learned](10-lessons-learned.md) | What cost us time |
| 11 | [End-to-end walkthrough](11-demo-walkthrough.md) | Every demo step with what to do, what you should see, how to check it, and what happened in our reference run |

**Build order:** 08 (console, any time) → 01 → 02 → 03 → 05 → 04 → 06 → 07 → 09 → 11.

## What you need

- Atlassian Cloud with **Jira Service Management Premium** (Assets, approvals), **Confluence**, **Rovo**, and org admin rights to install **Appfire Time to SLA** from the Marketplace.
- A free **Supabase** project and a free **Vercel** account for the badge console.
- About a day. Most of it is pasting prompts and instructions.

## Conventions

- Names are load-bearing: rules find transitions by name, agents find pages by title and label, and rules can invoke agents by name. Use the names exactly as written.
- Ids (fields, statuses, Assets keys like `PPL-276`) differ on every site. Wherever you see one, use yours.
- `<your-console>` stands for your badge console's Vercel host name.
- All people and companies are fictional.
