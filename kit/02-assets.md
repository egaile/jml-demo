# 02. Assets schemas and objects

Jira Service Management Assets (Premium). Two schemas: People (people, roles, access policies) and Facilities (badges).



Build the minimum that the agents and fields need.

### 2.1 Schema: People

Create object schema **People** (key PPL). Object types and attributes:

**Access Policy**

| Attribute | Type |
| --- | --- |
| Name | Text (default) |
| Access level | Select: User, Power User, Admin |
| Applications | Text |
| Owner | Text |

Objects (7):

| Name | Access level | Applications | Owner |
| --- | --- | --- | --- |
| Standard Employee | User | Workday, GSuite, Jira Service Management, Loom | IT |
| Standard Creative | User | Box, Adobe Creative Cloud | IT |
| Standard Sales Access | User | Salesforce.com | Sales Operations |
| Advanced Support Services | Admin | Jira Service Management | IT Operations |
| Standard Developer | User | Jira Align, Jira Service Management, Jira Software | Engineering |
| People Manager | Power User | Workday | HR |
| Legacy Archive Reader | User | Payroll archive (rack C-10) | IT Operations |

(The last one exists only to be DRIFT on Marcus Webb. See 2.4.)

**Department**

Name only. Objects: Sales & Marketing, Solution Engineering, Operations, Finance.

**Role**

| Attribute | Type |
| --- | --- |
| Name | Text |
| Access Policy | Reference → Access Policy, multi-value |
| Department | Reference → Department, multi-value |
| Badge zones | Textarea (newline separated) |

Objects (4):

| Name | Access Policies | Departments | Badge zones |
| --- | --- | --- | --- |
| Marketing Associate | Standard Employee, Standard Creative | Sales & Marketing | Floors 1-3 (business hours)\nMarketing storage |
| Sales Advocate | Standard Employee, Standard Sales Access | Sales & Marketing | Floors 1-3 (business hours) |
| Senior Support Engineer | Standard Employee, Advanced Support Services, Standard Developer | Solution Engineering | Floors 1-3 (24/7)\nLab 2A |
| Operations Manager | Standard Employee, People Manager, Advanced Support Services | Operations | Floors 1-3 (24/7)\nServer room\nNetwork closets |

**People**

| Attribute | Type |
| --- | --- |
| Name | Text |
| Employee ID | Text |
| Email | Email or Text |
| Status | Select: Active, Onboarding, Deactivated |
| Department | Reference → Department |
| Job Role | Reference → Role |
| Approver | Reference → People (the manager) |
| Approved Access | Reference → Access Policy, multi-value (what they actually hold, including drift) |
| Start Date | Date |
| Type | Select: Employee Full-Time, Contractor |

Objects (5). Create the two managers first so the three characters can reference them.

| Name | Employee ID | Email | Status | Department | Job Role | Approver | Approved Access | Start Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bruce Banner | bbanner | bbanner@northwindlabs.example | Active | Sales & Marketing | Operations Manager | (none) | Standard Employee, People Manager | 2015-06-01 |
| Mitch Davis | mdavis | mdavis@northwindlabs.example | Active | Solution Engineering | Operations Manager | (none) | Standard Employee, People Manager | 2012-02-13 |
| Riley Chen | rchen | rchen@northwindlabs.example | Onboarding | Sales & Marketing | Marketing Associate | Bruce Banner | (empty) | 2026-11-03 |
| Marcus Webb | mwebb | mwebb@northwindlabs.example | Active | Sales & Marketing | Sales Advocate | Bruce Banner | Standard Employee, Standard Sales Access, Legacy Archive Reader | 2025-01-20 |
| Lawrence Barnes | lbarnes | lbarnes@northwindlabs.example | Active | Operations | Operations Manager | Mitch Davis | Standard Employee, People Manager, Advanced Support Services | 2001-03-19 |

### 2.2 Schema: Facilities

Create object schema **Facilities** (key FAC) with object type **Badge**:

| Attribute | Type |
| --- | --- |
| Name | Text (set to "BADGE-nnnn Holder Name") |
| Badge Number | Text |
| Holder | Reference → People (People schema; enable cross-schema reference) |
| Status | Select: ACTIVE, SUSPENDED, INACTIVE |
| Deactivation Ref | Text |
| Zones | Textarea, newline separated. Text attributes are single-value in Assets; do not try to make Zones multi-value text |

Objects (3):

| Name | Badge Number | Holder | Status | Zones |
| --- | --- | --- | --- | --- |
| BADGE-4471 Riley Chen | BADGE-4471 | Riley Chen | ACTIVE | Floors 1-3 (business hours)\nMarketing storage |
| BADGE-3417 Marcus Webb | BADGE-3417 | Marcus Webb | ACTIVE | Floors 1-3 (business hours) |
| BADGE-1108 Lawrence Barnes | BADGE-1108 | Lawrence Barnes | ACTIVE | Floors 1-3 (24/7)\nServer room\nNetwork closets\nLegacy data center [DECOMMISSIONED] |

The fourth zone on Lawrence's badge is the whole point of the Leaver act: a zone that outlived its reason to exist and that the Deprovisioning agent must catch.

### 2.3 Assets REST notes

- Create object types: `POST .../v1/objecttype/create` with `objectSchemaId`, `name`, `iconId` (any icon id from `GET .../v1/icon/global`).
- Create attributes: `POST .../v1/objecttypeattribute/{objectTypeId}` with `name`, `type` (0 default, 1 object reference, 7 select...), `defaultTypeId` for default types (0 text, 4 date, 6 textarea, 9 select...), `typeValue` = referenced object type id for references, `maximumCardinality: -1` for multi-value references, `options` as a comma-separated string for selects.
- Create objects: `POST .../v1/object/create` with `objectTypeId` and `attributes: [{objectTypeAttributeId, objectAttributeValues: [{value}]}]`. References take the referenced object's id in `value`.
- Read back with `GET .../v1/object/{id}` and confirm the display values before moving on.

### 2.4 Why Marcus has drift

Marcus's Approved Access includes **Legacy Archive Reader**, which is in neither the Sales Advocate nor the Senior Support Engineer profile. The Access Audit agent must flag it as DRIFT. If Assets search is not available to the agents on your site, put the same fact on the Sales Advocate Role Profile page under a "Known drift" note so the fallback path still finds it.

### 2.5 Configure the three Assets custom fields

For each of JML Employee, JML Badge, Target Role: in the field's context configuration (Jira settings → Issues → Custom fields → the field → Contexts and default value → Edit Assets object/s field configuration), set the object schema and the filter AQL:

| Field | Schema | Filter scope (AQL) | Multiple |
| --- | --- | --- | --- |
| JML Employee | People | `objectType = "People"` | No |
| JML Badge | Facilities | `objectType = "Badge"` | No |
| Target Role | People | `objectType = "Role"` | No |

Attributes displayed on the issue: Name plus Status (People), Badge Number plus Status (Badge), Name (Role). This is a UI step; the internal endpoint (`PUT /rest/servicedesk/cmdb/latest/fieldconfig/{customFieldId}`) is undocumented and its payload must be captured from the browser if scripting it.
