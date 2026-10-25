# 03. Confluence spaces and pages

Three spaces: **EO** (Employee Onboarding, HR policy), **SECOPS** (Security Operations), **ITO** (IT Operations). Page bodies are verbatim: the agents quote them.



Create these pages with the Atlassian MCP `createConfluenceContent` (markdown body is fine) and then add labels with `POST /wiki/api/v2/pages/{id}/labels` or `POST /wiki/rest/api/content/{id}/label`. Labels are what the agents search by. Page bodies are in Appendix A and must be used verbatim; the agents quote them.

| Space | Title | Parent | Labels |
| --- | --- | --- | --- |
| EO | Joiner, Mover, Leaver (JML) Program | space home | jml |
| EO | JML Policy | JML Program | jml-policy, jml |
| EO | Role Profile: Marketing Associate | JML Program | role-profile, jml |
| EO | Role Profile: Sales Advocate | JML Program | role-profile, jml |
| EO | Role Profile: Senior Support Engineer | JML Program | role-profile, jml |
| EO | Role Profile: Operations Manager | JML Program | role-profile, jml |
| SECOPS | Leaver Deprovisioning Runbook | space home | runbook, jml, deprovisioning |
| ITO | RB - Legacy Data Center Decommission | space home | runbook, owner-lbarnes, legacy-data-center |
| ITO | RB - Network Closet Access Procedure | space home | runbook, owner-lbarnes, campus-network |

The two ITO runbooks are "owned" by Lawrence Barnes via the `owner-lbarnes` label and a "Document owner" row in a properties table. That is how the Knowledge Audit agent finds what he owns. The Legacy Data Center runbook contains the breaker 23 note the agent should call out as highest risk.

The Role Profile pages each state the Assets Role object key. Replace `PPL-nnn` in the page bodies below with the keys from chapter 02.

## Page bodies (verbatim)

### A.1 EO: Joiner, Mover, Leaver (JML) Program

```
This is the home for the Northwind Labs Joiner, Mover, Leaver program. The policy defines what must happen at each lifecycle event. Role Profiles define what access each role carries. Automation and Rovo agents in the **People Operations (JML)** Jira project do the work.

## How the program is organized

| Layer | Where it lives | What it does |
| --- | --- | --- |
| Policy | This space (Confluence) | Defines the rules. Agents read these pages before acting. |
| Role Profiles | This space, plus the **People** Assets schema (Role and Access Policy objects) | The entitlements a role carries. The Access Audit agent diffs two profiles to produce revoke and grant lists. |
| Work | Jira Service Management project **People Operations (JML)** | Joiner, Mover, and Leaver work items, fan-out tasks to IT, Facilities, Legal, Payroll, and Security. |
| Automation | Jira Automation rules in JML | Fan-out, blocking, scheduled confirmations, and the badge deactivation webhook. |
| Agents | Rovo Studio | People Ops Concierge, Access Audit, Knowledge Audit, Deprovisioning. |
| Physical access | SENTRIA Facility Console and the **Badge** object type in the Facilities Assets schema | Badge status is the flag. When it flips to INACTIVE, the door controller follows. |

## Pages in this section

(child pages list)
```

### A.2 EO: JML Policy

