import { memo, useMemo, useState } from 'react'
import type { Violation } from '../types'

interface ViolationCardProps {
  violation: Violation
  ruleTitle?: string
}

const PREVIEW_ENTRY_LIMIT = 8

function ViolationCardComponent({ violation, ruleTitle }: ViolationCardProps) {
  const [expanded, setExpanded] = useState(false)

  const previewEntries = useMemo(
    () => Object.entries(violation.violation_data).slice(0, PREVIEW_ENTRY_LIMIT),
    [violation.violation_data],
  )
  const hasHiddenEntries =
    Object.keys(violation.violation_data).length > PREVIEW_ENTRY_LIMIT
  const formattedJson = useMemo(() => {
    if (!expanded) return ''
    return JSON.stringify(violation.violation_data, null, 2)
  }, [expanded, violation.violation_data])

  return (
    <article className="group relative overflow-hidden rounded-xl border border-slate-700/60 border-l-4 border-l-red-500/80 bg-slate-800/60 p-5 shadow-[var(--shadow-card)] transition-all duration-300 hover:border-slate-600 hover:bg-slate-800/90 hover:shadow-[var(--shadow-panel)]">
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-red-500/5 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="mb-3">
        <h3 className="text-sm font-medium text-white">
          Rule: {ruleTitle ?? `#${violation.v3_rule_id}`}
        </h3>
        <p className="text-xs text-slate-500">Record: #{violation.record_id}</p>
      </div>

      <div className="mb-3">
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          Violating Data
        </p>
        <section className="rounded-lg bg-slate-950 p-3" aria-label="Violating record data in JSON format">
          {expanded ? (
            <pre className="overflow-x-auto font-mono text-xs text-slate-300">{formattedJson}</pre>
          ) : (
            <div className="space-y-1 font-mono text-xs text-slate-300">
              {previewEntries.map(([key, value]) => (
                <p key={key} className="break-all">
                  <span className="text-slate-500">{key}:</span> {JSON.stringify(value)}
                </p>
              ))}
              {previewEntries.length === 0 && <p>{'{}'}</p>}
            </div>
          )}
          {(hasHiddenEntries || expanded) && (
            <button
              type="button"
              onClick={() => setExpanded((prev) => !prev)}
              className="mt-2 rounded-md border border-slate-600 bg-slate-900 px-2.5 py-1 text-[11px] text-slate-300"
            >
              {expanded ? 'Collapse data' : 'Expand data'}
            </button>
          )}
        </section>
      </div>

      {violation.verdict_reasoning ? (
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
            Courtroom Verdict
          </p>
          <p className="text-sm text-slate-300">{violation.verdict_reasoning}</p>
          <p className="mt-2 text-xs text-slate-400">
            Confidence: {violation.confidence_score !== null ? `${(violation.confidence_score * 100).toFixed(0)}%` : '100% (deterministic)'}
          </p>
        </div>
      ) : (
        <p className="text-xs italic text-slate-500">Deterministic violation (no courtroom reasoning required).</p>
      )}
    </article>
  )
}

const ViolationCard = memo(ViolationCardComponent)

export default ViolationCard
