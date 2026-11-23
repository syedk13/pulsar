import type { SupabaseClient } from '@supabase/supabase-js'

import type { CrewProfile } from '../lib/types'
import { toDbError } from './errors'

/**
 * The crew profile linked to a signed-in account, or null if the account is not linked.
 * `crew_profiles.user_id` is unique, so there is at most one. RLS also limits reads to it.
 */
export async function getOwnProfile(
  client: SupabaseClient,
  userId: string,
): Promise<CrewProfile | null> {
  const { data, error } = await client
    .from('crew_profiles')
    .select('id, profile_code, display_name, mission_label, is_fictional')
    .eq('user_id', userId)
    .maybeSingle<CrewProfile>()
  if (error) throw toDbError(error)
  return data
}
