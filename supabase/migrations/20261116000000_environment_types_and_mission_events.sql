-- Pulsar migration 2: environment measurement types + mission_events.
-- Spec: docs/synthetic-data.md section 3. Apply after 20261114000000_initial_schema.sql.

-- ---------------------------------------------------------------------------
-- 1. Split environment measurement types so different quantities never share a series.
--    The initial check only allowed 'acceleration' and 'radiation'.
-- ---------------------------------------------------------------------------
alter table public.environment_readings
  drop constraint if exists environment_readings_measurement_type_check;

alter table public.environment_readings
  add constraint environment_readings_measurement_type_check
  check (measurement_type in (
    'acceleration_quasi_steady',
    'acceleration_vibratory',
    'absorbed_dose_rate',
    'dose_equivalent_rate',
    'particle_flux',
    'ppco2',
    'proton_flux_ge10mev'
  ));

-- ---------------------------------------------------------------------------
-- 2. Mission events: space weather (DONKI, NOAA S-scale) and environment
--    excursions. Context only, never personal data or personal dose.
-- ---------------------------------------------------------------------------
create table public.mission_events (
  id               uuid primary key default gen_random_uuid(),
  event_type       text not null
                   check (event_type in ('SEP', 'FLR', 'CME', 'GST', 'S_SCALE', 'CO2_EXCURSION')),
  level            text,                 -- e.g. 'S2', 'X1.2', 'ppco2_above_1h_limit'
  start_time       timestamptz not null,
  end_time         timestamptz,
  source           text not null check (source in ('donki', 'noaa_swpc', 'synthetic')),
  source_event_id  text,                 -- DONKI activityID; null for synthetic
  link             text,
  is_simulated     boolean not null default true,
  metadata         jsonb not null default '{}'::jsonb,
  created_at       timestamptz not null default now(),
  check (end_time is null or end_time >= start_time)
);

create index mission_events_time_idx on public.mission_events (start_time desc);

-- One row per upstream event, so live adapters can upsert safely.
create unique index mission_events_source_event_uidx
  on public.mission_events (source, source_event_id)
  where source_event_id is not null;

alter table public.mission_events enable row level security;

-- Shared context, read-only for signed-in users. Writes are server-side only.
create policy "mission_events: authenticated read"
  on public.mission_events for select to authenticated
  using (true);
