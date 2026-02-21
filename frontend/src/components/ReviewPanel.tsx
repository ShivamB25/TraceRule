import { ClipboardList, CheckCircle2, XCircle } from 'lucide-react'
import type { Rule } from '../types'
import RuleCard from './RuleCard'

type TabStatus = 'pending_review' | 'approved' | 'rejected'

interface ReviewPanelProps {
  rules: Rule[]
  activeTab: TabStatus
  onTabChange: (tab: TabStatus) => void
  onApprove: (id: number) => Promise<void>
  onReject: (id: number) => Promise<void>
}

const tabs: { status: TabStatus; label: string; icon: typeof ClipboardList }[] = [
  { status: 'pending_review', label: 'Pending Review', icon: ClipboardList },
  { status: 'approved', label: 'Approved', icon: CheckCircle2 },
  { status: 'rejected', label: 'Rejected', icon: XCircle },
]

export default function ReviewPanel({ rules, activeTab, onTabChange, onApprove, onReject }: ReviewPanelProps) {
  const counts: Record<TabStatus, number> = {
    pending_review: rules.filter((r) => r.status === 'pending_review').length,
    approved: rules.filter((r) => r.status === 'approved').length,
    rejected: rules.filter((r) => r.status === 'rejected').length,
  }

  const filtered = rules.filter((r) => r.status === activeTab)

  return (
    <section className="rounded-xl border border-slate-700/90 bg-slate-900/90 p-6 shadow-[0_24px_60px_-45px_rgba(15,23,42,1)]">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-white">Human Review Queue</h2>
        <p className="text-xs text-slate-500">Approve what is precise. Reject what is unclear.</p>
      </div>

      <div role="tablist" aria-label="Requirement status tabs" className="mb-6 flex gap-1 border-b border-slate-700">
        {tabs.map(({ status, label, icon: Icon }) => (
          <button
            key={status}
            type="button"
            onClick={() => onTabChange(status)}
            role="tab"
            aria-selected={activeTab === status}
            className={`flex min-h-11 items-center gap-2 rounded-t-md px-4 py-2.5 text-sm font-medium outline-none transition-all duration-200 focus-visible:bg-slate-800 ${
              activeTab === status
                ? 'border-b-2 border-blue-500 bg-slate-800/70 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
            <span
              className={`rounded-full px-2 py-0.5 text-xs ${
                activeTab === status ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-700 text-slate-400'
              }`}
            >
              {counts[status]}
            </span>
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-slate-700 py-12 text-slate-500">
            <ClipboardList className="h-8 w-8" />
            <p className="text-sm">No {activeTab.replace('_', ' ')} requirements right now</p>
          </div>
        ) : (
          filtered.map((rule) => (
            <RuleCard key={rule.id} rule={rule} onApprove={onApprove} onReject={onReject} />
          ))
        )}
      </div>
    </section>
  )
}
