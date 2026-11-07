"""Phase 2: Assets. Finds or creates the People and Facilities schemas, their object types and attributes, the demo objects,
then configures the three Assets custom fields. Works on a site that already has Atlassian's People/Facilities template
schemas (it adds what is missing) and on an empty Assets workspace (it builds them)."""
from .api import ProvisionError

STATUS_TYPES = {"Active": 1, "Onboarding": 2, "Deactivated": 0}          # Assets status categories: 0 inactive, 1 active, 2 pending
DEFAULT_TYPE = {"text": 0, "date": 4, "email": 8, "textarea": 9, "select": 10}
SCHEMAS = {"People": "PPL", "Facilities": "FAC"}
# attribute specs per object type: (name, kind, extra, multi, aliases)
ATTRS = {
 ("People", "Access Policy"): [("Access level", "select", "User,Power User,Admin", False, ["Access Allowed"]), ("Applications", "text", None, False, []), ("Owner", "text", None, False, [])],
 ("People", "Department"): [],
 ("People", "Role"): [("Access Policy", "ref", "People:Access Policy", True, []), ("Department", "ref", "People:Department", True, []), ("Badge zones", "textarea", None, False, [])],
 ("People", "People"): [("Employee ID", "text", None, False, []), ("Email", "email", None, False, []), ("Status", "status", None, False, []),
                        ("Department", "ref", "People:Department", False, []), ("Job Role", "ref", "People:Role", False, []), ("Approver", "ref", "People:People", False, []),
                        ("Approved Access", "ref", "People:Access Policy", True, []), ("Start Date", "date", None, False, []), ("Type", "select", "Employee Full-Time,Contractor", False, [])],
 ("Facilities", "Badge"): [("Badge Number", "text", None, False, []), ("Holder", "ref", "People:People", False, []), ("Status", "select", "ACTIVE,SUSPENDED,INACTIVE", False, []),
                           ("Deactivation Ref", "text", None, False, []), ("Zones", "textarea", None, False, [])],
}
POLICIES = [("Standard Employee", "User", "Workday, GSuite, Jira Service Management, Loom", "IT"), ("Standard Creative", "User", "Box, Adobe Creative Cloud", "IT"),
            ("Standard Sales Access", "User", "Salesforce.com", "Sales Operations"), ("Advanced Support Services", "Admin", "Jira Service Management", "IT Operations"),
            ("Standard Developer", "User", "Jira Align, Jira Service Management, Jira Software", "Engineering"), ("People Manager", "Power User", "Workday", "HR"),
            ("Legacy Archive Reader", "User", "Payroll archive (rack C-10)", "IT Operations")]
DEPARTMENTS = ["Sales & Marketing", "Solution Engineering", "Operations", "Finance"]
ROLES = [("Marketing Associate", ["Standard Employee", "Standard Creative"], ["Sales & Marketing"], "Floors 1-3 (business hours)\nMarketing storage"),
         ("Sales Advocate", ["Standard Employee", "Standard Sales Access"], ["Sales & Marketing"], "Floors 1-3 (business hours)"),
         ("Senior Support Engineer", ["Standard Employee", "Advanced Support Services", "Standard Developer"], ["Solution Engineering"], "Floors 1-3 (24/7)\nLab 2A"),
         ("Operations Manager", ["Standard Employee", "People Manager", "Advanced Support Services"], ["Operations"], "Floors 1-3 (24/7)\nServer room\nNetwork closets")]
PEOPLE = [("Bruce Banner", "bbanner", "Active", "Sales & Marketing", "Operations Manager", None, ["Standard Employee", "People Manager"], "2015-06-01"),
          ("Mitch Davis", "mdavis", "Active", "Solution Engineering", "Operations Manager", None, ["Standard Employee", "People Manager"], "2012-02-13"),
          ("Riley Chen", "rchen", "Onboarding", "Sales & Marketing", "Marketing Associate", "Bruce Banner", [], "2026-11-03"),
          ("Marcus Webb", "mwebb", "Active", "Sales & Marketing", "Sales Advocate", "Bruce Banner", ["Standard Employee", "Standard Sales Access", "Legacy Archive Reader"], "2025-01-20"),
          ("Lawrence Barnes", "lbarnes", "Active", "Operations", "Operations Manager", "Mitch Davis", ["Standard Employee", "People Manager", "Advanced Support Services"], "2001-03-19")]
