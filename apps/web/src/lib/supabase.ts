import { createClient } from '@supabase/supabase-js'

// Browser client. Uses ONLY the publishable (anon) key — never a secret/service-role key.
// Not imported anywhere yet; wire it up when features are implemented.
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
)
