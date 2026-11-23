// Row shapes for the tables the web app reads/writes. Mirrors supabase/migrations/.

export interface CrewProfile {
  id: string
  profile_code: string
  display_name: string
  mission_label: string | null
  is_fictional: boolean
}

export type CheckinSource = 'self_report' | 'wearable' | 'synthetic'

export interface HealthCheckin {
  id: string
  profile_id: string
  recorded_at: string
  sleep_duration_hours: number | null
  mood_rating: number | null
  resting_heart_rate: number | null
  source: CheckinSource
  is_simulated: boolean
  data_quality: Record<string, unknown>
  created_at: string
}

export type CheckinField = 'sleep_duration_hours' | 'resting_heart_rate' | 'mood_rating'

/**
 * Insert payload for a check-in entered through the web form.
 * `source` and `is_simulated` are literal types so the app cannot send a synthetic row;
 * RLS rejects `source = 'synthetic'` from the browser as well (migration 3).
 */
export interface FormCheckinInsert {
  profile_id: string
  recorded_at: string
  sleep_duration_hours: number | null
  mood_rating: number | null
  resting_heart_rate: number | null
  source: 'self_report'
  is_simulated: false
  data_quality: {
    entry_method: 'web_form'
    form_version: string
    hr_kind: 'resting_morning'
    mood_scale: string
    missing_fields: CheckinField[]
  }
}