```
CURRENT Owner: People Operations. Reviewed quarterly with Security Operations.

## 1. Purpose

Every employee lifecycle event changes what a person should be able to reach: systems, data, rooms, and people. This policy defines the minimum that must happen at each event and who is accountable. It applies to employees, contractors, and interns.

The principle behind all of it: **access follows the role, not the person.** A person holds access only because their current role carries it.

## 2. Joiner

A Joiner is any person starting a role for the first time.

- A Joiner work item must exist in the People Operations (JML) project at least 10 business days before the start date.
- Access is provisioned from the Role Profile for the hired role. Nothing outside the profile is granted without a separate approved request.
- Fan-out tasks go to IT (accounts and software), Facilities (badge and desk), Legal (agreements), Payroll (setup), and the hiring manager (orientation).
- A badge is issued with the zones listed in the Role Profile. No badge is issued before Legal confirms signed agreements.
- The Joiner is complete when every fan-out task is done and the manager confirms required training is complete.

## 3. Mover

A Mover is any person changing role, department, or manager while staying employed.

**Access must shrink before it grows.** Entitlements carried by the old role and not by the new role are revoked first. Entitlements carried only by the new role are granted only after every revoke task is complete.

- The Access Audit agent compares the current Role Profile with the target Role Profile and produces three lists: **REVOKE** (old role only), **GRANT** (new role only), and **RETAINED** (both roles).
- Anything the person currently holds that appears in neither profile is flagged as **DRIFT** and is revoked unless the new manager approves an exception within 5 business days.
- Grant tasks are blocked by revoke tasks in Jira. Automation enforces the order.
- Badge zones follow the same rule. Zones are removed before new zones are added.
- The Mover is effective on the date in the HR request. Revokes are scheduled for the effective date, not earlier, so the person can finish their current work.

## 4. What a Mover keeps

A Mover is still the same person. The following are retained across any move and are never part of a revoke list:

- Identity: user ID, email address, Atlassian account, directory record
- Tenure, start date, and employee number
- Completed training and certification records
- Personal files in their own drive and their own Confluence personal space
- Entitlements present in both the old and the new Role Profile (RETAINED)

## 5. Leaver

A Leaver is any person ending employment or engagement.

- A Leaver work item must exist as soon as a last day is known. The manager is the reporter of record.
- The Knowledge Audit agent inventories what the person owns: Confluence pages and spaces, runbooks, Jira work items, Assets objects where they are the sponsor or approver. Each group is assigned a successor. Default successor is the manager.
- On the last day, the Deprovisioning Runbook runs. Order matters: badge and physical access first, then identity, then application entitlements, then shared resources.
- A Leaver is **Verified** only when every runbook step has evidence attached. A closed task without evidence is not evidence.
- The Deprovisioning agent produces a closure report listing what was removed, by whom, when, and anything still found running. Anything still running becomes a Security Operations task.

## 6. Confirmations

Dates change. The system asks rather than assumes.

- At 21 days and 7 days before a Leaver's last day, the manager is asked to confirm the date is still correct. The work item waits in **Awaiting Manager Confirmation** until they answer.
- At 5 days before a Mover's effective date, the new manager is asked to confirm the move is still happening.
- At 5 days before a Joiner's start date, the hiring manager is asked to confirm the start date and the role.

## 7. Exceptions

- Exceptions to any revoke are requested on the Mover or Leaver work item, approved by the new manager and Security Operations, and expire in 30 days.
- Emergency terminations skip confirmations. The Deprovisioning Runbook runs immediately on creation of the Leaver with the **Immediate** flag set.
- Contractors follow the same lifecycle with the end date of the engagement as the last day.
```

### A.3 EO: Role Profile: Marketing Associate

```
CURRENT Assets Role object: **PPL-nnn**. Departments: Sales & Marketing, Customer Success Innovation, Services.

This page mirrors the Role object in the People Assets schema. Assets is the source of truth for entitlements. If this page and Assets disagree, Assets wins and this page is corrected.

## Access Policies

| Access Policy | Access level | Applications | Owner |
| --- | --- | --- | --- |
| Standard Employee | User | Workday, GSuite, Jira Service Management, Loom | IT |
| Standard Creative | User | Box, Adobe Creative Cloud | IT |

## Badge zones

| Zone | Hours | Approver |
| --- | --- | --- |
| Floors 1-3 | Business hours | Facilities |
| Marketing storage | Business hours | Marketing Manager |

## Knowledge ownership

Contributes to the Marketing Content space. No runbook ownership.
```

### A.4 EO: Role Profile: Sales Advocate

