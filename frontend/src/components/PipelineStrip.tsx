import { memo } from 'react'
import { FileText, UserCheck, Radar } from 'lucide-react'

const steps = [
  { num: 1, title: 'Policy PDF Ingest', desc: 'AST + SQL auto-heal', icon: FileText, color: 'text-blue-400', border: 'border-blue-500/30', bg: 'bg-blue-500/10' },
  { num: 2, title: 'Human Approval Gate', desc: 'Auditable logic + SQL', icon: UserCheck, color: 'text-yellow-400', border: 'border-yellow-500/30', bg: 'bg-yellow-500/10' },
  { num: 3, title: 'V3 Enforcement', desc: 'SQL + courtroom', icon: Radar, color: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' },
] as const

function PipelineStrip() {
  return (
    <section aria-label="Compliance pipeline" className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center sm:gap-0">
      {steps.map((step, i) => (
        <div key={step.num} className="flex items-center sm:flex-1">
          <div className={`flex w-full items-center gap-3 rounded-lg border ${step.border} ${step.bg} px-4 py-3`}>
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${step.bg} ${step.color}`}>
              <step.icon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-white">{step.title}</p>
              <p className={`text-xs ${step.color}`}>{step.desc}</p>
            </div>
          </div>
          {i < steps.length - 1 && (
            <>
              <div className="hidden h-px w-6 bg-slate-700 sm:block" />
              <div className="mx-auto block h-4 w-px bg-slate-700 sm:hidden" />
            </>
          )}
        </div>
      ))}
    </section>
  )
}

export default memo(PipelineStrip)
