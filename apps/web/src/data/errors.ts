import type { PostgrestError } from '@supabase/supabase-js'

export const ALREADY_CHECKED_IN_TODAY = 'You’ve already checked in today (UTC)'

/** Postgres unique_violation. For check-ins: the one-per-profile-per-UTC-day index (migration 4). */
export const UNIQUE_VIOLATION = '23505'

/** A database error with a user-facing message and the original Postgres/PostgREST code. */
export class DbError extends Error {
  readonly code: string | undefined

  constructor(message: string, code: string | undefined) {
    super(message)
    this.name = 'DbError'
    this.code = code
  }
}

export function toDbError(error: PostgrestError): DbError {
  return new DbError(describeDbError(error), error.code)
}

/** Turn a Supabase/PostgREST error into a message a crew member can act on. */
export function describeDbError(error: PostgrestError | Error): string {
  const code = 'code' in error ? error.code : undefined
  if (code === UNIQUE_VIOLATION) {
    return `${ALREADY_CHECKED_IN_TODAY}.`
  }
  if (code === '42501') {
    return 'Not allowed: check-ins can only be saved to your own crew profile.'
  }
  if (code === '23514') {
    return 'One of the values is outside what the field accepts. Check the form and try again.'
  }
  if (code === 'PGRST301' || /jwt/i.test(error.message)) {
    return 'Your session has expired. Sign in again.'
  }
  if (/fetch|network/i.test(error.message)) {
    return 'Could not reach the database. Check your connection and try again.'
  }
  return error.message
}
