import type { Violation, Rule } from '../types'

interface ViolationCardProps {
  violation: Violation
  rules: Rule[]
}

export default function ViolationCard({ violation, rules }: ViolationCardProps) {
  const rule = rules.find((r) => r.id === violation.rule_id)

  return (
    <article className="rounded-lg border-l-4 border-red-500 bg-slate-800/90 p-5 shadow-[0_20px_40px_-35px_rgba(15,23,42,1)]">
      <div className="mb-3">
        <p className="text-sm font-medium text-white">
          Requirement: {rule?.title ?? `#${violation.rule_id}`}
        </p>
        <p className="text-xs text-slate-500">Record: #{violation.record_pk}</p>
      </div>

      <div className="mb-3">
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          Violating Data
        </p>
        <div className="overflow-x-auto rounded-lg bg-slate-950 p-3">
          <pre className="font-mono text-xs text-slate-300">
            {JSON.stringify(violation.violating_data, null, 2)}
          </pre>
        </div>
      </div>

      {violation.ai_explanation ? (
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
            Explanation
          </p>
          <p className="text-sm text-slate-300">{violation.ai_explanation}</p>
        </div>
      ) : (
        <p className="animate-pulse text-xs italic text-slate-500">Generating explanation...</p>
      )}
    </article>
  )
}