BADGES = [("BADGE-4471", "Riley Chen", "Floors 1-3 (business hours)\nMarketing storage"), ("BADGE-3417", "Marcus Webb", "Floors 1-3 (business hours)"),
          ("BADGE-1108", "Lawrence Barnes", "Floors 1-3 (24/7)\nServer room\nNetwork closets\nLegacy data center [DECOMMISSIONED]")]
FIELD_CONFIG = {"JML Employee": ("People", 'objectType = "People"', ["Name"], ["Name", "Status"]),
                "JML Badge": ("Facilities", 'objectType = "Badge"', ["Name", "Badge Number"], ["Badge Number", "Status"]),
                "Target Role": ("People", 'objectType = "Role"', ["Name"], ["Name"])}


class Assets:
    def __init__(self, ctx):
        self.ctx, self.site = ctx, ctx.site; self.A = ctx.state.sec("assets")
        self.A["workspaceId"] = self.site.workspace()
        self.schemas = self.A.setdefault("schemas", {}); self.types = self.A.setdefault("objectTypes", {}); self.attrs = self.A.setdefault("attrs", {})
        self._attr_cache = {}; self._reftype = None; self._icon = None; self._status_types = None

    # ---- schemas and types
    def ensure_schema(self, name):
        s, r = self.site.aget("/objectschema/list"); hit = next((x for x in r.get("values", []) if x["name"] == name), None) if s == 200 else None
        if hit: self.schemas[name] = int(hit["id"]); return hit["id"]
        res = self.ctx.do(f"create Assets schema {name} ({SCHEMAS[name]})", self.site.apost, "/objectschema/create", {"name": name, "objectSchemaKey": SCHEMAS[name], "description": "JML demo"})
        if not res: return None
        s, x = res; self.ctx.need(s in (200, 201), f"schema {name}: {s} {str(x)[:300]}"); self.schemas[name] = int(x["id"]); return x["id"]

    def icon(self):
        if not self._icon:
            s, r = self.site.aget("/icon/global"); self._icon = next((x["id"] for x in r if x["name"] in ("People", "Person", "User")), r[0]["id"])
        return self._icon

    def ensure_type(self, schema, name):
        sid = self.schemas.get(schema)
        if not sid: self.ctx.plan(f"create object type {name} in {schema} (after the schema exists)"); return None
        s, r = self.site.aget(f"/objectschema/{sid}/objecttypes/flat"); hit = next((x for x in r if x["name"] == name), None) if s == 200 else None
        if hit: self.types[name] = int(hit["id"]); return hit["id"]
        res = self.ctx.do(f"create object type {schema} / {name}", self.site.apost, "/objecttype/create", {"name": name, "iconId": self.icon(), "objectSchemaId": str(sid)})
        if not res: return None
        s, x = res; self.ctx.need(s in (200, 201), f"object type {name}: {s} {str(x)[:300]}"); self.types[name] = int(x["id"]); return x["id"]

    # ---- attributes
    def attributes(self, type_id, refresh=False):
        if refresh or type_id not in self._attr_cache:
            s, r = self.site.aget(f"/objecttype/{type_id}/attributes"); self._attr_cache[type_id] = r if s == 200 else []
        return self._attr_cache[type_id]
    def attr(self, type_id, name, aliases=()):
        for n in (name, *aliases):
            a = next((a for a in self.attributes(type_id) if a["name"] == n), None)
            if a: return a
        return None
    def reftype(self):
        if not self._reftype:
            s, r = self.site.aget("/config/referencetype"); self._reftype = next((x["id"] for x in r if x["name"] == "Reference"), r[0]["id"])
        return self._reftype
    def status_types(self):
        """Assets status types: the global ones plus the People schema's own (Onboarding and Deactivated live there)."""
        if self._status_types is None:
            sid = self.schemas.get("People"); self._status_types = {}
            for q in ("", f"?objectSchemaId={sid}" if sid else None):
                if q is None: continue
                s, r = self.site.aget("/config/statustype" + q)
                if s == 200: self._status_types.update({x["name"]: x["id"] for x in r})
            for name, catg in STATUS_TYPES.items():
                if name in self._status_types: continue
                body = {"name": name, "category": catg, "description": "JML demo"}
                if sid: body["objectSchemaId"] = str(sid)
                res = self.ctx.do(f"create Assets status type {name} (People schema)", self.site.apost, "/config/statustype", body)
                if res and res[0] in (200, 201): self._status_types[name] = res[1]["id"]
        return self._status_types

    def ensure_attr(self, type_name, spec):
        name, kind, extra, multi, aliases = spec; tid = self.types.get(type_name)
        if not tid: return
        have = self.attr(tid, name, aliases)
        if have and kind == "ref":
            want = self.types.get(extra.split(":")[1])
            if want and str(have.get("referenceObjectTypeId")) != str(want):
                newname = "Approved Software" if name == "Approved Access" else f"{name} (legacy)"
                body = {"name": newname, "type": 1, "typeValue": str(have["referenceObjectTypeId"]), "maximumCardinality": have.get("maximumCardinality", 1),
                        "additionalValue": str((have.get("referenceType") or {}).get("id", self.reftype()))}
                res = self.ctx.do(f"{type_name}.{name} points at object type {have.get('referenceObjectTypeId')}, not {extra}: rename it to {newname}", self.site.aput, f"/objecttypeattribute/{tid}/{have['id']}", body)
                if res and res[0] != 200: self.ctx.warn(f"rename {name} failed: {res[0]} {str(res[1])[:200]}")
                have = None; self.attributes(tid, refresh=True)
        if have: self.attrs[f"{type_name}:{name}"] = str(have["id"]); return
        if kind == "ref":
            want = self.types.get(extra.split(":")[1])
            if not want: self.ctx.plan(f"create attribute {type_name}.{name} -> {extra} (after that type exists)"); return
            body = {"name": name, "type": 1, "typeValue": str(want), "additionalValue": self.reftype(), "maximumCardinality": -1 if multi else 1}
        elif kind == "status":
            body = {"name": name, "type": 7, "typeValue": ",".join(str(v) for v in self.status_types().values())}
        else:
            body = {"name": name, "type": 0, "defaultTypeId": DEFAULT_TYPE[kind]}
            if kind == "select": body["options"] = extra
        res = self.ctx.do(f"create attribute {type_name}.{name} ({kind}{' multi' if multi else ''})", self.site.apost, f"/objecttypeattribute/{tid}", body)
        if not res: return
        s, x = res
        if s not in (200, 201) and kind == "status":
            body.pop("typeValue"); s, x = self.site.apost(f"/objecttypeattribute/{tid}", body)
        self.ctx.need(s in (200, 201), f"attribute {type_name}.{name}: {s} {str(x)[:300]}")
        self.attrs[f"{type_name}:{name}"] = str(x["id"]); self.attributes(tid, refresh=True)

    # ---- objects
    def find(self, type_id, name):
        hits = [o for o in self.site.aql(f'objectTypeId = {type_id} AND Name = "{name}"') if o.get("label") == name or o.get("name") == name]
        return hits[0] if hits else None

    def value(self, a, v):
        """Attribute values by name: references resolve to object ids, status to status type ids, the rest are strings."""
        if a["type"] == 1:
            o = self.find(a["referenceObjectTypeId"], v)
            if not o:
                res = self.ctx.do(f"create referenced object {v} in type {a['referenceObjectTypeId']}", self.site.apost, "/object/create",
                                  {"objectTypeId": str(a["referenceObjectTypeId"]), "attributes": [{"objectTypeAttributeId": str(self.name_attr(a["referenceObjectTypeId"])), "objectAttributeValues": [{"value": v}]}]})
                if not res: return None
                self.ctx.need(res[0] in (200, 201), f"object {v}: {res[0]} {str(res[1])[:200]}"); return str(res[1]["id"])
            return str(o["id"])
        if a["type"] == 7: return str(self.status_types().get(v, v))
        return str(v)
    def name_attr(self, type_id): return self.attr(type_id, "Name")["id"]

    def ensure_object(self, type_name, name, values):
        """Create or update the object called `name` so its attributes equal `values` ({attr name: value or [values]})."""
        tid = self.types.get(type_name)
        if not tid: self.ctx.plan(f"create {type_name} object {name} (after the type exists)"); return None
        attrs = [{"objectTypeAttributeId": str(self.name_attr(tid)), "objectAttributeValues": [{"value": name}]}]
        for an, v in values.items():
            a = self.attr(tid, an, {"Access level": ["Access Allowed"]}.get(an, ()))
            if not a: self.ctx.warn(f"{type_name} has no attribute {an}; skipped on {name}"); continue
            vals = v if isinstance(v, list) else [v]
            resolved = [self.value(a, x) for x in vals]
            if any(x is None for x in resolved): continue
            attrs.append({"objectTypeAttributeId": str(a["id"]), "objectAttributeValues": [{"value": x} for x in resolved]})
        o = self.find(tid, name)
        if o:
            res = self.ctx.do(f"update {type_name} {o['objectKey']} {name}", self.site.aput, f"/object/{o['id']}", {"attributes": attrs})
            if res and res[0] != 200: self.ctx.warn(f"update {name}: {res[0]} {str(res[1])[:200]}")
            return o
        res = self.ctx.do(f"create {type_name} object {name}", self.site.apost, "/object/create", {"objectTypeId": str(tid), "attributes": attrs})
        if not res: return None
        s, x = res; self.ctx.need(s in (200, 201), f"object {name}: {s} {str(x)[:300]}"); return x


