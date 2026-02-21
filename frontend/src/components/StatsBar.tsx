import { FileText, CheckCircle2, Radar, AlertTriangle } from 'lucide-react'

interface StatsBarProps {
  totalRules: number
  approvedRules: number
  pendingRules: number
  totalViolations: number
}

export default function StatsBar({ totalRules, approvedRules, pendingRules, totalViolations }: StatsBarProps) {
  if (totalRules === 0) return null

  const stats = [
    { label: 'Total Rules', value: totalRules, icon: FileText, color: 'text-blue-400' },
    { label: 'Approved', value: approvedRules, icon: CheckCircle2, color: 'text-emerald-400' },
    { label: 'Pending', value: pendingRules, icon: Radar, color: 'text-yellow-400' },
    { label: 'Violations', value: totalViolations, icon: AlertTriangle, color: totalViolations > 0 ? 'text-red-400' : 'text-slate-500' },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {stats.map(({ label, value, icon: Icon, color }) => (
        <div
          key={label}
          className="flex items-center gap-3 rounded-lg border border-slate-700/80 bg-slate-800/60 px-4 py-3"
        >
          <Icon className={`h-5 w-5 ${color}`} />
          <div>
            <p className="text-lg font-bold text-white">{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
