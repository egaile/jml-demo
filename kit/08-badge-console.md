# 08. The badge console (SENTRIA)

A fake physical-access system so the demo has something outside Atlassian to switch off. Jira Automation calls one serverless endpoint to activate or deactivate a badge; a console page shows every badge and a live event feed, so the audience sees the card turn red seconds after "Start deprovisioning".

You have two options: **deploy this repo as is** (fastest), or **have an AI coding assistant build your own** from the prompt in 8.4.

## 8.1 Supabase (database)

Create a free Supabase project, then run in the SQL editor:

```sql
create table badges (
  id uuid primary key default gen_random_uuid(),
  badge_number text unique not null,
  holder_name text not null,
  holder_employee_id text not null,
  department text,
  zones text[] default '{}',
  status text not null default 'ACTIVE',
  issued_date date,
  deactivated_at timestamptz,
  deactivation_ref text,
  updated_at timestamptz default now()
);

create table badge_events (
  id bigserial primary key,
  badge_number text not null,
  event_type text not null,
  detail text,
  source text,
  reference text,
  created_at timestamptz default now()
);

alter table badges enable row level security;
alter table badge_events enable row level security;
create policy "read badges" on badges for select to anon using (true);
create policy "read events" on badge_events for select to anon using (true);

insert into badges (badge_number, holder_name, holder_employee_id, department, zones, status, issued_date) values
 ('BADGE-4471','Riley Chen','rchen','Marketing', array['Floors 1-3 (business hours)','Marketing storage'], 'INACTIVE','2026-10-12'),
 ('BADGE-3417','Marcus Webb','mwebb','Sales', array['Floors 1-3 (business hours)'], 'ACTIVE','2025-01-20'),
 ('BADGE-1108','Lawrence Barnes','lbarnes','IT Operations', array['Floors 1-3 (24/7)','Server room','Network closets','Legacy data center [DECOMMISSIONED]'], 'ACTIVE','2001-03-19');
```

The browser only ever reads (publishable/anon key, select-only policies). Writes happen in the serverless function with the service role key. Riley's badge starts INACTIVE so the Joiner act (A2) visibly turns it green.

## 8.2 Deploy this repo (Vercel)

1. Fork this repo. In `src/index.html`, set `SUPABASE_URL` and `ANON_KEY` to your project's URL and **publishable** key.
2. Import the fork in Vercel. Set environment variables (type "encrypted", not "sensitive", so you can read the secret back later):

| Name | Value |
| --- | --- |
| `SUPABASE_URL` | your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | the service role key (server side only) |
| `JML_SHARED_SECRET` | any long random string; rules send it as `X-JML-Secret` |

3. Deploy. Your console is `https://<your-console>.vercel.app`, the endpoint `https://<your-console>.vercel.app/api/badge`.

Test:

```bash
curl "https://<your-console>.vercel.app/api/badge?badge_number=BADGE-1108"
```

```bash
curl -X POST "https://<your-console>.vercel.app/api/badge" -H "Content-Type: application/json" -H "X-JML-Secret: <your secret>" -d '{"badge_number":"BADGE-1108","action":"deactivate","reference":"TEST","source":"curl"}'
```

401 means a wrong secret; 502 means Supabase rejected the service key.

## 8.3 API contract (what the rules rely on)

`POST /api/badge`, header `X-JML-Secret`, body:

```json
{ "badge_number": "BADGE-1108", "action": "deactivate | activate | suspend", "reference": "JML-1", "source": "Jira Automation (Badge deactivation)", "detail": "optional" }
```

Returns `{ "ok": true, "badge": {...}, "confirmation": "BA-20261105-4821" }`. Rules A2, A7 and Demo reset read `{{webResponse.body.confirmation}}`, so turn on "Delay execution of subsequent rule actions until we've received a response" on each web request step.

`GET /api/badge?badge_number=...` returns `{ ok, badge, events }` and needs no secret.

## 8.4 Build your own with an AI assistant

Paste this into Claude (or any AI coding assistant):

```
Build a small Vercel project called "badge-console": a fake physical access control system named SENTRIA for a Jira demo.

Backend: one serverless function at api/badge.js (ES modules, no dependencies, use fetch against the Supabase REST API).
- POST /api/badge requires header X-JML-Secret equal to env JML_SHARED_SECRET (else 401). Body: badge_number, action (deactivate | activate | suspend; default deactivate), reference, source, optional detail.
  Map actions to status/event: deactivate → INACTIVE/DEACTIVATED, activate → ACTIVE/ACTIVATED, suspend → SUSPENDED/SUSPENDED.
  PATCH the badges row (status, updated_at, and deactivated_at + deactivation_ref only when INACTIVE, else null), 404 if no row.
  Generate a confirmation like BA-YYYYMMDD-NNNN, insert a badge_events row (badge_number, event_type, detail, source, reference),
  and return { ok, badge, confirmation }.
- GET /api/badge?badge_number=X returns { ok, badge, events } with the 10 newest events. No secret.
- Use env SUPABASE_URL and SUPABASE_SERVICE_KEY (service role, server side only). Allow CORS for GET, POST, OPTIONS. Return 502 with the Supabase error text on failure.

Frontend: src/index.html, a single static page served via vercel.json {"outputDirectory":"src"}.
- Dark "security operations" look: IBM Plex Mono and IBM Plex Sans, amber accent.
- A card per badge: holder initials, name, department, employee id, badge number, issued date, authorized zones
  (zones containing DECOMMISSIONED in a warning colour) and a status lozenge (ACTIVE green, INACTIVE red, SUSPENDED amber).
- A right-hand "Live Event Feed" of badge_events, newest first.
- Poll both tables every 3 seconds with the Supabase publishable (anon) key; flash any card whose status changed since the last poll.
- Header pill "CONTROLLER LINK OK" (or "LINK DEGRADED · RETRYING" when a poll fails).
- Footer: "SENTRIA CONTROLLER NODE 01 · POLL 3000MS · INTEGRATION: PEOPLE OPERATIONS AUTOMATION (WEBHOOK)".

Tables (already created in Supabase): badges(id uuid, badge_number text unique, holder_name, holder_employee_id, department,
zones text[], status, issued_date date, deactivated_at timestamptz, deactivation_ref, updated_at) and
badge_events(id bigserial, badge_number, event_type, detail, source, reference, created_at). RLS allows anon select only.
Give me the files and the Vercel deploy steps.
```

## 8.5 Resetting the feed

Before a talk, clear test events so the feed starts clean:

```sql
delete from badge_events where source like 'Jira Automation%' or source in ('Demo reset', 'curl');
update badges set status = 'INACTIVE' where badge_number = 'BADGE-4471';
update badges set status = 'ACTIVE', deactivated_at = null, deactivation_ref = null where badge_number in ('BADGE-1108','BADGE-3417');
```
