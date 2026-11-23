import type { SupabaseClient } from '@supabase/supabase-js'
import { type FormEvent, type ReactNode, useState } from 'react'

import {
  buildFormCheckin,
  type CheckinFormValues,
  EMPTY_FORM,
  MOOD_LABELS,
  validateCheckin,
} from '../checkin/validation'
import { createCheckin } from '../data/checkins'
import { DbError, UNIQUE_VIOLATION } from '../data/errors'
import type { CheckinField, HealthCheckin } from '../lib/types'

type Errors = Partial<Record<CheckinField | 'form', string>>

interface Props {
  client: SupabaseClient
  profileId: string
  /** True when today's check-in exists (or history is still loading). */
  disabled: boolean
  onSaved: (row: HealthCheckin) => void
  /** The database rejected the insert because today's check-in already exists (23505). */
  onAlreadyCheckedIn: () => void
}

export function CheckinForm({ client, profileId, disabled, onSaved, onAlreadyCheckedIn }: Props) {
  const [values, setValues] = useState<CheckinFormValues>(EMPTY_FORM)
  const [errors, setErrors] = useState<Errors>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  function set(field: CheckinField, value: string) {
    setValues((v) => ({ ...v, [field]: value }))
    setErrors((e) => ({ ...e, [field]: undefined, form: undefined }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (submitting || disabled) return
    setSubmitError(null)
    const result = validateCheckin(values)
    if (!result.ok) {
      setErrors(result.errors)
      return
    }
    setErrors({})
    setSubmitting(true)
    try {
      const saved = await createCheckin(client, buildFormCheckin(profileId, result.value, new Date()))
      setValues(EMPTY_FORM)
      onSaved(saved)
    } catch (err) {
      if (err instanceof DbError && err.code === UNIQUE_VIOLATION) {
        // Not a failure to report: the page shows "already checked in today" and re-reads.
        setValues(EMPTY_FORM)
        onAlreadyCheckedIn()
        return
      }
      setSubmitError(err instanceof Error ? err.message : 'Could not save the check-in.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form noValidate onSubmit={onSubmit} className="space-y-5" aria-busy={submitting}>
      <fieldset disabled={submitting || disabled} className="space-y-5">
        <Field
          label="Sleep last night"
          unit="hours"
          error={errors.sleep_duration_hours}
          input={
            <input
              id="sleep"
              type="number"
              inputMode="decimal"
              step="0.1"
              min="0"
              max="24"
              placeholder="e.g. 6.5"
              value={values.sleep_duration_hours}
              onChange={(e) => set('sleep_duration_hours', e.target.value)}
              aria-invalid={!!errors.sleep_duration_hours}
              className="w-32 rounded border border-slate-300 px-3 py-2"
            />
          }
          htmlFor="sleep"
        />
        <Field
          label="Resting heart rate (morning)"
          unit="bpm"
          error={errors.resting_heart_rate}
          input={
            <input
              id="rhr"
              type="number"
              inputMode="numeric"
              step="1"
              min="20"
              max="250"
              placeholder="e.g. 58"
              value={values.resting_heart_rate}
              onChange={(e) => set('resting_heart_rate', e.target.value)}
              aria-invalid={!!errors.resting_heart_rate}
              className="w-32 rounded border border-slate-300 px-3 py-2"
            />
          }
          htmlFor="rhr"
        />
        <fieldset>
          <legend className="text-sm font-medium">Mood</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <label
                key={n}
                className="flex cursor-pointer items-center gap-1 rounded border border-slate-300 px-3 py-1.5 text-sm has-[:checked]:border-slate-900 has-[:checked]:bg-slate-900 has-[:checked]:text-white"
              >
                <input
                  type="radio"
                  name="mood"
                  value={n}
                  checked={values.mood_rating === String(n)}
                  onChange={() => set('mood_rating', String(n))}
                  className="sr-only"
                />
                {n} · {MOOD_LABELS[n]}
              </label>
            ))}
            {values.mood_rating !== '' && (
              <button
                type="button"
                onClick={() => set('mood_rating', '')}
                className="px-2 text-sm text-slate-600 underline"
              >
                Clear
              </button>
            )}
          </div>
          {errors.mood_rating && <p className="mt-1 text-sm text-red-700">{errors.mood_rating}</p>}
        </fieldset>
      </fieldset>

      <p className="text-xs text-slate-500">
        Leave a field blank if you don't have it today; it is saved as missing, not as zero.
      </p>
      {errors.form && (
        <p role="alert" className="text-sm text-red-700">
          {errors.form}
        </p>
      )}
      {submitError && (
        <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">
          {submitError}
        </p>
      )}
      <button
        type="submit"
        disabled={submitting || disabled}
        className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {submitting ? 'Saving…' : 'Save check-in'}
      </button>
    </form>
  )
}

function Field(props: {
  label: string
  unit: string
  htmlFor: string
  input: ReactNode
  error?: string
}) {
  return (
    <div>
      <label htmlFor={props.htmlFor} className="block text-sm font-medium">
        {props.label}
      </label>
      <div className="mt-1 flex items-center gap-2">
        {props.input}
        <span className="text-sm text-slate-600">{props.unit}</span>
      </div>
      {props.error && <p className="mt-1 text-sm text-red-700">{props.error}</p>}
    </div>
  )
}
