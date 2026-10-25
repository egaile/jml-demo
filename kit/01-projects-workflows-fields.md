# 01. Projects, statuses, workflows, fields

Build order: 01 → 02 → 03 → 05 → 04 → 06 → 07. Names are load-bearing: rules reference transitions by name, agents reference pages by title and label.

## Prerequisites and conventions

### 0.1 What your site needs before you start

- Jira Service Management **Premium** (Assets and approvals), Confluence, Rovo. You need org admin (to install apps) and site admin.
- The HR service management template available when creating a JSM project.
- Three Confluence spaces. Create them if absent: **EO** (Employee Onboarding; HR policy), **SECOPS** (Security Operations), **ITO** (IT Operations). Space keys matter only because agent knowledge scoping and CQL use them; if different keys are chosen, substitute consistently.
- An Atlassian API token for your account, exported as `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN`. Site base URL exported as `SITE` (for example `https://<newsite>.atlassian.net`).
- A badge console (the fake SENTRIA door system) deployed from this repo; see 08. Rules A2, A7 and Demo reset call it.

### 0.2 How to call the APIs

- **Jira and Confluence REST:** `curl -u "$ATLASSIAN_EMAIL:$ATLASSIAN_TOKEN" -H "Content-Type: application/json" "$SITE/rest/api/3/..."` and `"$SITE/wiki/api/v2/..."`.
- **Assets REST:** first `GET $SITE/rest/servicedeskapi/assets/workspace` to get the `workspaceId`, then `https://api.atlassian.com/jsm/assets/workspace/{workspaceId}/v1/...` with the same basic auth.
- **Atlassian MCP:** use it for searches, reading pages, creating Confluence pages, and creating or editing work items. It cannot create projects, workflows, fields, Assets schemas, Automation flows, or Rovo agents. Do not waste calls discovering otherwise.
- **No public API** exists for Jira Automation flows or Rovo Studio agents. Chapters 05 and 06 are mostly manual; they supply paste-ready prompts and instructions so the human part is copy and paste plus a few dropdown clicks.

### 0.3 Capture IDs as you go

Every phase creates objects with site-specific ids. Maintain a file `jml-ids.json` with: project id, service desk id, issue type ids, status ids, workflow ids, custom field ids, Assets workspace id, schema ids, object type ids, attribute ids, object ids, Confluence space ids and page ids. Later phases and the agent instructions need them. Never hard-code ids from these documents; any ids shown are examples of shape.

### 0.4 Naming

Names are load-bearing. Automation rules reference transitions by name, agents reference pages by title and label, and rules A3 and A8 invoke agents by name. Use the exact names in this document.




### 1.1 Project

Create a JSM project from the **HR service management** template, company-managed:

- Name: **People Operations**
- Key: **JML**
- Lead: you

Use `POST /rest/api/3/project` with `projectTypeKey: "service_desk"` and the HR template key (`com.atlassian.servicedesk:simplified-hr-service-desk` or whatever the site reports under `GET /rest/servicedeskapi/servicedesk` templates; if the REST template key is rejected, create the project in the UI from the HR template, which takes one minute, and continue). Record project id and service desk id.

The HR template provides the three work types we use as the lifecycle events plus Task. Confirm they exist in the project (`GET /rest/api/3/issue/createmeta/JML/issuetypes`) and record their ids:

| Work type | Lifecycle event |
| --- | --- |
| Employee onboarding | Joiner |
| HR request (with approval) | Mover |
| Employee offboarding | Leaver |
| Task | Fan-out work for IT, Facilities, Legal, Payroll, Security, Manager |

If the template on your site names them differently, rename the types to these names rather than changing every reference in this document.

### 1.2 Statuses

Create any of these that do not already exist (`POST /rest/api/3/statuses`, scope global), with the category shown. Record all ids, including the built-ins.

| Status | Category | Used by |
| --- | --- | --- |
| Open | To Do | all |
| Pre-Day-One | In Progress | Joiner |
| Day One | In Progress | Joiner |
| Awaiting approval | In Progress | Mover |
| Revoking | In Progress | Mover |
| Granting | In Progress | Mover |
| Declined | Done | Mover |
| Awaiting Manager Confirmation | In Progress | Leaver |
| Knowledge Audit | In Progress | Leaver |
| Deprovisioning | In Progress | Leaver |
| Verified | In Progress | Leaver |
| Closed | Done | all |
| Canceled | Done | Joiner, Leaver |

### 1.3 Workflows

Create three workflows with `POST /rest/api/3/workflows/create`. Shape that works: each status entry needs a client-generated UUID `statusReference`, the existing `id` from 1.2, `name`, and `statusCategory`; each transition has `name`, `type` (`INITIAL` for Create, `DIRECTED` otherwise), `toStatusReference`, and `links: [{fromStatusReference, fromPort: 0, toPort: 1}]` for every allowed source status. Give the workflow a `description`; the API requires it.

**JML: Joiner**

