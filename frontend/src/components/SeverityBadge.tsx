interface SeverityBadgeProps {
  severity: string
}

const styles: Record<string, string> = {
  CRITICAL: 'bg-red-500/20 text-red-400 border border-red-500/30',
  HIGH: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  LOW: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
}

export default function SeverityBadge({ severity }: SeverityBadgeProps) {
  const cls = styles[severity] ?? styles.MEDIUM
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-medium uppercase ${cls}`}>
      {severity}
    </span>
  )
}
