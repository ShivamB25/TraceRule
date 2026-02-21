import { ShieldCheck, AlertTriangle } from 'lucide-react'
import type { Violation, Rule } from '../types'
import ViolationCard from './ViolationCard'

interface ViolationsPanelProps {
  violations: Violation[]
  rules: Rule[]
  selectedStatus: 'all' | 'open' | 'resolved'
  selectedRuleId: number | 'all'
  onStatusChange: (value: 'all' | 'open' | 'resolved') => void
  onRuleChange: (value: number | 'all') => void
}

export default function ViolationsPanel({
  violations,
  rules,
  selectedStatus,
  selectedRuleId,
  onStatusChange,
  onRuleChange,
}: ViolationsPanelProps) {
  return (
    <section className="rounded-xl border border-slate-700/90 bg-slate-900/90 p-6 shadow-[0_24px_60px_-45px_rgba(15,23,42,1)]">
      <div className="mb-4 space-y-3">
        <div className="mb-1 flex items-center gap-3">
          <h2 className="text-lg font-semibold text-white">Detected Violations</h2>
          {violations.length > 0 && (
            <span className="rounded-full border border-red-500/30 bg-red-500/20 px-2.5 py-0.5 text-xs font-medium text-red-300">
              {violations.length}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500">Scan results — SQL executed against the transactions database. Zero LLM.</p>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-400">
            Status
            <select
              value={selectedStatus}
              onChange={(e) => onStatusChange(e.target.value as 'all' | 'open' | 'resolved')}
              className="rounded-md border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-200 outline-none"
            >
              <option value="all">All</option>
              <option value="open">Open</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>

          <label className="flex items-center gap-2 text-xs text-slate-400">
            Rule
            <select
              value={selectedRuleId === 'all' ? 'all' : String(selectedRuleId)}
              onChange={(e) =>
                onRuleChange(e.target.value === 'all' ? 'all' : Number(e.target.value))
              }
              className="max-w-72 rounded-md border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-200 outline-none"
            >
              <option value="all">All rules</option>
              {rules.map((rule) => (
                <option key={rule.id} value={rule.id}>
                  #{rule.id} {rule.title}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="space-y-4">
        {violations.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-slate-700 py-12 text-slate-500">
            <ShieldCheck className="h-8 w-8" />
            <p className="text-sm">No violations detected — all records compliant</p>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5">
              <AlertTriangle className="h-4 w-4 text-red-300" />
              <p className="text-sm text-red-300">
                {violations.length} violation{violations.length !== 1 ? 's' : ''} found
              </p>
            </div>
            {violations.map((v) => (
              <ViolationCard key={v.id} violation={v} rules={rules} />
            ))}
          </>
        )}
      </div>
    </section>
  )
}