def run(ctx):
    a = Assets(ctx); A = a.A
    for schema in SCHEMAS: a.ensure_schema(schema)
    for (schema, tname) in ATTRS: a.ensure_type(schema, tname)
    for (schema, tname), specs in ATTRS.items():
        for spec in specs: a.ensure_attr(tname, spec)
    ctx.state.save()
    if not all(t in a.types for _, t in ATTRS): ctx.plan("create the demo objects (after the object types exist)"); return
    pol, dep, roles, people, badges = {}, {}, {}, {}, {}
    for name, lvl, apps, owner in POLICIES:
        v = {"Access level": lvl, "Applications": apps, "Owner": owner}
        if a.attr(a.types["Access Policy"], "Status") and a.attr(a.types["Access Policy"], "Status")["type"] == 7: v["Status"] = "Active"
        o = a.ensure_object("Access Policy", name, v); pol[name] = int(o["id"]) if o else None
    for name in DEPARTMENTS:
        o = a.ensure_object("Department", name, {}); dep[name] = int(o["id"]) if o else None
    for name, pols, deps, zones in ROLES:
        o = a.ensure_object("Role", name, {"Access Policy": pols, "Department": deps, "Badge zones": zones}); roles[name] = int(o["id"]) if o else None
        A.setdefault("roleKeys", {})[name] = o["objectKey"] if o else None
    for name, emp, status, d, role, approver, access, start in PEOPLE:
        v = {"Employee ID": emp, "Email": f"{emp}@northwindlabs.example", "Status": status, "Department": d, "Job Role": role, "Approved Access": access, "Start Date": start, "Type": "Employee Full-Time"}
        if approver: v["Approver"] = approver
        o = a.ensure_object("People", name, v); people[name] = int(o["id"]) if o else None
    for num, holder, zones in BADGES:
        o = a.ensure_object("Badge", f"{num} {holder}", {"Badge Number": num, "Holder": holder, "Status": "ACTIVE", "Deactivation Ref": [], "Zones": zones}); badges[num] = int(o["id"]) if o else None
    A.update(accessPolicies=pol, departments=dep, roles=roles, people=people, badges=badges, peopleStatusTypes=a.status_types()); ctx.state.save()
    ctx.say(f"objects: {len(pol)} policies, {len(dep)} departments, {len(roles)} roles, {len(people)} people, {len(badges)} badges")
    configure_fields(ctx, a)


