# Cost Model — Tahadi (تحدي)

> A living estimate of the monthly cost of the deployed system. Every published
> rate records the **date it was verified** and a source URL. Recompute the
> arithmetic whenever a rate or usage changes. This copy is dated **2026-10-21**.

## 1. Usage assumptions

| Assumption | Value | Note |
| --- | --- | --- |
| Frontend users (monthly active) | 50 | Course demo: ~10 coaches + ~40 clients (synthetic) |
| Backend requests / month | 75,000 | ~50 users × ~50 requests/day × 30 days |
| Data volume (rows) | ~5,000 | users + clients + measurements + thread messages |
| Storage (GB) | 0.1 | Synthetic only; no files, well under free tier |
| Concurrent users (peak) | 20 | Matches NFR-2 |
| Number of coaches (seeded) | 10 | Idempotent seed script |

## 2. Component rates (published, with date verified)

| Service | Plan / tier | Published rate | Billing unit | Date verified | Source URL |
| --- | --- | --- | --- | --- | --- |
| Render — frontend (static site) | Static Sites | $0 | /month | 2026-10-21 | https://render.com/pricing |
| Render — backend (web service) | Free compute | $0 | /month | 2026-10-21 | https://render.com/pricing |
| Render — backend (optional always-on) | 1c-2g (1 CPU / 2 GB) | $25 | /month | 2026-10-21 | https://render.com/pricing |
| Supabase — PostgreSQL | Free | $0 | /month | 2026-10-21 | https://supabase.com/pricing |
| Supabase — PostgreSQL (reliable) | Pro | $25 | /month | 2026-10-21 | https://supabase.com/pricing |

> Rule: never quote a rate from memory; fetch and record the source URL + date.
> Free tiers may be rate-limited or sleep; record the limits too.

* **Render free compute limits:** 512 MB RAM, <1 CPU, **750 free instance hours per
  workspace per month**; a web service sleeps after ~15 minutes of inactivity.
  Static sites are always free. **Supabase free limits:** 500 MB DB, 50,000 monthly
  active users, 5 GB egress, **pauses after 1 week of inactivity**, max 2 active
  projects.

## 3. Monthly cost arithmetic

| Component | Quantity | Rate | Monthly cost |
| --- | --- | --- | --- |
| Render frontend (static site) | 1 | $0 | $0 |
| Render backend (free web service) | 1 | $0 | $0 |
| Supabase database (free) | 1 | $0 | $0 |
| **Total base** | | | **$0** |

*Show the arithmetic:* `1 × $0 = $0`; `1 × $0 = $0`; `1 × $0 = $0`.

> The backend web service staying on the **free tier** uses ≈730 instance hours/month
> (24×7), which is within the 750 free hours/workspace/month, so it costs $0. If we
> needed a second always-on web service or higher compute, the free tier would not
> cover both.

## 4. Sensitivity scenarios

Vary one assumption at a time and show the resulting monthly cost.

| Scenario | Changed assumption | New value | New monthly cost | Notes |
| --- | --- | --- | --- | --- |
| Small | Frontend users | 10 | $0 | Still within free tiers |
| Expected | Frontend users | 50 | $0 | Within free tiers |
| High | Frontend users | 200 | $0 | Within 50k MAU and 500 MB; free tier holds |
| Reliability (always-on, no sleep/pause) | Backend + DB tiers | backend 1c-2g + Supabase Pro | `$25 + $25 = $50` | Avoids cold start and DB pause |
| Storage jump | Data volume ×10 | ~50,000 rows | $0 (or $25 if >500 MB) | 50k rows still under 500 MB; Pro if exceeded |
| Free-tier expiry | Render sleeps after idle | cold start | $0 (latency risk) | Covered by R-004; warm-up before demo |

## 5. Decision & risk

* **Does this stay within a student budget?** **Yes.** Target ceiling **$0/month**
  on the all-free tier; up to **$50/month** if we choose always-on reliability.
* **Main cost risk:** Render's free web service sleeps after ~15 min of inactivity
  (cold start, R-004) and Supabase free pauses after 1 week of inactivity (R-005) —
  both hit during a demo if not warmed up.
* **Mitigation:** stay on free tiers; ping a health endpoint and access the app
  before the demo; document cold-start latency in the runbook; if budget allows,
  upgrade the backend to `1c-2g` ($25) and Supabase to Pro ($25).

## 6. Verification

| Check | Result |
| --- | --- |
| Rates fetched from official pricing pages | ☑ Yes (render.com/pricing, supabase.com/pricing, 2026-10-21) |
| Arithmetic re-computed after last change | ☑ Yes (by hand) |
| Dated copy saved with this file | ☑ Yes (2026-10-21) |
