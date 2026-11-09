-- Tahadi agent backend schema (ADR-0007). 4 tables, cap is 8.
-- Run once in the Supabase SQL editor. Safe to re-run.

create extension if not exists pgcrypto;

create table if not exists clients (
  id               uuid primary key default gen_random_uuid(),
  name             text not null,
  telegram_chat_id bigint unique,
  created_at       timestamptz not null default now()
);

create table if not exists measurements (
  id         uuid primary key default gen_random_uuid(),
  client_id  uuid not null references clients(id) on delete cascade,
  date       date not null,
  weight_kg  numeric(5,2) check (weight_kg between 30 and 300),
  waist_cm   numeric(5,1) check (waist_cm between 40 and 200),
  source     text not null check (source in ('app', 'telegram')),
  created_at timestamptz not null default now(),
  check (weight_kg is not null or waist_cm is not null)
);
create index if not exists measurements_client_date_idx on measurements (client_id, date);

create table if not exists form_checks (
  id         uuid primary key default gen_random_uuid(),
  client_id  uuid not null references clients(id) on delete cascade,
  exercise   text not null default 'squat',
  reps       int  not null check (reps >= 0),
  errors     jsonb not null default '[]'::jsonb,
  confidence numeric(4,3) check (confidence between 0 and 1),
  created_at timestamptz not null default now()
);
create index if not exists form_checks_client_idx on form_checks (client_id, created_at desc);

create table if not exists drafts (
  id         uuid primary key default gen_random_uuid(),
  client_id  uuid not null references clients(id) on delete cascade,
  text       text not null,
  status     text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  created_at timestamptz not null default now(),
  sent_at    timestamptz
);
create index if not exists drafts_status_idx on drafts (status, created_at desc);

-- Row-level security on every table.
-- The backend uses the service key, which bypasses RLS.
-- DEMO ONLY: the frontend's anon key may read all four tables (synthetic data only, see R-013).
alter table clients      enable row level security;
alter table measurements enable row level security;
alter table form_checks  enable row level security;
alter table drafts       enable row level security;

drop policy if exists "demo anon read" on clients;
drop policy if exists "demo anon read" on measurements;
drop policy if exists "demo anon read" on form_checks;
drop policy if exists "demo anon read" on drafts;

create policy "demo anon read" on clients      for select to anon using (true);
create policy "demo anon read" on measurements for select to anon using (true);
create policy "demo anon read" on form_checks  for select to anon using (true);
create policy "demo anon read" on drafts       for select to anon using (true);
