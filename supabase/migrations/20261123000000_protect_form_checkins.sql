-- Pulsar migration 3: keep form check-ins distinct from generated ones.
-- Generated rows: source = 'synthetic', is_simulated = true (written server-side by the loader).
-- Form rows (M3): source = 'self_report' (column default), is_simulated = false (new default).

-- 1. A check-in that does not say otherwise was entered by a person, not generated.
alter table public.health_checkins
  alter column is_simulated set default false;

-- 2. Signed-in users may insert check-ins only for their own profile, and never as
--    'synthetic'. Only the server (loader / secret key) writes synthetic rows,
--    so reloading synthetic data can never delete a form entry.
drop policy if exists "health_checkins: owner insert" on public.health_checkins;

create policy "health_checkins: owner insert"
  on public.health_checkins for insert to authenticated
  with check (
    source <> 'synthetic'
    and profile_id in (
      select id from public.crew_profiles where user_id = (select auth.uid())
    )
  );
