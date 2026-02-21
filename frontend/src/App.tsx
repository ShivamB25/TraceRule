import { useState, useEffect, useCallback, useRef } from 'react'
import { AlertCircle } from 'lucide-react'
import type { Rule, Violation, PolicyUploadResponse } from './types'
import { uploadPolicy, getRules, approveRule, rejectRule, getViolations, triggerScan } from './api'
import Header from './components/Header'
import PipelineStrip from './components/PipelineStrip'
import UploadPanel from './components/UploadPanel'
import StatsBar from './components/StatsBar'
import ReviewPanel from './components/ReviewPanel'
import ViolationsPanel from './components/ViolationsPanel'
import RequestTimeline, { type TimelineEvent } from './components/RequestTimeline'

type TabStatus = 'pending_review' | 'approved' | 'rejected'

export default function App() {
  const [rules, setRules] = useState<Rule[]>([])
  const [violations, setViolations] = useState<Violation[]>([])
  const [activeTab, setActiveTab] = useState<TabStatus>('pending_review')
  const [selectedViolationStatus, setSelectedViolationStatus] = useState<'all' | 'open' | 'resolved'>('all')
  const [selectedViolationRuleId, setSelectedViolationRuleId] = useState<number | 'all'>('all')
  const [uploading, setUploading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpload, setLastUpload] = useState<PolicyUploadResponse | null>(null)
  const [lastScanCount, setLastScanCount] = useState<number | null>(null)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null)
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([])
  const initialLoadLoggedRef = useRef(false)
  const explanationsPendingRef = useRef(false)

  const pushTimeline = useCallback((event: Omit<TimelineEvent, 'id' | 'at'>) => {
    setTimelineEvents((prev) => {
      const next: TimelineEvent = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        at: new Date(),
        ...event,
      }
      return [next, ...prev].slice(0, 30)
    })
  }, [])

  const approvedCount = rules.filter((r) => r.status === 'approved').length
  const extractedCount = lastUpload
    ? rules.filter((r) => r.policy_id === lastUpload.id).length
    : 0

  const refreshData = useCallback(async (showSpinner = false) => {
    if (showSpinner) setRefreshing(true)
    try {
      const [r, v] = await Promise.all([
        getRules(),
        getViolations(
          selectedViolationRuleId === 'all' ? undefined : selectedViolationRuleId,
          selectedViolationStatus === 'all' ? undefined : selectedViolationStatus,
        ),
      ])
      setRules(r)
      setViolations(v)
      setLastUpdatedAt(new Date())
      if (!initialLoadLoggedRef.current) {
        initialLoadLoggedRef.current = true
        pushTimeline({
          kind: 'info',
          title: 'Dashboard loaded',
          detail: `Fetched ${r.length} rule(s) and ${v.length} violation(s) from backend`,
          request: 'GET /api/v1/rules + GET /api/v1/violations',
          response: `200 OK, rules=${r.length}, violations=${v.length}`,
        })
      } else if (showSpinner) {
        pushTimeline({
          kind: 'info',
          title: 'Manual refresh complete',
          detail: `Now showing ${r.length} rule(s) and ${v.length} violation(s)`,
          request: 'GET /api/v1/rules + GET /api/v1/violations',
          response: `200 OK, rules=${r.length}, violations=${v.length}`,
        })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
      pushTimeline({
        kind: 'error',
        title: 'Data refresh failed',
        detail: err instanceof Error ? err.message : 'Failed to load data',
        request: 'GET /api/v1/rules + GET /api/v1/violations',
      })
      console.error(err)
    } finally {
      if (showSpinner) setRefreshing(false)
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
      request: `GET /api/v1/rules?policy_id=${lastUpload.id} (poll every 3s)`,
    })

    let attempts = 0
    const interval = setInterval(async () => {
      try {
        const newRules = await getRules(undefined, lastUpload.id)
        if (newRules.length > 0) {
          setRules((prev) => [
            ...prev.filter((r) => r.policy_id !== lastUpload.id),
            ...newRules,
          ])
          setLastUpload((prev) => (prev ? { ...prev, status: 'completed' } : null))
          setLastUpdatedAt(new Date())
          setActiveTab('pending_review')
          pushTimeline({
            kind: 'success',
            title: 'Rules generated',
            detail: `${newRules.length} rule(s) compiled for policy #${lastUpload.id}`,
            request: `GET /api/v1/rules?policy_id=${lastUpload.id}`,
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
            request: `GET /api/v1/rules?policy_id=${lastUpload.id}`,
            response: '200 OK, count=0',
          })
          clearInterval(interval)
        }
      } catch (_error) {
        return
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [lastUpload, pushTimeline])

  useEffect(() => {
    const hasNullExplanation = violations.some((v) => v.ai_explanation === null)
    if (!hasNullExplanation) return

    const interval = setInterval(async () => {
      try {
        const fresh = await getViolations(
          selectedViolationRuleId === 'all' ? undefined : selectedViolationRuleId,
          selectedViolationStatus === 'all' ? undefined : selectedViolationStatus,
        )
        setViolations(fresh)
        setLastUpdatedAt(new Date())
        if (!fresh.some((v) => v.ai_explanation === null)) {
          clearInterval(interval)
        }
      } catch (_error) {
        return
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [violations, selectedViolationRuleId, selectedViolationStatus])

  useEffect(() => {
    const hasPending = violations.some((v) => v.ai_explanation === null)
    if (hasPending && !explanationsPendingRef.current) {
      explanationsPendingRef.current = true
      pushTimeline({
        kind: 'info',
        title: 'Generating explanations',
        detail: 'Backend is enriching new violations with AI explanations',
        request: 'GET /api/v1/violations (poll every 5s)',
      })
    } else if (!hasPending && explanationsPendingRef.current) {
      explanationsPendingRef.current = false
      pushTimeline({
        kind: 'success',
        title: 'Explanations ready',
        detail: 'All visible violations now have AI explanations',
        request: 'GET /api/v1/violations',
        response: '200 OK, all ai_explanation fields present',
      })
    }
  }, [pushTimeline, violations])

  const handleUpload = useCallback(async (file: File) => {
    const name = file.name.toLowerCase()
    const allowed = name.endsWith('.pdf') || name.endsWith('.md') || name.endsWith('.markdown')
    if (!allowed) {
      setError('Unsupported file type. Upload a .pdf or .md file.')
      pushTimeline({
        kind: 'warning',
        title: 'Upload blocked',
        detail: `${file.name} is not a supported policy file`,
      })
      return
    }

    setUploading(true)
    setError(null)
    pushTimeline({
      kind: 'info',
      title: 'Upload started',
      detail: file.name,
      request: 'POST /api/v1/policies/upload',
    })
    try {
      const result = await uploadPolicy(file)
      setLastUpload(result)
      setSelectedViolationStatus('all')
      setSelectedViolationRuleId('all')
      pushTimeline({
        kind: 'success',
        title: 'Upload accepted',
        detail: `Policy #${result.id} queued for compilation`,
        request: 'POST /api/v1/policies/upload',
        response: `200 OK, policy_id=${result.id}, status=processing`,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      pushTimeline({
        kind: 'error',
        title: 'Upload failed',
        detail: err instanceof Error ? err.message : 'Upload failed',
        request: 'POST /api/v1/policies/upload',
      })
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
    }
  }, [pushTimeline])

  const handleApprove = useCallback(async (id: number) => {
    setError(null)
    try {
      const updated = await approveRule(id)
      setRules((prev) => prev.map((r) => (r.id === id ? updated : r)))
      setLastUpdatedAt(new Date())
      pushTimeline({
        kind: 'success',
        title: 'Rule approved',
        detail: `Rule #${id} is now eligible for scan`,
        request: `PATCH /api/v1/rules/${id}/approve`,
        response: '200 OK, status=approved',
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve rule')
      pushTimeline({
        kind: 'error',
        title: 'Approve failed',
        detail: err instanceof Error ? err.message : 'Failed to approve rule',
        request: `PATCH /api/v1/rules/${id}/approve`,
      })
    }
  }, [pushTimeline])

  const handleReject = useCallback(async (id: number) => {
    setError(null)
    try {
      const updated = await rejectRule(id)
      setRules((prev) => prev.map((r) => (r.id === id ? updated : r)))
      setLastUpdatedAt(new Date())
      pushTimeline({
        kind: 'warning',
        title: 'Rule rejected',
        detail: `Rule #${id} removed from scan path`,
        request: `PATCH /api/v1/rules/${id}/reject`,
        response: '200 OK, status=rejected',
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject rule')
      pushTimeline({
        kind: 'error',
        title: 'Reject failed',
        detail: err instanceof Error ? err.message : 'Failed to reject rule',
        request: `PATCH /api/v1/rules/${id}/reject`,
      })
    }
  }, [pushTimeline])

  const handleScan = useCallback(async () => {
    setScanning(true)
    setError(null)
    pushTimeline({
      kind: 'info',
      title: 'Manual scan started',
      detail: 'Calling POST /api/v1/scan',
      request: 'POST /api/v1/scan',
    })
    try {
      const result = await triggerScan()
      setLastScanCount(result.violations_found)
      const fresh = await getViolations(
        selectedViolationRuleId === 'all' ? undefined : selectedViolationRuleId,
        selectedViolationStatus === 'all' ? undefined : selectedViolationStatus,
      )
      setViolations(fresh)
      setLastUpdatedAt(new Date())
      pushTimeline({
        kind: result.violations_found > 0 ? 'warning' : 'success',
        title: 'Scan completed',
        detail: `${result.violations_found} new violation(s) found`,
        request: 'POST /api/v1/scan -> GET /api/v1/violations',
        response: `200 OK, violations_found=${result.violations_found}`,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed')
      pushTimeline({
        kind: 'error',
        title: 'Scan failed',
        detail: err instanceof Error ? err.message : 'Scan failed',
        request: 'POST /api/v1/scan',
      })
      console.error('Scan failed:', err)
    } finally {
      setScanning(false)
    }
  }, [pushTimeline, selectedViolationRuleId, selectedViolationStatus])

  const lastUpdatedText = lastUpdatedAt
    ? `Updated ${lastUpdatedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
    : 'Not refreshed yet'

  const handleViolationStatusChange = useCallback((value: 'all' | 'open' | 'resolved') => {
    setSelectedViolationStatus(value)
  }, [])

  const handleViolationRuleChange = useCallback((value: number | 'all') => {
    setSelectedViolationRuleId(value)
  }, [])

  return (
    <div className="relative min-h-screen overflow-x-clip bg-slate-950 text-white">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_12%_10%,rgba(37,99,235,0.28),transparent_38%),radial-gradient(circle_at_82%_18%,rgba(14,116,144,0.2),transparent_35%),linear-gradient(180deg,#020617_0%,#0b1220_100%)]" />
      <Header
        scanning={scanning}
        refreshing={refreshing}
        lastScanCount={lastScanCount}
        onScan={handleScan}
        onRefresh={() => {
          pushTimeline({ kind: 'info', title: 'Manual refresh started', detail: 'Refreshing rules and violations', request: 'GET /api/v1/rules + GET /api/v1/violations' })
          void refreshData(true)
        }}
        approvedCount={approvedCount}
        lastUpdatedText={lastUpdatedText}
      />

      <main className="mx-auto max-w-6xl space-y-8 px-6 py-8 sm:px-8">
        {error && (
          <div
            role="alert"
            className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm font-medium text-red-300"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <PipelineStrip />

        <UploadPanel
          uploading={uploading}
          lastUpload={lastUpload}
          extractedCount={extractedCount}
          onUpload={handleUpload}
        />

        <StatsBar
          totalRules={rules.length}
          approvedRules={rules.filter(r => r.status === 'approved').length}
          pendingRules={rules.filter(r => r.status === 'pending_review').length}
          totalViolations={violations.length}
        />

        <RequestTimeline events={timelineEvents} />

        <ReviewPanel
          rules={rules}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onApprove={handleApprove}
          onReject={handleReject}
        />

        <ViolationsPanel
          violations={violations}
          rules={rules}
          selectedStatus={selectedViolationStatus}
          selectedRuleId={selectedViolationRuleId}
          onStatusChange={handleViolationStatusChange}
          onRuleChange={handleViolationRuleChange}
        />
      </main>
    </div>
  )
}