| Transition | From | To |
| --- | --- | --- |
| Create | (initial) | Open |
| Fan out | Open | Pre-Day-One |
| Day one | Pre-Day-One | Day One |
| Training confirmed | Day One | Closed |
| Cancel | Open, Pre-Day-One | Canceled |

**JML: Mover**

| Transition | From | To |
| --- | --- | --- |
| Create | (initial) | Open |
| Submit for approval | Open | Awaiting approval |
| Approve | Awaiting approval | Revoking |
| Decline | Awaiting approval | Declined |
| Revokes complete | Revoking | Granting |
| Grants complete | Granting | Closed |
| Reopen | Closed, Declined | Open |

**JML: Leaver**

| Transition | From | To |
| --- | --- | --- |
| Create | (initial) | Open |
| Request confirmation | Open, Knowledge Audit | Awaiting Manager Confirmation |
| Manager confirmed | Open, Awaiting Manager Confirmation | Knowledge Audit |
| Start deprovisioning | Open, Awaiting Manager Confirmation, Knowledge Audit | Deprovisioning |
| Verify | Deprovisioning | Verified |
| Findings open | Verified | Deprovisioning |
| Close | Verified | Closed |
| Cancel | Open, Awaiting Manager Confirmation, Knowledge Audit | Canceled |

Tasks keep the project's default workflow (Open, Pending, Work in progress, Reopened, Done). Rules A4 and A8 trigger on Task transitioned to **Done**; confirm the default workflow's done status is named Done, or adjust those rule triggers.

### 1.4 Map the workflows to the project

`POST /rest/api/3/workflowscheme/update` on the project's scheme with `statusMappingsByWorkflows: [{oldWorkflowId, newWorkflowId, statusMappings: [{oldStatusId, newStatusId}]}]` for each issue type being remapped, plus `statusMappingsByIssueTypeOverride` where the API asks for it, and a `description`. Map:

- Employee onboarding → JML: Joiner
- HR request (with approval) → JML: Mover
- Employee offboarding → JML: Leaver

The template's existing items (none yet) map Open → Open. If the API rejects the payload, do it in Project settings → Workflows in the UI; it is three dropdowns.

### 1.5 Custom fields

Create these (`POST /rest/api/3/field`, then add to the JML screens via `POST /rest/api/3/screens/{screenId}/tabs/{tabId}/fields` for every screen in the project's screen scheme, or add them in the UI under Project settings → Work types for each type). Record every id.

| Field | Type | Options or notes | Used on |
| --- | --- | --- | --- |
| Badge number | Text (single line) | e.g. BADGE-1108. Plain text copy of the Assets badge, used in web requests | Joiner, Mover, Leaver |
| Last day | Date | | Leaver |
| Effective date | Date | | Mover |
| Lifecycle phase | Select (single) | PRE-DAY-ONE, REVOKE, GRANT, DEPROVISION, STILL-RUNNING | Task |
| Fan-out team | Select (single) | IT, Facilities, Legal, Payroll, Security, Recruiting, Manager | Task |
| Evidence | URL | Proof a runbook step completed | Task |
| Immediate termination | Checkbox | one option: Yes | Leaver |
| Knowledge audit status | Select (single) | Not started, In progress, Complete | Leaver |
| Deprovisioning status | Select (single) | Not started, In progress, Verified, Findings open | Leaver |
| JML Employee | Assets object | People schema, object type People (see 02) | all three |
| JML Badge | Assets object | Facilities schema, object type Badge | Joiner, Leaver |
| Target Role | Assets object | People schema, object type Role | Mover |
| Start date | Date | Reuse the HR template's field if it exists, else create | Joiner |
| Manager | User picker (multi) | Reuse the template's field if it exists, else create | all three |
| Employee ID | Text | Reuse if exists. Values are first initial plus last name, lowercase | all three |
| Role | Text | Reuse if exists. Must match a Role Profile page title suffix | all three |
| Department | Select | Reuse if exists | all three |

The three Assets fields need their schema and AQL configured after chapter 02 (see 2.5).

### 1.6 Link types

Confirm the site has **Relates** (relates to) and **Blocks** (blocks / is blocked by). Rules use only these two. Do not rely on "is child of"; the fan-out uses "relates to".

### 1.7 Second project: IT Fulfilment (ITF)

IT and Security fan-out tasks live in their own project so they can carry operational clocks (see 07) and so the
picture is cross-project, the way real customers run it. Manager, Payroll, Legal and Facilities tasks stay in JML.

- Create a **Jira Software, company-managed** project, name **IT Fulfilment**, key **ITF** (template: basic software development / Scrum or Kanban, either works).
- Its workflow needs a done status named **Done** (the simplified workflow has To Do, In Progress, In Review, Done). Note there is no "Mark as done" transition here; the transition is "Done".
- Add **Lifecycle phase**, **Fan-out team** and **Evidence** to the ITF screens (Project settings → Work types → Task).
- The automation rule actor (you, or Automation for Jira) needs **Create, Edit, Delete and Link** work items in ITF. Delete matters for Demo reset.
- Links between ITF and JML ("relates to", "is blocked by") work across projects; nothing else changes.

