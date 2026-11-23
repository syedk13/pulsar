import type { SupabaseClient } from '@supabase/supabase-js'

import type { FormCheckinInsert, HealthCheckin } from '../lib/types'
import { toDbError } from './errors'

const COLUMNS =
  'id, profile_id, recorded_at, sleep_duration_hours, mood_rating, resting_heart_rate, source, is_simulated, data_quality, created_at'

/** Most recent check-ins for a profile, all sources, newest first. */
export async function listCheckins(
  client: SupabaseClient,
  profileId: string,
  limit = 10,
): Promise<HealthCheckin[]> {
  const { data, error } = await client
    .from('health_checkins')
    .select(COLUMNS)
    .eq('profile_id', profileId)
    .order('recorded_at', { ascending: false })
    .limit(limit)
    .overrideTypes<HealthCheckin[], { merge: false }>()
  if (error) throw toDbError(error)
  return data ?? []
}

/** Insert one form check-in and return the stored row (as the database saved it). */
export async function createCheckin(
  client: SupabaseClient,
  row: FormCheckinInsert,
): Promise<HealthCheckin> {
  const { data, error } = await client
    .from('health_checkins')
    .insert(row)
    .select(COLUMNS)
    .single<HealthCheckin>()
  if (error) throw toDbError(error)
  return data
}
