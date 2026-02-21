type TimelineKind = 'info' | 'success' | 'warning' | 'error'

export interface TimelineEvent {
  id: string
  at: Date
  kind: TimelineKind
  title: string
  detail?: string
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
  return (
    <section className="rounded-xl border border-slate-700/90 bg-slate-900/90 p-6 shadow-[0_24px_60px_-45px_rgba(15,23,42,1)]">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-white">Live Request Timeline</h2>
        <p className="text-xs text-slate-500">Frontend actions and backend API lifecycle in real time.</p>
      </div>

      {events.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-700 py-8 text-center text-sm text-slate-500">
          No events yet. Upload a policy PDF to start the trace.
        </div>
      ) : (
        <ol className="space-y-3">
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
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
