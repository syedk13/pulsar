import { createClient, type SupabaseClient } from '@supabase/supabase-js'

// Browser client. Uses ONLY the publishable key — never a secret/service-role key.
// Created lazily-safe: if env vars are missing, `supabase` is null and the app shows a
// configuration message instead of crashing at import.
const url = import.meta.env.VITE_SUPABASE_URL?.trim()
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim()

export const supabaseConfigError: string | null =
  !url || !publishableKey
    ? 'VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY must be set in the repo-root .env.'
    : null

export const supabase: SupabaseClient | null = supabaseConfigError
  ? null
  : createClient(url!, publishableKey!)
