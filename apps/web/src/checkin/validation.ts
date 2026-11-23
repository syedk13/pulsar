import type { CheckinField, FormCheckinInsert } from '../lib/types'

export const FORM_VERSION = 'checkin-form-v1'
export const MOOD_SCALE = 'pulsar-mood-1to5-v1'
export const MOOD_LABELS: Record<number, string> = {
  1: 'Very low',
  2: 'Low',
  3: 'Okay',
  4: 'Good',
  5: 'Very good',
}

/** Raw form state: strings straight from the inputs, '' means "left blank". */
export interface CheckinFormValues {
  sleep_duration_hours: string
  resting_heart_rate: string
  mood_rating: string
}

export const EMPTY_FORM: CheckinFormValues = {
  sleep_duration_hours: '',
  resting_heart_rate: '',
  mood_rating: '',
}

export interface ParsedCheckin {
  sleep_duration_hours: number | null
  resting_heart_rate: number | null
  mood_rating: number | null
  missing_fields: CheckinField[]
}

export type ValidationResult =
  | { ok: true; value: ParsedCheckin }
  | { ok: false; errors: Partial<Record<CheckinField | 'form', string>> }

// Input bounds match the database CHECK constraints. They are limits on what the field
// accepts, not health thresholds.
export function validateCheckin(values: CheckinFormValues): ValidationResult {
  const errors: Partial<Record<CheckinField | 'form', string>> = {}
  const missing: CheckinField[] = []

  const sleepRaw = values.sleep_duration_hours.trim()
  let sleep: number | null = null
  if (sleepRaw === '') missing.push('sleep_duration_hours')
  else {
    const n = Number(sleepRaw)
    if (!Number.isFinite(n) || n < 0 || n > 24) {
      errors.sleep_duration_hours = 'Enter hours between 0 and 24.'
    } else if (Math.round(n * 100) !== n * 100) {
      errors.sleep_duration_hours = 'Use at most two decimal places (e.g. 6.5).'
    } else sleep = n
  }

  const rhrRaw = values.resting_heart_rate.trim()
  let rhr: number | null = null
  if (rhrRaw === '') missing.push('resting_heart_rate')
  else {
    const n = Number(rhrRaw)
    if (!Number.isInteger(n) || n < 20 || n > 250) {
      errors.resting_heart_rate = 'Enter a whole number of bpm between 20 and 250.'
    } else rhr = n
  }

  const moodRaw = values.mood_rating.trim()
  let mood: number | null = null
  if (moodRaw === '') missing.push('mood_rating')
  else {
    const n = Number(moodRaw)
    if (!Number.isInteger(n) || n < 1 || n > 5) errors.mood_rating = 'Pick a mood from 1 to 5.'
    else mood = n
  }

  if (Object.keys(errors).length === 0 && missing.length === 3) {
    errors.form = 'Fill in at least one indicator. Any you skip are saved as missing.'
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors }
  return {
    ok: true,
    value: {
      sleep_duration_hours: sleep,
      resting_heart_rate: rhr,
      mood_rating: mood,
      missing_fields: missing,
    },
  }
}

/** Build the insert row. Provenance is set explicitly, never left to column defaults. */
export function buildFormCheckin(
  profileId: string,
  parsed: ParsedCheckin,
  recordedAt: Date,
): FormCheckinInsert {
  return {
    profile_id: profileId,
    recorded_at: recordedAt.toISOString(),
    sleep_duration_hours: parsed.sleep_duration_hours,
    resting_heart_rate: parsed.resting_heart_rate,
    mood_rating: parsed.mood_rating,
    source: 'self_report',
    is_simulated: false,
    data_quality: {
      entry_method: 'web_form',
      form_version: FORM_VERSION,
      hr_kind: 'resting_morning',
      mood_scale: MOOD_SCALE,
      missing_fields: parsed.missing_fields,
    },
  }
}
