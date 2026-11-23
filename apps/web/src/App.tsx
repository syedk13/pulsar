import type { SupabaseClient } from '@supabase/supabase-js'
import type { ReactNode } from 'react'

import { useSession } from './auth/useSession'
import { SignIn } from './components/SignIn'
import { supabase, supabaseConfigError } from './lib/supabase'
import { CheckinPage } from './pages/CheckinPage'

export function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-3xl px-4 py-8">
        {supabase ? (
          <AuthedApp client={supabase} />
        ) : (
          <Shell>
            <p role="alert" className="rounded bg-red-50 p-4 text-sm text-red-800">
              Supabase is not configured. {supabaseConfigError}
            </p>
          </Shell>
        )}
        <footer className="mt-10 text-xs text-slate-500">
          Decision-support prototype, not a diagnostic tool. All crew profiles are fictional.
        </footer>
      </div>
    </div>
  )
}

function AuthedApp({ client }: { client: SupabaseClient }) {
  const session = useSession(client)

  if (session === undefined) {
    return (
      <Shell>
        <p className="text-sm text-slate-600">Loading…</p>
      </Shell>
    )
  }
  if (!session) {
    return (
      <Shell>
        <SignIn client={client} />
      </Shell>
    )
  }
  return (
    <Shell
      right={
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-600">{session.user.email}</span>
          <button type="button" className="underline" onClick={() => void client.auth.signOut()}>
            Sign out
          </button>
        </div>
      }
    >
      <CheckinPage client={client} user={session.user} />
    </Shell>
  )
}

function Shell({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <>
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Pulsar</h1>
        {right}
      </header>
      <main>{children}</main>
    </>
  )
}
