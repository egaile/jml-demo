# 04. Seed work items (the three characters)

Create these after the automation rules (05) are enabled, so the Joiner's fan-out exists.



Create three work items in JML (MCP `createJiraIssue` or REST). Create them **after** the chapter 05 rules are enabled if you want A1's fan-out to exist on the Joiner; otherwise run the Fan out transition by hand later.

| Key (expected) | Type | Summary | Fields |
| --- | --- | --- | --- |
| JML-1 | Employee offboarding | Offboarding: Lawrence Barnes (Operations Manager, IT Operations) | Last day: a date 2 to 3 weeks after the talk; Employee ID lbarnes; Role Operations Manager; Manager: you (or a Mitch Davis user if one exists); Badge number BADGE-1108; JML Employee → Lawrence Barnes; JML Badge → BADGE-1108; Knowledge audit status Not started; Deprovisioning status Not started |
| JML-2 | HR request (with approval) | Transfer: Marcus Webb, Sales Advocate to Senior Support Engineer (Solution Engineering) | Effective date: talk week; Employee ID mwebb; Role Sales Advocate; Target Role → Senior Support Engineer; JML Employee → Marcus Webb; Badge number BADGE-3417; Manager: you |
| JML-3 | Employee onboarding | Onboarding: Riley Chen, Marketing Associate (Sales & Marketing) | Start date: a date after the talk; Employee ID rchen; Role Marketing Associate; Manager: you; Badge number BADGE-4471; JML Employee → Riley Chen; JML Badge → BADGE-4471 |

Descriptions:

- JML-1: "Lawrence Barnes is leaving after 25 years. Last day is {Last day}. Manager: Mitch Davis. Badge BADGE-1108 carries Server room, Network closets, and the Legacy data center [DECOMMISSIONED] zone. Owns runbooks in the ITO space (label owner-lbarnes)."
- JML-2: "Marcus Webb is moving from Sales (Sales Advocate) to Solution Engineering (Senior Support Engineer), effective {Effective date}. Current manager: Bruce Banner. New manager: Mitch Davis. Access must shrink before it grows: Access Audit agent to produce REVOKE, GRANT, RETAINED, DRIFT."
- JML-3: "Riley Chen starts {Start date} as a Marketing Associate reporting to Bruce Banner. Provision from Role Profile: Marketing Associate (Standard Employee, Standard Creative). Badge BADGE-4471: Floors 1-3 business hours, Marketing storage."

For JML-2, run **Submit for approval** so it sits in Awaiting approval; the Mover act on stage is the Approve transition.

For JML-3, run **Fan out** once (A1 creates its five tasks), then close every task except **Legal** so the stage moment is "close the Legal task".
