import { ShieldCheck, AlertTriangle } from 'lucide-react'
import type { Violation, Rule } from '../types'
import ViolationCard from './ViolationCard'

interface ViolationsPanelProps {
  violations: Violation[]
  rules: Rule[]
}

export default function ViolationsPanel({ violations, rules }: ViolationsPanelProps) {
  return (
    <section className="rounded-xl border border-slate-700/90 bg-slate-900/90 p-6 shadow-[0_24px_60px_-45px_rgba(15,23,42,1)]">
      <div className="mb-4">
        <div className="mb-1 flex items-center gap-3">
          <h2 className="text-lg font-semibold text-white">Compliance Issues</h2>
          {violations.length > 0 && (
            <span className="rounded-full border border-red-500/30 bg-red-500/20 px-2.5 py-0.5 text-xs font-medium text-red-300">
              {violations.length}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500">Latest scan output from approved requirements.</p>
      </div>

      <div className="space-y-4">
        {violations.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-slate-700 py-12 text-slate-500">
            <ShieldCheck className="h-8 w-8" />
            <p className="text-sm">No violations detected</p>
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