def configure_fields(ctx, a):
    """Point the three Assets custom fields at their schema and object type (internal cmdb fieldconfig endpoint)."""
    F = ctx.S.get("fields", {}); ws = ctx.site.workspace()
    for fname, (schema, aql, search, show) in FIELD_CONFIG.items():
        cid = F.get(fname + " contextId"); sid = a.schemas.get(schema)
        if not (cid and sid): ctx.plan(f"configure Assets field {fname} (after the field and schema exist)"); continue
        s, cur = ctx.site.get(f"/rest/servicedesk/cmdb/latest/fieldconfig/{cid}")
        if s == 200 and str(cur.get("objectSchemaId")) == str(sid) and cur.get("objectFilterQuery") == aql: ctx.say(f"Assets field {fname} configured"); continue
        body = {"workspaceId": ws, "objectSchemaId": str(sid), "objectSchemaName": schema, "objectFilterQuery": aql, "attributesIncludedInAutoCompleteSearch": search,
                "attributesDisplayedOnIssue": show, "multiple": False, "shouldSetDefaultValuesFromEmptySearch": False, "assignStrict": False, "attributesLimit": 50}
        res = ctx.do(f"configure Assets field {fname}: schema {schema}, filter {aql}", ctx.site.put, f"/rest/servicedesk/cmdb/latest/fieldconfig/{cid}", body)
        if res and res[0] != 200: ctx.warn(f"Assets field {fname}: {res[0]} {str(res[1])[:200]}; set it in the UI (Custom fields -> {fname} -> Contexts -> Edit Assets object/s field configuration)")
