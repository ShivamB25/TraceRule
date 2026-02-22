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
  loading: boolean
}

export default function ViolationsPanel({
  violations,
  rules,
  selectedStatus,
  selectedRuleId,
  onStatusChange,
  onRuleChange,
  loading,
}: ViolationsPanelProps) {
  return (
    <section className="rounded-xl border border-slate-700/90 bg-slate-900/90 p-6 shadow-[var(--shadow-panel)]">
      <div className="mb-4 space-y-3">
        <div className="mb-1 flex items-center gap-3">
          <h2 className="text-lg font-semibold text-white">Detected Violations</h2>
          {violations.length > 0 && (
            <span className="rounded-full border border-red-500/30 bg-red-500/20 px-2.5 py-0.5 text-xs font-medium text-red-300">
              {violations.length}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500">Scan results from V3 engine: deterministic SQL checks plus courtroom-evaluated semantic violations.</p>
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="violation-status-filter" className="flex items-center gap-2 text-xs text-slate-400">
            Status
            <select
              id="violation-status-filter"
              value={selectedStatus}
              onChange={(e) => onStatusChange(e.target.value as 'all' | 'open' | 'resolved')}
              className="rounded-md border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-200 outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
            >
              <option value="all">All</option>
              <option value="open">Open</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>

          <label htmlFor="violation-rule-filter" className="flex items-center gap-2 text-xs text-slate-400">
            V3 Rule
            <select
              id="violation-rule-filter"
              value={selectedRuleId === 'all' ? 'all' : String(selectedRuleId)}
              onChange={(e) =>
                onRuleChange(e.target.value === 'all' ? 'all' : Number(e.target.value))
              }
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-200 outline-none focus-visible:ring-2 focus-visible:ring-blue-400 sm:max-w-72"
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

      <div className="space-y-4" aria-live="polite">
        {loading ? (
          ['violation-a', 'violation-b'].map((item) => (
            <div key={item} className="animate-pulse rounded-lg border border-slate-700 bg-slate-800/40 p-5">
              <div className="h-4 w-1/3 rounded bg-slate-700/50" />
              <div className="mt-3 h-4 w-full rounded bg-slate-700/40" />
              <div className="mt-2 h-4 w-4/5 rounded bg-slate-700/30" />
            </div>
          ))
        ) : violations.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-slate-700 py-12 text-slate-500">
            <ShieldCheck className="h-8 w-8" />
            <p className="text-sm">No violations detected — all records compliant</p>
            <p className="text-xs text-slate-400">Run a manual scan after approving one or more rules.</p>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5">
              <AlertTriangle className="h-4 w-4 text-red-300" />
              <p className="text-sm text-red-300">
                {violations.length} violation{violations.length !== 1 ? 's' : ''} found
              </p>
            </div>
            {violations.map((v, index) => (
              <div key={v.id} className="animate-fade-slide" style={{ animationDelay: `${index * 45}ms` }}>
                <ViolationCard violation={v} rules={rules} />
              </div>
            ))}
          </>
        )}
      </div>
    </section>
  )
}
