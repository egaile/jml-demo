"""Site-agnostic REST client (Jira, Confluence, Assets, the Automation gateway, Time to SLA) and the per-site state file.
Standard library only."""
import base64, json, pathlib, ssl, urllib.error, urllib.parse, urllib.request

CTX = ssl.create_default_context()
CTX.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)   # Python 3.13 rejects some valid chains (Time to SLA's) as "strict"


class ProvisionError(Exception):
    pass


class Site:
    def __init__(self, url, email, token, tts_base="", tts_token=""):
        self.url = url.rstrip("/"); self.email = email
        self.tts_base = (tts_base or "").rstrip("/"); self.tts_token = tts_token or ""
        self._auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
        self._ws = self._cloud = self._me = None

    def call(self, method, path, body=None, headers=None, auth=None, raw=False):
        url = path if path.startswith("http") else self.url + path
        h = {"Authorization": auth or self._auth, "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
        if headers: h.update(headers)
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, context=CTX) as r:
                t = r.read().decode()
                return (r.status, t) if raw else (r.status, json.loads(t) if t else None)
        except urllib.error.HTTPError as e:
            t = e.read().decode()
            try: t = json.loads(t)
            except Exception: pass
            return e.code, t

    def get(self, p, **k): return self.call("GET", p, **k)
    def post(self, p, b=None, **k): return self.call("POST", p, b, **k)
    def put(self, p, b=None, **k): return self.call("PUT", p, b, **k)
    def delete(self, p, **k): return self.call("DELETE", p, headers={"Content-Type": "application/json"}, **k)
    def patch(self, p, b=None, **k): return self.call("PATCH", p, b, headers={"Content-Type": "application/json"}, **k)

    # ---- identity
    def cloud_id(self):
        if not self._cloud:
            s, r = self.get("/_edge/tenant_info")
            if s != 200: raise ProvisionError(f"cannot read tenant info from {self.url}: {s} {r}")
            self._cloud = r["cloudId"]
        return self._cloud
    def me(self):
        if not self._me:
            s, r = self.get("/rest/api/3/myself")
            if s != 200: raise ProvisionError(f"authentication failed against {self.url}: {s} {str(r)[:200]}")
            self._me = r
        return self._me

    # ---- Assets
    def workspace(self):
        if not self._ws:
            s, r = self.get("/rest/servicedeskapi/assets/workspace")
            if s != 200 or not r.get("values"): raise ProvisionError(f"no Assets workspace (JSM Premium needed): {s} {str(r)[:200]}")
            self._ws = r["values"][0]["workspaceId"]
        return self._ws
    def assets_base(self): return f"https://api.atlassian.com/jsm/assets/workspace/{self.workspace()}/v1"
    def aget(self, p): return self.get(self.assets_base() + p)
    def apost(self, p, b=None): return self.post(self.assets_base() + p, b)
    def aput(self, p, b=None): return self.put(self.assets_base() + p, b)
    def aql(self, query, attrs=False):
        s, r = self.apost("/object/aql?maxResults=200", {"qlQuery": query, "includeAttributes": attrs})
        if s != 200: raise ProvisionError(f"AQL failed: {query}: {s} {str(r)[:200]}")
        return r.get("values", [])

    # ---- Automation gateway (internal API, basic auth works)
    def auto_base(self): return f"/gateway/api/automation/internal-api/jira/{self.cloud_id()}/pro/rest"

    # ---- Time to SLA (Appfire) regional API
    def tts(self, method, path, body=None):
        if not (self.tts_base and self.tts_token): return 0, "no Time to SLA token"
        return self.call(method, self.tts_base + path, body, auth=f"Bearer {self.tts_token}")

    # ---- Jira helpers
    def search(self, jql, fields="summary,status,issuetype", max_results=100):
        q = urllib.parse.urlencode({"jql": jql, "fields": fields, "maxResults": max_results})
        s, r = self.get("/rest/api/3/search/jql?" + q)
        if s != 200: raise ProvisionError(f"search failed: {jql}: {s} {str(r)[:200]}")
        return r.get("issues", [])
    def transitions(self, key):
        s, r = self.get(f"/rest/api/3/issue/{key}/transitions")
        return {t["name"]: t["id"] for t in r.get("transitions", [])} if s == 200 else {}
    def transition(self, key, name):
        tid = self.transitions(key).get(name)
        if not tid: return 0, f"no transition {name!r} on {key}"
        return self.post(f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": tid}})


class State:
    """One JSON file per site holding every id the build created or found."""
    def __init__(self, path):
        self.path = pathlib.Path(path); self.d = json.loads(self.path.read_text()) if self.path.exists() else {}
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.d, indent=1, sort_keys=True))
    def sec(self, section):
        return self.d.setdefault(section, {})
    def set(self, section, **kw):
        self.sec(section).update(kw); self.save()


class Ctx:
    """What every phase gets: the site, the state, the edition and the apply/plan switch."""
    def __init__(self, site, state, edition, apply, opts):
        self.site, self.state, self.edition, self.apply, self.opts = site, state, edition, apply, opts
        self.notes = {}         # facts the manual guide prints (key -> value)
        self.warnings = []
    def say(self, msg): print("  " + msg)
    def plan(self, msg): print(("  " if self.apply else "  [plan] ") + msg)
    def warn(self, msg): self.warnings.append(msg); print("  WARNING: " + msg)
    def note(self, phase, key, value=True): self.notes[f"{phase}.{key}"] = value
    def do(self, msg, fn, *a, **k):
        """Print the planned write; run it only with --apply. Returns fn's result or None."""
        self.plan(msg)
        return fn(*a, **k) if self.apply else None
    def need(self, cond, msg):
        if not cond: raise ProvisionError(msg)
    @property
    def S(self): return self.state.d