```
CURRENT Assets Role object: **PPL-nnn**. Departments: Sales & Marketing, Customer Success Innovation, Services.

This page mirrors the Role object in the People Assets schema. Assets is the source of truth for entitlements. If this page and Assets disagree, Assets wins and this page is corrected.

## Access Policies

| Access Policy | Access level | Applications | Owner |
| --- | --- | --- | --- |
| Standard Employee | User | Workday, GSuite, Jira Service Management, Loom | IT |
| Standard Sales Access | User | Salesforce.com | Sales Operations |

## Badge zones

| Zone | Hours | Approver |
| --- | --- | --- |
| Floors 1-3 | Business hours | Facilities |

## Knowledge ownership

Account notes live in Salesforce. Confluence contributions limited to the Sales space.

## Known drift

Marcus Webb (mwebb) holds Legacy Archive Reader (payroll archive, rack C-10), granted during the 2024 data center migration and never removed. It is in no Role Profile.
```

### A.5 EO: Role Profile: Senior Support Engineer

```
CURRENT Assets Role object: **PPL-nnn**. Departments: Research & Development, Support, Solution Engineering.

This page mirrors the Role object in the People Assets schema. Assets is the source of truth for entitlements. If this page and Assets disagree, Assets wins and this page is corrected.

## Access Policies

| Access Policy | Access level | Applications | Owner |
| --- | --- | --- | --- |
| Standard Employee | User | Workday, GSuite, Jira Service Management, Loom | IT |
| Advanced Support Services | Admin | Jira Service Management | IT Operations |
| Standard Developer | User | Jira Align, Jira Service Management, Jira Software | Engineering |

## Badge zones

| Zone | Hours | Approver |
| --- | --- | --- |
| Floors 1-3 | 24/7 | Facilities |
| Lab 2A | Business hours | Solution Engineering Lead |

## Knowledge ownership

Expected to own customer-facing runbooks in the Engineering Support space.
```

### A.6 EO: Role Profile: Operations Manager

```
CURRENT Assets Role object: **PPL-nnn**. Department: Operations.

This page mirrors the Role object in the People Assets schema. Assets is the source of truth for entitlements. If this page and Assets disagree, Assets wins and this page is corrected.

## Access Policies

| Access Policy | Access level | Applications | Owner |
| --- | --- | --- | --- |
| Standard Employee | User | Workday, GSuite, Jira Service Management, Loom | IT |
| People Manager | Power User | Workday | HR |
| Advanced Support Services | Admin | Jira Service Management | IT Operations |

## Badge zones

| Zone | Hours | Approver |
| --- | --- | --- |
| Floors 1-3 | 24/7 | Facilities |
| Server room | 24/7 | Security Operations |
| Network closets | 24/7 | Security Operations |

## Knowledge ownership

Owns the IT Operations runbooks (label `runbook`) and the Operations on-call documentation. Successor must be named before departure.
```

### A.7 SECOPS: Leaver Deprovisioning Runbook

