import type { PostgrestError } from '@supabase/supabase-js'

/** Turn a Supabase/PostgREST error into a message a crew member can act on. */
export function describeDbError(error: PostgrestError | Error): string {
  const code = 'code' in error ? error.code : undefined
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
