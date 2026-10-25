// SENTRIA Facility Console: badge control endpoint for Jira Automation.
//
// POST /api/badge
//   Headers: X-JML-Secret: <JML_SHARED_SECRET>
//   Body:    { "badge_number": "BADGE-1108", "action": "deactivate" | "activate" | "suspend",
//              "reference": "JML-12", "source": "Jira Automation", "detail": "optional text" }
//   Returns: { ok, badge, confirmation }
//
// GET /api/badge?badge_number=BADGE-1108
//   Returns: { ok, badge, events }   (read-only, no secret needed)
//
// The Supabase service role key lives only in this function's environment.
// The browser console keeps using the publishable key for reads.

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;
const SECRET = process.env.JML_SHARED_SECRET || process.env.JML_WEBHOOK_SECRET;

const ACTIONS = {
  deactivate: { status: "INACTIVE", event: "DEACTIVATED" },
  activate: { status: "ACTIVE", event: "ACTIVATED" },
  suspend: { status: "SUSPENDED", event: "SUSPENDED" },
};

function headers(extra = {}) {
  return {
    apikey: SERVICE_KEY,
    Authorization: `Bearer ${SERVICE_KEY}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

async function sb(path, init = {}) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, init);
  const text = await res.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!res.ok) throw new Error(`Supabase ${res.status}: ${typeof body === "string" ? body : JSON.stringify(body)}`);
  return body;
}

function confirmation() {
  const d = new Date();
  const ymd = d.toISOString().slice(0, 10).replace(/-/g, "");
  const n = Math.floor(1000 + Math.random() * 9000);
  return `BA-${ymd}-${n}`;
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-JML-Secret");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();

  if (!SUPABASE_URL || !SERVICE_KEY) {
    return res.status(500).json({ ok: false, error: "Function is missing SUPABASE_URL or SUPABASE_SERVICE_KEY" });
  }

  try {
    if (req.method === "GET") {
      const badge_number = (req.query.badge_number || "").toString().trim();
      if (!badge_number) return res.status(400).json({ ok: false, error: "badge_number is required" });
      const badges = await sb(`badges?badge_number=eq.${encodeURIComponent(badge_number)}&select=*`, { headers: headers() });
      if (!badges.length) return res.status(404).json({ ok: false, error: `No badge ${badge_number}` });
      const events = await sb(`badge_events?badge_number=eq.${encodeURIComponent(badge_number)}&select=*&order=created_at.desc&limit=10`, { headers: headers() });
      return res.status(200).json({ ok: true, badge: badges[0], events });
    }

    if (req.method !== "POST") return res.status(405).json({ ok: false, error: "Use GET or POST" });

    if (!SECRET || req.headers["x-jml-secret"] !== SECRET) {
      return res.status(401).json({ ok: false, error: "Invalid or missing X-JML-Secret" });
    }

    const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : (req.body || {});
    const badge_number = (body.badge_number || "").toString().trim();
    const action = (body.action || "deactivate").toString().toLowerCase();
    const reference = (body.reference || "").toString().trim() || null;
    const source = (body.source || "People Operations Automation").toString();
    const spec = ACTIONS[action];

    if (!badge_number) return res.status(400).json({ ok: false, error: "badge_number is required" });
    if (!spec) return res.status(400).json({ ok: false, error: `action must be one of ${Object.keys(ACTIONS).join(", ")}` });

    const now = new Date().toISOString();
    const patch = {
      status: spec.status,
      updated_at: now,
      deactivated_at: spec.status === "INACTIVE" ? now : null,
      deactivation_ref: spec.status === "INACTIVE" ? reference : null,
    };

    const updated = await sb(`badges?badge_number=eq.${encodeURIComponent(badge_number)}`, {
      method: "PATCH",
      headers: headers({ Prefer: "return=representation" }),
      body: JSON.stringify(patch),
    });
    if (!updated.length) return res.status(404).json({ ok: false, error: `No badge ${badge_number}` });
    const badge = updated[0];

    const conf = confirmation();
    const detail = body.detail
      ? body.detail.toString()
      : `Badge ${badge_number} (${badge.holder_name}) set to ${spec.status}. Confirmation ${conf}.`;

    await sb(`badge_events`, {
      method: "POST",
      headers: headers({ Prefer: "return=minimal" }),
      body: JSON.stringify({ badge_number, event_type: spec.event, detail, source, reference }),
    });

    return res.status(200).json({ ok: true, badge, confirmation: conf });
  } catch (err) {
    return res.status(502).json({ ok: false, error: err.message });
  }
}
