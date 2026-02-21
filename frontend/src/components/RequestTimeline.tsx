import { useState } from 'react'
import { TerminalSquare } from 'lucide-react'

type TimelineKind = 'info' | 'success' | 'warning' | 'error'

export interface TimelineEvent {
  id: string
  at: Date
  kind: TimelineKind
  title: string
  detail?: string
  request?: string
  response?: string
}

interface RequestTimelineProps {
  events: TimelineEvent[]
}

const colorByKind: Record<TimelineKind, string> = {
  info: 'bg-blue-400',
  success: 'bg-emerald-400',
  warning: 'bg-amber-400',
  error: 'bg-red-400',
}

export default function RequestTimeline({ events }: RequestTimelineProps) {
  const [technicalMode, setTechnicalMode] = useState(false)

  return (
    <section className="rounded-xl border border-slate-700/90 bg-slate-900/90 p-6 shadow-[0_24px_60px_-45px_rgba(15,23,42,1)]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Compliance Lifecycle Timeline</h2>
          <p className="text-xs text-slate-400">Live trace of policy ingestion, approval actions, scan execution, and violation enrichment.</p>
        </div>
        <button
          type="button"
          onClick={() => setTechnicalMode((prev) => !prev)}
          aria-pressed={technicalMode}
          className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium outline-none transition-colors ${
            technicalMode
              ? 'border-blue-500/40 bg-blue-500/15 text-blue-300'
              : 'border-slate-600 bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
        >
          <TerminalSquare className="h-3.5 w-3.5" />
          {technicalMode ? 'Technical mode on' : 'Technical mode off'}
        </button>
      </div>

      {events.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-700 py-8 text-center text-sm text-slate-500">
          No events yet. Upload a policy file to start the trace.
        </div>
      ) : (
          <ol className="space-y-3" aria-live="polite" aria-label="Timeline events">
          {events.map((event) => (
            <li key={event.id} className="rounded-lg border border-slate-700/80 bg-slate-800/60 px-4 py-3">
              <div className="flex items-start gap-3">
                <span className={`mt-1.5 inline-block h-2.5 w-2.5 rounded-full ${colorByKind[event.kind]}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-white">{event.title}</p>
                    <span className="text-xs text-slate-500">
                      {event.at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  {event.detail && <p className="mt-1 text-xs text-slate-400">{event.detail}</p>}
                  {technicalMode && (event.request || event.response) && (
                    <div className="mt-2 space-y-1 rounded-md border border-slate-700 bg-slate-900/70 p-2">
                      {event.request && (
                        <p className="font-mono text-[11px] text-slate-300">
                          <span className="text-slate-500">request:</span> {event.request}
                        </p>
                      )}
                      {event.response && (
                        <p className="font-mono text-[11px] text-slate-300">
                          <span className="text-slate-500">response:</span> {event.response}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
