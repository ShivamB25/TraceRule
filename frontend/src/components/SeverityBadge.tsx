import { memo } from 'react'
import type { RuleSeverity } from '../types'

interface SeverityBadgeProps {
  severity: RuleSeverity
}

const styles: Record<RuleSeverity, string> = {
  CRITICAL: 'bg-red-500/20 text-red-400 border border-red-500/30',
  HIGH: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  MEDIUM: 'bg-yellow-500/30 text-yellow-200 border border-yellow-400/40',
  LOW: 'bg-slate-500/30 text-slate-200 border border-slate-400/40',
}

function SeverityBadge({ severity }: SeverityBadgeProps) {
  const cls = styles[severity]
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-medium uppercase ${cls}`}>
      {severity}
    </span>
  )
}

export default memo(SeverityBadge)
