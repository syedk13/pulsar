import { MOOD_LABELS } from '../checkin/validation'
import { formatUtc } from '../lib/format'
import type { HealthCheckin } from '../lib/types'

export function ProvenanceBadge({ row }: { row: HealthCheckin }) {
  if (row.is_simulated || row.source === 'synthetic') {
    return (
      <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-900">
        Simulated · synthetic
      </span>
    )
  }
  const label = row.source === 'self_report' ? 'Self-reported' : 'Wearable'
  return <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-900">{label}</span>
}

export function Value({ value, unit }: { value: number | null; unit: string }) {
  if (value === null) return <span className="text-slate-400 italic">missing</span>
  return (
    <span>
      {value} <span className="text-slate-500">{unit}</span>
    </span>
  )
}

interface Props {
  rows: HealthCheckin[]
  loading: boolean
  error: string | null
  highlightId: string | null
  onRetry: () => void
}

export function CheckinHistory({ rows, loading, error, highlightId, onRetry }: Props) {
  if (error) {
    return (
      <p role="alert" className="text-sm text-red-700">
        {error}{' '}
        <button type="button" onClick={onRetry} className="underline">
          Retry
        </button>
      </p>
    )
  }
  if (!loading && rows.length === 0) {
    return <p className="text-sm text-slate-600">No check-ins yet.</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[36rem] text-left text-sm" aria-busy={loading}>
        <thead className="border-b border-slate-200 text-slate-600">
          <tr>
            <th className="py-2 pr-3 font-medium">Recorded</th>
            <th className="py-2 pr-3 font-medium">Sleep</th>
            <th className="py-2 pr-3 font-medium">Resting HR</th>
            <th className="py-2 pr-3 font-medium">Mood</th>
            <th className="py-2 font-medium">Source</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              className={`border-b border-slate-100 ${row.id === highlightId ? 'bg-emerald-50' : ''}`}
            >
              <td className="py-2 pr-3 whitespace-nowrap">{formatUtc(row.recorded_at)}</td>
              <td className="py-2 pr-3">
                <Value value={row.sleep_duration_hours} unit="h" />
              </td>
              <td className="py-2 pr-3">
                <Value value={row.resting_heart_rate} unit="bpm" />
              </td>
              <td className="py-2 pr-3">
                {row.mood_rating === null ? (
                  <Value value={null} unit="" />
                ) : (
                  <span>
                    {row.mood_rating} <span className="text-slate-500">{MOOD_LABELS[row.mood_rating]}</span>
                  </span>
                )}
              </td>
              <td className="py-2">
                <ProvenanceBadge row={row} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {loading && <p className="mt-2 text-xs text-slate-500">Refreshing…</p>}
    </div>
  )
}
