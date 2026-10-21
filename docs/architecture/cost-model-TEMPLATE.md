# Cost Model — Tahadi (تحدي)

> A living estimate of the monthly cost of the deployed system. Every published
> rate must record the **date it was verified** and a source URL. Recompute the
> arithmetic whenever a rate or usage changes. This is a template — fill in real
> values and keep a dated copy.

## 1. Usage assumptions

| Assumption | Value | Note |
| --- | --- | --- |
| Frontend users (monthly active) | | |
| Backend requests / month | | |
| Data volume (rows) | | |
| Storage (GB) | | |
| Concurrent users (peak) | | |
| Number of coaches (seeded) | | |

## 2. Component rates (published, with date verified)

| Service | Plan / tier | Published rate | Billing unit | Date verified | Source URL |
| --- | --- | --- | --- | --- | --- |
| Render — frontend | *(e.g. Free / Starter)* | | /month | | |
| Render — backend | *(e.g. Free / Starter)* | | /month | | |
| Supabase — PostgreSQL | *(e.g. Free / Pro)* | | /month | | |
| *(other, e.g. domain)* | | | /month | | |

> Rule: never quote a rate from memory; fetch and record the source URL + date.
> Free tiers may be rate-limited or sleep; record the limits too.

## 3. Monthly cost arithmetic

| Component | Quantity | Rate | Monthly cost |
| --- | --- | --- | --- |
| Render frontend | 1 | | $$ |
| Render backend | 1 | | $$ |
| Supabase database | 1 | | $$ |
| *(other)* | | | $$ |
| **Total base** | | | **$$** |

*Show the arithmetic* (e.g. `1 × $0 = $0`; `1 × $25 = $25`). If any tier is metered,
show `(units × rate)`.

## 4. Sensitivity scenarios

Vary one assumption at a time and show the resulting monthly cost.

| Scenario | Changed assumption | New value | New monthly cost | Notes |
| --- | --- | --- | --- | --- |
| Small | users = e.g. 10 | | | |
| Expected | users = e.g. 50 | | | |
| High | users = e.g. 200 | | | |
| Storage jump | rows ×10 | | | |
| Free-tier expiry | Render sleeps/limits | | | |

## 5. Decision & risk

* **Does this stay within a student budget?** *(Yes/No + target ceiling)*
* **Main cost risk:** *(e.g. Render free tier sleeps after inactivity; same DB
  instance shared; bandwith.)*
* **Mitigation:** *(e.g. keep tier free; use one DB; document cold-start latency.)*

## 6. Verification

| Check | Result |
| --- | --- |
| Rates fetched from official pricing pages | ☐ Yes / ☐ No |
| Arithmetic re-computed after last change | ☐ Yes / ☐ No |
| Dated copy saved with this file | ☐ Yes / ☐ No |
