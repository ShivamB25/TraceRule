import { useState } from 'react'
import { Check, X, Loader2 } from 'lucide-react'
import type { Rule } from '../types'
import SeverityBadge from './SeverityBadge'
import SqlBlock from './SqlBlock'

interface RuleCardProps {
  rule: Rule
  onApprove: (id: number) => Promise<void>
  onReject: (id: number) => Promise<void>
}

export default function RuleCard({ rule, onApprove, onReject }: RuleCardProps) {
  const [acting, setActing] = useState<'approve' | 'reject' | null>(null)
  const [exiting, setExiting] = useState(false)

  async function handleAction(action: 'approve' | 'reject') {
    setActing(action)
    try {
      if (action === 'approve') await onApprove(rule.id)
      else await onReject(rule.id)
      setExiting(true)
    } catch {
      setActing(null)
    }
  }

  return (
    <article
      className={`rounded-lg border border-slate-700 bg-slate-800/90 p-6 shadow-[var(--shadow-card)] transition-all duration-300 hover:border-slate-600 ${
        exiting ? 'translate-y-2 opacity-0' : ''
      }`}
    >
      <div className="mb-4 flex items-center gap-3">
        <SeverityBadge severity={rule.severity} />
        <h3 className="text-lg font-semibold text-white">{rule.title}</h3>
      </div>

      <div className="mb-4">
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          Policy Source
        </p>
        <blockquote className="rounded-r-md border-l-2 border-blue-500 bg-slate-900/70 py-2 pl-4 text-sm italic text-slate-300">
          {rule.source_quote}
        </blockquote>
      </div>

      {rule.compiled_sql !== null && (
        <div className="mb-4">
          <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
            Compiled SQL
          </p>
          <SqlBlock sql={rule.compiled_sql} />
        </div>
      )}

      <div className="mb-4">
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
            rule.is_deterministic
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
              : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
          }`}
        >
          {rule.is_deterministic ? 'Deterministic' : 'Requires Human Judgment'}
        </span>
      </div>

      {rule.status === 'pending_review' ? (
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => handleAction('approve')}
            disabled={acting !== null}
            aria-busy={acting === 'approve'}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-6 py-2 text-sm font-medium text-white outline-none transition-all duration-200 hover:bg-emerald-700 focus-visible:ring-4 focus-visible:ring-emerald-500/50 disabled:opacity-50"
          >
            {acting === 'approve' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Check className="h-4 w-4" />
            )}
            Approve
          </button>
          <button
            type="button"
            onClick={() => handleAction('reject')}
            disabled={acting !== null}
            aria-busy={acting === 'reject'}
            className="flex items-center gap-2 rounded-lg border border-red-500/50 px-6 py-2 text-sm font-medium text-red-400 outline-none transition-all duration-200 hover:bg-red-500/10 focus-visible:ring-4 focus-visible:ring-red-500/50 disabled:opacity-50"
          >
            {acting === 'reject' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <X className="h-4 w-4" />
            )}
            Reject
          </button>
        </div>
      ) : (
        <span
          className={`inline-block rounded-full px-3 py-1 text-xs font-medium uppercase ${
            rule.status === 'approved'
              ? 'bg-emerald-500/20 text-emerald-400'
              : 'bg-red-500/20 text-red-400'
          }`}
        >
          {rule.status === 'approved' ? 'Approved' : 'Rejected'}
        </span>
      )}
    </article>
  )
}
