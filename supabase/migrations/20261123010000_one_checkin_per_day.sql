-- Pulsar migration 4: at most one check-in per crew profile per day.
-- "Day" is the UTC calendar day (mission time is UTC, see docs/synthetic-data.md).
-- Applies to every source, so the M4 baseline ("last 14 check-ins") is also "last 14 days with a check-in".
-- Apply after 20261123000000_protect_form_checkins.sql.

-- 1. Check-ins from the app are stamped with the server's time, not the browser's.
--    This stops backdating (which could collide with a synthetic day and break reloads)
--    and keeps "today" consistent no matter the device clock.
create or replace function public.health_checkins_server_time()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if current_user = 'authenticated' then
    new.recorded_at := now();
  end if;
  return new;
end;
$$;

drop trigger if exists health_checkins_server_time on public.health_checkins;
create trigger health_checkins_server_time
  before insert on public.health_checkins
  for each row execute function public.health_checkins_server_time();

-- 2. The cap itself. A second check-in for the same profile on the same UTC day
--    fails with error code 23505 (unique_violation); the app shows
--    "You've already checked in today".
create unique index health_checkins_one_per_day_uidx
  on public.health_checkins (profile_id, ((recorded_at at time zone 'UTC')::date));
