"""Phase 3: Confluence spaces EO, SECOPS, ITO and the nine pages, verbatim from the kit's chapter 03, with labels."""
import html, re, urllib.parse

SPACES = {"EO": "Employee Onboarding", "SECOPS": "Security Operations", "ITO": "IT Operations"}
LABELS = {"Joiner, Mover, Leaver (JML) Program": ["jml"], "JML Policy": ["jml-policy", "jml"],
          "Role Profile: Marketing Associate": ["role-profile", "jml"], "Role Profile: Sales Advocate": ["role-profile", "jml"],
          "Role Profile: Senior Support Engineer": ["role-profile", "jml"], "Role Profile: Operations Manager": ["role-profile", "jml"],
          "Leaver Deprovisioning Runbook": ["runbook", "jml", "deprovisioning"],
          "RB - Legacy Data Center Decommission": ["runbook", "owner-lbarnes", "legacy-data-center"],
          "RB - Network Closet Access Procedure": ["runbook", "owner-lbarnes", "campus-network"]}
PROGRAM = "Joiner, Mover, Leaver (JML) Program"


def bodies(kit_dir):
    """{title: (space, markdown)} from the '### A.n SPACE: Title' fenced blocks of kit/03-confluence.md."""
    txt = (kit_dir / "03-confluence.md").read_text(); out = {}
    for m in re.finditer(r"^### A\.\d+ (\w+): (.+?)\n\n```\n(.*?)\n```", txt, re.S | re.M):
        out[m.group(2).strip()] = (m.group(1), m.group(3))
    return out


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def md2storage(md):
    lines = md.split("\n"); i = 0; out = []; buf = []
    def flush():
        if buf: out.append("<p>" + " ".join(inline(x) for x in buf) + "</p>"); buf.clear()
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == "(child pages list)":
            flush(); out.append('<ac:structured-macro ac:name="children" ac:schema-version="2"><ac:parameter ac:name="all">true</ac:parameter></ac:structured-macro>'); i += 1; continue
        if ln.startswith("|"):
            flush(); rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells): rows.append(cells)
                i += 1
            t = ["<table><tbody>"]
            for ri, r in enumerate(rows):
                tag = "th" if ri == 0 else "td"; t.append("<tr>" + "".join(f"<{tag}><p>{inline(c)}</p></{tag}>" for c in r) + "</tr>")
            t.append("</tbody></table>"); out.append("".join(t)); continue
        m = re.match(r"^(#{1,3}) (.+)$", ln)
        if m: flush(); out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>"); i += 1; continue
        if re.match(r"^\* \[( |x)\] ", ln):
            flush(); t = ["<ac:task-list>"]
            while i < len(lines) and re.match(r"^\* \[( |x)\] ", lines[i]):
                m = re.match(r"^\* \[( |x)\] (.*)$", lines[i]); st = "complete" if m.group(1) == "x" else "incomplete"
                t.append(f"<ac:task><ac:task-status>{st}</ac:task-status><ac:task-body>{inline(m.group(2))}</ac:task-body></ac:task>"); i += 1
            t.append("</ac:task-list>"); out.append("".join(t)); continue
        if re.match(r"^- ", ln):
            flush(); t = ["<ul>"]
            while i < len(lines) and re.match(r"^- ", lines[i]): t.append(f"<li><p>{inline(lines[i][2:])}</p></li>"); i += 1
            t.append("</ul>"); out.append("".join(t)); continue
        if re.match(r"^\d+\. ", ln):
            flush(); t = ["<ol>"]
            while i < len(lines) and re.match(r"^\d+\. ", lines[i]): t.append(f"<li><p>{inline(re.sub(r'^\d+\. ', '', lines[i]))}</p></li>"); i += 1
            t.append("</ol>"); out.append("".join(t)); continue
        if ln.strip() == "": flush(); i += 1; continue
        buf.append(ln); i += 1
    flush(); return "".join(out)


def ensure_spaces(ctx):
    site = ctx.site; sp = ctx.state.sec("confluence").setdefault("spaces", {})
    s, r = site.get("/wiki/api/v2/spaces?keys=" + ",".join(SPACES) + "&limit=10")
    ctx.need(s == 200, f"Confluence not reachable at {site.url}/wiki: {s} {str(r)[:200]}")
    have = {x["key"]: x for x in r.get("results", [])}
    for key, name in SPACES.items():
        if key in have: sp[key] = {"id": have[key]["id"], "homepageId": have[key].get("homepageId")}; ctx.say(f"space {key} exists"); continue
        res = ctx.do(f"create Confluence space {key} ({name})", site.post, "/wiki/api/v2/spaces", {"name": name, "key": key})
        if not res: continue
        s, x = res
        if s not in (200, 201):
            s, x = site.post("/wiki/rest/api/space", {"key": key, "name": name})
        ctx.need(s in (200, 201), f"space {key}: {s} {str(x)[:300]}")
        s, y = site.get(f"/wiki/api/v2/spaces?keys={key}"); y = y["results"][0]
        sp[key] = {"id": y["id"], "homepageId": y.get("homepageId")}
    ctx.state.save()


def find_page(site, space_id, title):
    s, r = site.get(f"/wiki/api/v2/spaces/{space_id}/pages?title={urllib.parse.quote(title)}&limit=5")
    return next((p for p in r.get("results", []) if p["title"] == title), None) if s == 200 else None


def run(ctx):
    ensure_spaces(ctx)
    site, conf = ctx.site, ctx.state.sec("confluence"); pages = conf.setdefault("pages", {}); sp = conf["spaces"]
    role_keys = ctx.S.get("assets", {}).get("roleKeys", {})
    order = [PROGRAM] + [t for t in LABELS if t != PROGRAM]
    src = bodies(ctx.opts["kit_dir"])
    for title in order:
        space, md = src[title]
        if space not in sp: ctx.plan(f"create page {space}/{title} (after the space exists)"); continue
        if title.startswith("Role Profile: "):
            key = role_keys.get(title.split(": ", 1)[1])
            if key: md = md.replace("PPL-nnn", key)
            else: ctx.warn(f"{title}: Role object key unknown yet; page keeps the PPL-nnn placeholder")
        existing = find_page(site, sp[space]["id"], title)
        if existing: pid = existing["id"]; ctx.say(f"page {space}/{title} exists ({pid})")
        else:
            parent = pages.get(PROGRAM, {}).get("id") if (space == "EO" and title != PROGRAM) else sp[space].get("homepageId")
            body = {"spaceId": str(sp[space]["id"]), "status": "current", "title": title, "body": {"representation": "storage", "value": md2storage(md)}}
            if parent: body["parentId"] = str(parent)
            res = ctx.do(f"create page {space}/{title}", site.post, "/wiki/api/v2/pages", body)
            if not res: continue
            s, x = res; ctx.need(s in (200, 201), f"page {title}: {s} {str(x)[:300]}"); pid = x["id"]
        s, lr = site.get(f"/wiki/rest/api/content/{pid}/label"); have = {l["name"] for l in lr.get("results", [])} if s == 200 else set()
        missing = [l for l in LABELS[title] if l not in have]
        if missing: ctx.do(f"label {title}: {missing}", site.post, f"/wiki/rest/api/content/{pid}/label", [{"prefix": "global", "name": l} for l in missing])
        pages[title] = {"id": pid, "space": space, "labels": LABELS[title]}
    ctx.state.save()
