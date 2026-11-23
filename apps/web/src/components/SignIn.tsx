import type { SupabaseClient } from '@supabase/supabase-js'
import { type FormEvent, useState } from 'react'

export function SignIn({ client }: { client: SupabaseClient }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setPending(true)
    setError(null)
    const { error } = await client.auth.signInWithPassword({ email: email.trim(), password })
    // On success, onAuthStateChange swaps this screen out.
    if (error) setError(error.message)
    setPending(false)
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-sm space-y-4 rounded-lg border border-slate-200 bg-white p-6">
      <div>
        <h2 className="text-lg font-semibold">Sign in</h2>
        <p className="text-sm text-slate-600">Use the demo account for your fictional crew profile.</p>
      </div>
      <label className="block text-sm">
        <span className="font-medium">Email</span>
        <input
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        <span className="font-medium">Password</span>
        <input
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {pending ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  )
}
