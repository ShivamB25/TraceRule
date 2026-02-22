import type { Violation, Rule } from '../types'

interface ViolationCardProps {
  violation: Violation
  rules: Rule[]
}

export default function ViolationCard({ violation, rules }: ViolationCardProps) {
  const rule = rules.find((r) => r.id === violation.v3_rule_id)

  return (
    <article className="group relative overflow-hidden rounded-xl border border-slate-700/60 border-l-4 border-l-red-500/80 bg-slate-800/60 p-5 shadow-[var(--shadow-card)] transition-all duration-300 hover:border-slate-600 hover:bg-slate-800/90 hover:shadow-[var(--shadow-panel)]">
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-red-500/5 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="mb-3">
        <h3 className="text-sm font-medium text-white">
          Rule: {rule?.title ?? `#${violation.v3_rule_id}`}
        </h3>
        <p className="text-xs text-slate-500">Record: #{violation.record_id}</p>
      </div>

      <div className="mb-3">
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          Violating Data
        </p>
        <section className="overflow-x-auto rounded-lg bg-slate-950 p-3" aria-label="Violating record data in JSON format">
          <pre className="font-mono text-xs text-slate-300">
            {JSON.stringify(violation.violation_data, null, 2)}
          </pre>
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