```
CURRENT Owner: Security Operations. Executed by Jira Automation and the Deprovisioning agent on every Leaver in the People Operations (JML) project.

Order matters. Physical access and identity go first because they gate everything else. A step is complete only when its evidence is attached to the task. A closed task with no evidence is reopened by the Deprovisioning agent.

## Preconditions

- Leaver work item exists with a confirmed last day (manager confirmed at T-21 and T-7, or the Immediate flag is set).
- Knowledge Audit is complete: every owned page, runbook, and work item has a named successor task.
- Manager has confirmed hardware return location.

## Steps

| # | Step | Owner | System | Performed by | Evidence required |
| --- | --- | --- | --- | --- | --- |
| 1 | Set Badge status to INACTIVE in Assets. Door controller follows within 5 seconds. | Security Operations | Assets (Facilities schema, Badge object) and SENTRIA Facility Console | Automation rule A7 (badge deactivation webhook) | SENTRIA confirmation reference (BA-...) posted as comment |
| 2 | Revoke all badge zones. Verify no zone remains, including decommissioned zones. | Security Operations | SENTRIA Facility Console | Security Operations analyst | Console screenshot or event feed entry |
| 3 | Disable identity: SSO account, MFA devices, and directory record set to Departed. | IT | Identity provider, directory | IT fan-out task | Directory status = Departed |
| 4 | Remove every entitlement listed on the person's Role Profile, and anything in Approved Access not on the profile (drift). | IT | Each application in the Access Policies | IT fan-out task per Access Policy | Per-application removal confirmation |
| 5 | Transfer ownership of Confluence pages, spaces, and runbooks to the successor named in the Knowledge Audit. | Successor | Confluence | Knowledge Audit tasks | Page owner changed; link to each page |
| 6 | Reassign open Jira work items and recurring automation rules the person owns. | Manager | Jira | Knowledge Audit tasks | JQL for assignee returns zero open items |
| 7 | Collect hardware: laptop, phone, badge, keys. Mark Assets hardware objects as Returned. | Facilities | Assets (IT Employee Assets schema) | Facilities fan-out task | Asset status = Returned |
| 8 | Payroll final, benefits, and Legal exit documents. | Payroll, Legal | Workday | Payroll and Legal fan-out tasks | Workday status = Terminated |
| 9 | Closure report: the Deprovisioning agent verifies steps 1-8, lists anything still running, and posts the report on the Leaver. | Security Operations | Jira, Assets, Confluence, SENTRIA | Deprovisioning agent | Closure report comment; Leaver transitioned to Verified |

## What counts as still running

- A badge with status other than INACTIVE, or any zone still assigned.
- Any Access Policy or Approved Access entry still present on the person's People object.
- Any Confluence page where the person is still the owner.
- Any open Jira work item assigned to the person, or any automation rule where they are the actor.
- Any Assets object where the person is Sponsor, Approver, or Holder.

Each finding becomes a Security Operations task linked to the Leaver with the **still-running** label.

## Immediate terminations

Skip the preconditions. Steps 1 and 3 run within 15 minutes of the Leaver being created with the Immediate flag. Steps 2 and 4-9 follow in the normal order.
```

### A.8 ITO: RB - Legacy Data Center Decommission

```
| Runbook name | Legacy Data Center Decommission |
| --- | --- |
| Document owner | Lawrence Barnes (lbarnes) |
| Service | Legacy data center, Building C basement |
| Status | DECOMMISSION IN PROGRESS |
| Last reviewed | |

## Purpose

Procedure for powering down, wiping, and physically removing the remaining racks in the legacy data center. Lawrence is the only engineer with badge access to this zone and the only one who knows the breaker map.

## Remaining work

* [x] Migrate DNS for legacy-mon-01 and legacy-mon-02 to the cloud monitoring stack
* [x] Wipe and release rack C-04 through C-09
* [ ] Wipe and release rack C-10 (still hosting the old payroll archive, waiting on Legal retention sign-off)
* [ ] Remove the Legacy data center zone from SENTRIA and retire the door controller
* [ ] Hand breaker map to Facilities

## Breaker map

Panel LP-3, basement east wall. Breakers 14 through 22 feed racks C-04 to C-12. Breaker 23 is the door controller for the zone. Do not trip 23 before SENTRIA has the zone removed or the door fails closed.

## Contacts

- Facilities: building operations desk
- Legal retention: Commercial Legal Service Desk
```

### A.9 ITO: RB - Network Closet Access Procedure

```
| Runbook name | Network Closet Access Procedure |
| --- | --- |
| Document owner | Lawrence Barnes (lbarnes) |
| Service | Campus network, HQ floors 1-3 |
| Status | ACTIVE |
| Last reviewed | |

## Purpose

How to get into a network closet after hours, what to log, and what never to touch without a change ticket.

## Procedure

1. Open an IT Operations change ticket with the closet number and the reason.
2. Badge in. Closets 1N, 2N, 3N require the Network closets zone on your badge. Only two badges currently carry it: Lawrence Barnes and the on-call phone badge.
3. Photograph the patch panel before touching anything. Attach the photo to the change ticket.
4. Make the change. Label every new cable with ticket number and date.
5. Photograph after. Attach. Close the ticket.

## Never without a change ticket

- Core switch uplinks (ports 47 and 48 on every closet switch)
- The SENTRIA door controller feed (closet 1N, port 12)
- Anything with a red label

## Escalation

If a closet switch is down and you cannot reach the on-call engineer, call Lawrence directly. His number is on the on-call page.
```
