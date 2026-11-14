-- Pulsar initial schema (structure only — no seed data, no application logic).
-- Apply manually via the Supabase SQL editor or `supabase db push` once a project exists.
-- See docs/data-model.md.

create extension if not exists pgcrypto;  -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Crew profiles (fictional/synthetic for the hackathon demo)
-- ---------------------------------------------------------------------------
create table public.crew_profiles (
  id                uuid primary key default gen_random_uuid(),
  -- Optional link to a Supabase Auth user if accounts are enabled.
  user_id           uuid unique references auth.users (id) on delete set null,
  profile_code      text not null unique,          -- fictional identifier, e.g. "CREW-A"
  display_name      text not null,
  mission_label     text,
  baseline_metadata jsonb not null default '{}'::jsonb,  -- placeholder for future baselines
  is_fictional      boolean not null default true,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Daily health check-ins
-- ---------------------------------------------------------------------------
create table public.health_checkins (
  id                   uuid primary key default gen_random_uuid(),
  profile_id           uuid not null references public.crew_profiles (id) on delete cascade,
  recorded_at          timestamptz not null,
  sleep_duration_hours numeric(4, 2) check (sleep_duration_hours between 0 and 24),
  mood_rating          smallint check (mood_rating between 1 and 5),
  resting_heart_rate   smallint check (resting_heart_rate between 20 and 250),  -- bpm
  source               text not null default 'self_report'
                       check (source in ('self_report', 'wearable', 'synthetic')),
  is_simulated         boolean not null default true,
  data_quality         jsonb not null default '{}'::jsonb,  -- e.g. completeness/flags
  created_at           timestamptz not null default now()
);

create index health_checkins_profile_time_idx
  on public.health_checkins (profile_id, recorded_at desc);

-- ---------------------------------------------------------------------------
-- Mission-context environment telemetry (NOT personal dose / personal data)
-- ---------------------------------------------------------------------------
create table public.environment_readings (
  id                uuid primary key default gen_random_uuid(),
  recorded_at       timestamptz not null,
  source            text not null,       -- e.g. 'synthetic', 'nasa_pims', 'nasa_radlab'
  instrument        text,
  measurement_type  text not null
                    check (measurement_type in ('acceleration', 'radiation')),
  value             double precision not null,
  unit              text not null,       -- e.g. 'micro-g', 'uGy/h'
  location_context  text,                -- e.g. module/vehicle; never an individual
  is_simulated      boolean not null default true,
  is_stale          boolean not null default false,
  source_retrieved_at timestamptz,       -- freshness tracking for future ingestion
  metadata          jsonb not null default '{}'::jsonb,
  created_at        timestamptz not null default now()
);

create index environment_readings_type_time_idx
  on public.environment_readings (measurement_type, recorded_at desc);

-- ---------------------------------------------------------------------------
-- Anomaly results — reserved for future analysis output. Not populated yet.
-- ---------------------------------------------------------------------------
create table public.anomaly_results (
  id             uuid primary key default gen_random_uuid(),
  profile_id     uuid not null references public.crew_profiles (id) on delete cascade,
  checkin_id     uuid references public.health_checkins (id) on delete set null,
  score          double precision,
  review_label   text check (review_label in ('within_baseline', 'worth_reviewing', 'insufficient_data')),
  explanation    jsonb not null default '{}'::jsonb,   -- plain-language text + contributing features
  model_version  text not null,
  created_at     timestamptz not null default now()
);

create index anomaly_results_profile_time_idx
  on public.anomaly_results (profile_id, created_at desc);
create index anomaly_results_checkin_idx on public.anomaly_results (checkin_id);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- RLS is enabled on every table so nothing is readable via the publishable key
-- until a policy explicitly allows it. The server (service/secret key) bypasses RLS.
-- ---------------------------------------------------------------------------
alter table public.crew_profiles        enable row level security;
alter table public.health_checkins      enable row level security;
alter table public.environment_readings enable row level security;
alter table public.anomaly_results      enable row level security;

-- Signed-in users can read/update only their own profile.
create policy "crew_profiles: owner read"
  on public.crew_profiles for select to authenticated
  using (user_id = (select auth.uid()));

create policy "crew_profiles: owner update"
  on public.crew_profiles for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- Signed-in users can read and insert check-ins for their own profile.
create policy "health_checkins: owner read"
  on public.health_checkins for select to authenticated
  using (profile_id in (select id from public.crew_profiles where user_id = (select auth.uid())));

create policy "health_checkins: owner insert"
  on public.health_checkins for insert to authenticated
  with check (profile_id in (select id from public.crew_profiles where user_id = (select auth.uid())));

-- Mission-context telemetry is shared, read-only for signed-in users. Writes are server-side only.
create policy "environment_readings: authenticated read"
  on public.environment_readings for select to authenticated
  using (true);

-- Users can read their own anomaly results. Writes are server-side only (FastAPI with secret key).
create policy "anomaly_results: owner read"
  on public.anomaly_results for select to authenticated
  using (profile_id in (select id from public.crew_profiles where user_id = (select auth.uid())));

-- PLACEHOLDER: if the demo runs without accounts, add explicit, narrowly-scoped
-- `to anon` SELECT policies for fictional profiles only (is_fictional = true).
-- Do not add anon write policies.
