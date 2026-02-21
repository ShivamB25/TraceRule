import { Radar, Loader2, Activity, RefreshCw } from 'lucide-react'

interface HeaderProps {
  scanning: boolean
  refreshing: boolean
  lastScanCount: number | null
  onScan: () => void
  onRefresh: () => void
  approvedCount: number
  lastUpdatedText: string
}

export default function Header({
  scanning,
  refreshing,
  lastScanCount,
  onScan,
  onRefresh,
  approvedCount,
  lastUpdatedText,
}: HeaderProps) {
  const statusText =
    lastScanCount !== null
      ? lastScanCount > 0
        ? `${lastScanCount} violation${lastScanCount > 1 ? 's' : ''} found`
        : 'All clear'
      : 'Ready'

  const statusColor =
    lastScanCount !== null
      ? lastScanCount > 0
        ? 'bg-red-500/20 text-red-400 border-red-500/30'
        : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
      : 'bg-slate-500/20 text-slate-400 border-slate-500/30'

  return (
    <header className="sticky top-0 z-50 border-b border-slate-700/80 bg-slate-900/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4 sm:px-8">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-lg border border-blue-500/30 bg-blue-500/10 p-2 text-blue-300">
            <Radar className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">
              TraceRule <span className="font-normal text-slate-400">Data Policy Compliance Agent</span>
            </h1>
            <p className="text-xs text-slate-400">Upload policy PDFs. Approve SQL checks. Detect violations in company data with deterministic scans.</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400" aria-live="polite">{lastUpdatedText}</span>
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${statusColor}`}>
            <Activity className="h-3.5 w-3.5" />
            {statusText}
          </span>

          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            aria-busy={refreshing}
            aria-label={refreshing ? 'Refreshing dashboard data' : 'Refresh dashboard data'}
            className="flex min-h-11 items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200 outline-none transition-all duration-200 hover:bg-slate-700 focus-visible:ring-4 focus-visible:ring-slate-500/40 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>

          <button
            type="button"
            onClick={onScan}
            disabled={scanning || approvedCount === 0}
            aria-busy={scanning}
            aria-label={scanning ? 'Running deterministic scan' : 'Trigger deterministic scan'}
            className="flex min-h-11 items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_24px_-12px_rgba(59,130,246,0.7)] outline-none transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-500 focus-visible:ring-4 focus-visible:ring-blue-500/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {scanning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Radar className="h-4 w-4" />
            )}
            {scanning ? 'Scanning...' : 'Trigger Scan'}
          </button>
        </div>
      </div>
    </header>
  )
}
