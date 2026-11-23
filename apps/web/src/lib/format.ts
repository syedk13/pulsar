// All mission data is on UTC (the synthetic mission clock), so timestamps are shown in UTC.

export function formatUtc(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)} UTC`
}

export function utcDate(iso: string | Date): string {
  return (typeof iso === 'string' ? new Date(iso) : iso).toISOString().slice(0, 10)
}
