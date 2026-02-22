import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { approveRule, getRules, getViolations, rejectRule, triggerScan, uploadPolicy } from './api'
import type {
  PolicyUploadResponse,
  Rule,
  RuleStatus,
  Violation,
  ViolationStatusFilter,
} from './types'
import ErrorBoundary from './components/ErrorBoundary'
import Header from './components/Header'
import PipelineStrip from './components/PipelineStrip'
import RequestTimeline, { type TimelineEvent } from './components/RequestTimeline'
import ReviewPanel from './components/ReviewPanel'
import StatsBar from './components/StatsBar'
import UploadPanel from './components/UploadPanel'
import ViolationsPanel from './components/ViolationsPanel'

type TabStatus = RuleStatus

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

function formatTime(date: Date | null): string {
  if (!date) return 'Not refreshed yet'
  return `Updated ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
}

export default function App() {
  const [rules, setRules] = useState<Rule[]>([])
  const [violations, setViolations] = useState<Violation[]>([])
  const [activeTab, setActiveTab] = useState<TabStatus>('pending_review')
  const [selectedViolationStatus, setSelectedViolationStatus] = useState<ViolationStatusFilter>('all')
  const [selectedViolationRuleId, setSelectedViolationRuleId] = useState<number | 'all'>('all')
  const [uploading, setUploading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [loadingInitial, setLoadingInitial] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpload, setLastUpload] = useState<PolicyUploadResponse | null>(null)
  const [lastScanCount, setLastScanCount] = useState<number | null>(null)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null)
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([])
  const [liveAnnouncement, setLiveAnnouncement] = useState('')
  const initialLoadLoggedRef = useRef(false)

  const announce = useCallback((message: string): void => {
    setLiveAnnouncement('')
    window.setTimeout(() => setLiveAnnouncement(message), 80)
  }, [])

  const pushTimeline = useCallback((event: Omit<TimelineEvent, 'id' | 'at'>): void => {
    setTimelineEvents((prev) => {
      const next: TimelineEvent = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        at: new Date(),
        ...event,
      }
      return [next, ...prev].slice(0, 30)
    })
    announce(event.title)
  }, [announce])

  const approvedCount = rules.filter((rule) => rule.status === 'approved').length
  const extractedCount = lastUpload ? rules.filter((rule) => rule.policy_id === lastUpload.id).length : 0

  const refreshData = useCallback(async (showSpinner = false): Promise<void> => {
    if (showSpinner) setRefreshing(true)
    try {
      const [nextRules, nextViolations] = await Promise.all([
        getRules(),
        getViolations(
          selectedViolationRuleId === 'all' ? undefined : selectedViolationRuleId,
          selectedViolationStatus === 'all' ? undefined : selectedViolationStatus,
        ),
      ])
      setRules(nextRules)
      setViolations(nextViolations)
      setLastUpdatedAt(new Date())
      if (!initialLoadLoggedRef.current) {
        initialLoadLoggedRef.current = true
        pushTimeline({
          kind: 'info',
          title: 'Dashboard loaded',
          detail: `Fetched ${nextRules.length} rule(s) and ${nextViolations.length} violation(s) from backend`,
          request: 'GET /api/v3/rules + GET /api/v3/violations',
          response: `200 OK, rules=${nextRules.length}, violations=${nextViolations.length}`,
        })
      } else if (showSpinner) {
        pushTimeline({
          kind: 'info',
          title: 'Manual refresh complete',
          detail: `Now showing ${nextRules.length} rule(s) and ${nextViolations.length} violation(s)`,
          request: 'GET /api/v3/rules + GET /api/v3/violations',
          response: `200 OK, rules=${nextRules.length}, violations=${nextViolations.length}`,
        })
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load data'
      setError(message)
      pushTimeline({
        kind: 'error',
        title: 'Data refresh failed',
        detail: message,
        request: 'GET /api/v3/rules + GET /api/v3/violations',
      })
    } finally {
      if (showSpinner) setRefreshing(false)
      setLoadingInitial(false)
    }
  }, [pushTimeline, selectedViolationRuleId, selectedViolationStatus])

  useEffect(() => {
    void refreshData()
  }, [refreshData])

  useEffect(() => {
    if (!lastUpload || lastUpload.status !== 'processing') return

    pushTimeline({
      kind: 'info',
      title: 'Compilation started',
      detail: `Polling rules for policy #${lastUpload.id}`,
      request: `GET /api/v3/rules?policy_id=${lastUpload.id} (poll every 3s)`,
    })

    let attempts = 0
    const interval = setInterval(async () => {
      try {
        const newRules = await getRules(undefined, lastUpload.id)
        if (newRules.length > 0) {
          setRules((prev) => [...prev.filter((rule) => rule.policy_id !== lastUpload.id), ...newRules])
          setLastUpload((prev) => (prev ? { ...prev, status: 'completed' } : null))
          setLastUpdatedAt(new Date())
          setActiveTab('pending_review')
          pushTimeline({
            kind: 'success',
            title: 'Rules generated',
            detail: `${newRules.length} rule(s) compiled for policy #${lastUpload.id}`,
            request: `GET /api/v3/rules?policy_id=${lastUpload.id}`,
            response: `200 OK, count=${newRules.length}`,
          })
          clearInterval(interval)
          return
        }
        attempts += 1
        if (attempts >= 40) {
          setError('Compilation is taking longer than expected. You can refresh and check rules manually.')
          pushTimeline({
            kind: 'warning',
            title: 'Compilation still running',
            detail: `No rules yet for policy #${lastUpload.id} after 2 minutes`,
            request: `GET /api/v3/rules?policy_id=${lastUpload.id}`,
            response: '200 OK, count=0',
          })
          clearInterval(interval)
        }
      } catch {
        attempts += 1
        if (attempts >= 40) clearInterval(interval)
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [lastUpload, pushTimeline])

  async function handleUpload(file: File): Promise<void> {
    const name = file.name.toLowerCase()
    const allowed = name.endsWith('.pdf') || name.endsWith('.md') || name.endsWith('.markdown')
    if (!allowed) {
      const message = 'Unsupported file type. Upload a .pdf or .md file.'
      setError(message)
      pushTimeline({
        kind: 'warning',
        title: 'Upload blocked',
        detail: `${file.name} is not a supported policy file`,
      })
      return
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      const message = 'File is too large. Upload a file under 10 MB.'
      setError(message)
      pushTimeline({ kind: 'warning', title: 'Upload blocked', detail: `${file.name} exceeds size limit` })
      return
    }

    setUploading(true)
    setError(null)
    pushTimeline({ kind: 'info', title: 'Upload started', detail: file.name, request: 'POST /api/v3/policies/upload' })
    try {
      const result = await uploadPolicy(file)
      setLastUpload(result)
      setSelectedViolationStatus('all')
      setSelectedViolationRuleId('all')
      pushTimeline({
        kind: 'success',
        title: 'Upload accepted',
        detail: `Policy #${result.id} queued for compilation`,
        request: 'POST /api/v3/policies/upload',
        response: `200 OK, policy_id=${result.id}, status=processing`,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setError(message)
      pushTimeline({ kind: 'error', title: 'Upload failed', detail: message, request: 'POST /api/v3/policies/upload' })
    } finally {
      setUploading(false)
    }
  }

  async function handleApprove(id: number): Promise<void> {
    setError(null)
    try {
      const updated = await approveRule(id)
      setRules((prev) => prev.map((rule) => (rule.id === id ? updated : rule)))
      setLastUpdatedAt(new Date())
      pushTimeline({
        kind: 'success',
        title: 'Rule approved',
        detail: `Rule #${id} is now eligible for scan`,
        request: `PATCH /api/v3/rules/${id}/approve`,
        response: '200 OK, status=approved',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to approve rule'
      setError(message)
      pushTimeline({ kind: 'error', title: 'Approve failed', detail: message, request: `PATCH /api/v3/rules/${id}/approve` })
    }
  }

  async function handleReject(id: number): Promise<void> {
    setError(null)
    try {
      const updated = await rejectRule(id)
      setRules((prev) => prev.map((rule) => (rule.id === id ? updated : rule)))
      setLastUpdatedAt(new Date())
      pushTimeline({
        kind: 'warning',
        title: 'Rule rejected',
        detail: `Rule #${id} removed from scan path`,
        request: `PATCH /api/v3/rules/${id}/reject`,
        response: '200 OK, status=rejected',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reject rule'
      setError(message)
      pushTimeline({ kind: 'error', title: 'Reject failed', detail: message, request: `PATCH /api/v3/rules/${id}/reject` })
    }
  }

  async function handleScan(): Promise<void> {
    setScanning(true)
    setError(null)
    pushTimeline({ kind: 'info', title: 'Manual scan started', detail: 'Calling POST /api/v3/scan', request: 'POST /api/v3/scan' })
    try {
      const result = await triggerScan()
      setLastScanCount(result.total)
      const fresh = await getViolations(
        selectedViolationRuleId === 'all' ? undefined : selectedViolationRuleId,
        selectedViolationStatus === 'all' ? undefined : selectedViolationStatus,
      )
      setViolations(fresh)
      setLastUpdatedAt(new Date())
      pushTimeline({
        kind: result.total > 0 ? 'warning' : 'success',
        title: 'Scan completed',
        detail: `${result.total} total violation(s): deterministic=${result.deterministic_violations}, semantic=${result.semantic_violations}`,
        request: 'POST /api/v3/scan -> GET /api/v3/violations',
        response: `200 OK, total=${result.total}`,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Scan failed'
      setError(message)
      pushTimeline({ kind: 'error', title: 'Scan failed', detail: message, request: 'POST /api/v3/scan' })
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-x-clip bg-slate-950 text-white">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_12%_10%,rgba(37,99,235,0.15),transparent_38%),radial-gradient(circle_at_82%_18%,rgba(14,116,144,0.12),transparent_35%),linear-gradient(180deg,#020617_0%,#0b1220_100%)]" />
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-slate-800 focus:px-3 focus:py-2 focus:text-sm focus:text-white focus:ring-2 focus:ring-blue-400"
      >
        Skip to main content
      </a>
      <Header
        scanning={scanning}
        refreshing={refreshing}
        lastScanCount={lastScanCount}
        onScan={handleScan}
        onRefresh={() => {
          pushTimeline({
            kind: 'info',
            title: 'Manual refresh started',
            detail: 'Refreshing rules and violations',
            request: 'GET /api/v3/rules + GET /api/v3/violations',
          })
          void refreshData(true)
        }}
        approvedCount={approvedCount}
        lastUpdatedText={formatTime(lastUpdatedAt)}
      />

      <main id="main-content" tabIndex={-1} className="mx-auto max-w-6xl space-y-8 px-6 py-8 sm:px-8">
        <span aria-live="polite" aria-atomic="true" className="sr-only">
          {liveAnnouncement}
        </span>
        {error && (
          <div
            role="alert"
            aria-live="assertive"
            aria-atomic="true"
            className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm font-medium text-red-300"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <PipelineStrip />

        <UploadPanel uploading={uploading} lastUpload={lastUpload} extractedCount={extractedCount} onUpload={handleUpload} />

        <StatsBar
          totalRules={rules.length}
          approvedRules={rules.filter((rule) => rule.status === 'approved').length}
          pendingRules={rules.filter((rule) => rule.status === 'pending_review').length}
          totalViolations={violations.length}
          loading={loadingInitial}
        />

        <RequestTimeline events={timelineEvents} />

        <ErrorBoundary>
          <ReviewPanel
            rules={rules}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onApprove={handleApprove}
            onReject={handleReject}
            loading={loadingInitial}
          />

          <ViolationsPanel
            violations={violations}
            rules={rules}
            selectedStatus={selectedViolationStatus}
            selectedRuleId={selectedViolationRuleId}
            onStatusChange={setSelectedViolationStatus}
            onRuleChange={setSelectedViolationRuleId}
            loading={loadingInitial}
          />
        </ErrorBoundary>
      </main>
    </div>
  )
}
