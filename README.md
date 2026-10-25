# jml-demo

Source for the **SENTRIA Access Control · Facility Console**, the JML (Joiner/Mover/Leaver) badge demo. Jira Automation calls a serverless endpoint to activate, deactivate, or suspend a facility badge, and the console shows badge status and events live from Supabase.

Recovered from the production Vercel deployment of `jml-badge-console` (deployment `dpl_uyiwZjUHsoYDPohoMSLbogrFsGAV`, October 2026). Every file was checked against the deployed file hash.

## Live

- Console: https://jml-badge-console.vercel.app
- Vercel project: `jml-badge-console` (egaile-gmailcom's projects)
- Supabase project ref: `cxbkbtpschiobtmvesch`

## Layout

| Path | What it is |
| --- | --- |
| `api/badge.js` | Serverless function for Jira Automation. Writes to Supabase with the service role key. |
| `src/index.html` | The console UI. Reads from Supabase with the publishable key. |
| `vercel.json` | Serves `src/` as the static output. |
| `package.json` | ES module flag, no dependencies. |

## API

`POST /api/badge`

- Header: `X-JML-Secret: <JML_SHARED_SECRET>`
- Body: `{ "badge_number": "BADGE-1108", "action": "deactivate" | "activate" | "suspend", "reference": "JML-12", "source": "Jira Automation", "detail": "optional text" }`
- Returns: `{ ok, badge, confirmation }`

`GET /api/badge?badge_number=BADGE-1108`

- Read-only, no secret needed
- Returns: `{ ok, badge, events }`

## Environment variables (set in Vercel, never committed)

| Name | Purpose |
| --- | --- |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Service role key, used only inside `api/badge.js` |
| `JML_SHARED_SECRET` | Shared secret Jira Automation sends in `X-JML-Secret` (`JML_WEBHOOK_SECRET` also accepted) |

## Deploy

```bash
vercel link        # pick the existing jml-badge-console project
vercel --prod
```

To deploy on every push instead, connect this repo under the Vercel project's Settings → Git.
