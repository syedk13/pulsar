import type { SupabaseClient, User } from '@supabase/supabase-js'
import { useCallback, useEffect, useState } from 'react'

import { CheckinForm } from '../components/CheckinForm'
import { CheckinHistory, ProvenanceBadge, Value } from '../components/CheckinHistory'
import { MOOD_LABELS } from '../checkin/validation'
import { listCheckins } from '../data/checkins'
import { ALREADY_CHECKED_IN_TODAY } from '../data/errors'
import { getOwnProfile } from '../data/profile'
import { formatUtc, utcDate } from '../lib/format'
import type { CrewProfile, HealthCheckin } from '../lib/types'

type ProfileState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'unlinked' }
  | { status: 'ready'; profile: CrewProfile }

const HISTORY_LIMIT = 10

export function CheckinPage({ client, user }: { client: SupabaseClient; user: User }) {
  const [profileState, setProfileState] = useState<ProfileState>({ status: 'loading' })
  const [profileAttempt, setProfileAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setProfileState({ status: 'loading' })
    getOwnProfile(client, user.id)
      .then((profile) => {
        if (active) setProfileState(profile ? { status: 'ready', profile } : { status: 'unlinked' })
      })
      .catch((err: Error) => active && setProfileState({ status: 'error', message: err.message }))
    return () => {
      active = false
    }
  }, [client, user.id, profileAttempt])

  if (profileState.status === 'loading') {
    return <p className="text-sm text-slate-600">Loading your crew profile…</p>
  }
  if (profileState.status === 'error') {
    return (
      <p role="alert" className="text-sm text-red-700">
        Could not load your crew profile: {profileState.message}{' '}
        <button type="button" className="underline" onClick={() => setProfileAttempt((n) => n + 1)}>
          Retry
        </button>
      </p>
    )
  }
  if (profileState.status === 'unlinked') {
    return (
      <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-medium">This account isn't linked to a crew profile yet.</p>
        <p className="mt-1">
          Ask the project owner to set <code>crew_profiles.user_id</code> for your account. Your
          account id is <code className="select-all">{user.id}</code>.
        </p>
      </div>
    )
  }
  return <LinkedCheckin client={client} profile={profileState.profile} />
}

function LinkedCheckin({ client, profile }: { client: SupabaseClient; profile: CrewProfile }) {
  const [rows, setRows] = useState<HealthCheckin[]>([])
  const [loading, setLoading] = useState(true)
  const [loadedOnce, setLoadedOnce] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastSaved, setLastSaved] = useState<HealthCheckin | null>(null)
  // UTC date on which the database answered 23505. Keeps the form locked even if the
  // device clock disagrees with the server about which day it is.
  const [duplicateDay, setDuplicateDay] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setRows(await listCheckins(client, profile.id, HISTORY_LIMIT))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load check-ins.')
    } finally {
      setLoading(false)
      setLoadedOnce(true)
    }
  }, [client, profile.id])

  useEffect(() => {
    void reload()
  }, [reload])

  function onSaved(row: HealthCheckin) {
    setLastSaved(row)
    // Show the saved row immediately, then re-read so the list matches the database.
    setRows((prev) => [row, ...prev.filter((r) => r.id !== row.id)].slice(0, HISTORY_LIMIT))
    void reload()
  }

  function onAlreadyCheckedIn() {
    setDuplicateDay(utcDate(new Date()))
    void reload()
  }

  // The cap (migration 4) applies to every source, so any row dated today counts.
  const today = utcDate(new Date())
  const todays = rows.find((r) => utcDate(r.recorded_at) === today)
  const alreadyToday = !!todays || duplicateDay === today
  const formDisabled = alreadyToday || !loadedOnce

  return (
    <div className="space-y-8">
      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">Daily check-in</h2>
        <p className="mb-5 text-sm text-slate-600">
          {profile.display_name} · {profile.profile_code}
          {profile.mission_label ? ` · ${profile.mission_label}` : ''}
        </p>
        {lastSaved && (
          <p role="status" className="mb-5 rounded bg-emerald-50 p-3 text-sm text-emerald-900">
            Check-in saved at {formatUtc(lastSaved.recorded_at)} as self-reported.
          </p>
        )}
        {alreadyToday && (
          <div role="status" className="mb-5 rounded bg-slate-100 p-3 text-sm text-slate-800">
            <p className="font-medium">{ALREADY_CHECKED_IN_TODAY}</p>
            {todays ? (
              <TodaySummary row={todays} />
            ) : (
              <p className="mt-1 text-slate-600">{loading ? 'Loading it…' : 'It will appear in the history below.'}</p>
            )}
          </div>
        )}
        <CheckinForm
          client={client}
          profileId={profile.id}
          disabled={formDisabled}
          onSaved={onSaved}
          onAlreadyCheckedIn={onAlreadyCheckedIn}
        />
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold">Recent check-ins</h2>
        <CheckinHistory
          rows={rows}
          loading={loading}
          error={error}
          highlightId={lastSaved?.id ?? null}
          onRetry={() => void reload()}
        />
      </section>
    </div>
  )
}

function TodaySummary({ row }: { row: HealthCheckin }) {
  return (
    <dl className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1">
      <div>
        <dt className="inline text-slate-500">Recorded </dt>
        <dd className="inline">{formatUtc(row.recorded_at)}</dd>
      </div>
      <div>
        <dt className="inline text-slate-500">Sleep </dt>
        <dd className="inline">
          <Value value={row.sleep_duration_hours} unit="h" />
        </dd>
      </div>
      <div>
        <dt className="inline text-slate-500">Resting HR </dt>
        <dd className="inline">
          <Value value={row.resting_heart_rate} unit="bpm" />
        </dd>
      </div>
      <div>
        <dt className="inline text-slate-500">Mood </dt>
        <dd className="inline">
          {row.mood_rating === null ? (
            <Value value={null} unit="" />
          ) : (
            `${row.mood_rating} ${MOOD_LABELS[row.mood_rating]}`
          )}
        </dd>
      </div>
      <ProvenanceBadge row={row} />
    </dl>
  )
}
