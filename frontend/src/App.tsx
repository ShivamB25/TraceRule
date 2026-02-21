import { useState, useEffect, useCallback } from 'react'
import { AlertCircle } from 'lucide-react'
import type { Rule, Violation, PolicyUploadResponse } from './types'
import { uploadPolicy, getRules, approveRule, rejectRule, getViolations, triggerScan } from './api'
import Header from './components/Header'
import PipelineStrip from './components/PipelineStrip'
import UploadPanel from './components/UploadPanel'
import StatsBar from './components/StatsBar'
import ReviewPanel from './components/ReviewPanel'
import ViolationsPanel from './components/ViolationsPanel'

type TabStatus = 'pending_review' | 'approved' | 'rejected'

export default function App() {
  const [rules, setRules] = useState<Rule[]>([])
  const [violations, setViolations] = useState<Violation[]>([])
  const [activeTab, setActiveTab] = useState<TabStatus>('pending_review')
  const [uploading, setUploading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpload, setLastUpload] = useState<PolicyUploadResponse | null>(null)
  const [lastScanCount, setLastScanCount] = useState<number | null>(null)

  const approvedCount = rules.filter((r) => r.status === 'approved').length
  const extractedCount = lastUpload
    ? rules.filter((r) => r.policy_id === lastUpload.id).length
    : 0

  useEffect(() => {
    Promise.all([getRules(), getViolations()])
      .then(([r, v]) => {
        setRules(r)
        setViolations(v)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load data')
        console.error(err)
      })
  }, [])

  useEffect(() => {
    if (!lastUpload || lastUpload.status !== 'processing') return

    const interval = setInterval(async () => {
      try {
        const newRules = await getRules(undefined, lastUpload.id)
        if (newRules.length > 0) {
          setRules((prev) => [
            ...prev.filter((r) => r.policy_id !== lastUpload.id),
            ...newRules,
          ])
          setLastUpload((prev) => (prev ? { ...prev, status: 'completed' } : null))
        }
      } catch (_error) {
        return
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [lastUpload])

  useEffect(() => {
    const hasNullExplanation = violations.some((v) => v.ai_explanation === null)
    if (!hasNullExplanation) return

    const interval = setInterval(async () => {
      try {
        const fresh = await getViolations()
        setViolations(fresh)
        if (!fresh.some((v) => v.ai_explanation === null)) {
          clearInterval(interval)
        }
      } catch (_error) {
        return
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [violations])

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true)
    setError(null)
    try {
      const result = await uploadPolicy(file)
      setLastUpload(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
    }
  }, [])

  const handleApprove = useCallback(async (id: number) => {
    setError(null)
    try {
      const updated = await approveRule(id)
      setRules((prev) => prev.map((r) => (r.id === id ? updated : r)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve rule')
    }
  }, [])

  const handleReject = useCallback(async (id: number) => {
    setError(null)
    try {
      const updated = await rejectRule(id)
      setRules((prev) => prev.map((r) => (r.id === id ? updated : r)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject rule')
    }
  }, [])

  const handleScan = useCallback(async () => {
    setScanning(true)
    setError(null)
    try {
      const result = await triggerScan()
      setLastScanCount(result.violations_found)
      const fresh = await getViolations()
      setViolations(fresh)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed')
      console.error('Scan failed:', err)
    } finally {
      setScanning(false)
    }
  }, [])

  return (
    <div className="relative min-h-screen overflow-x-clip bg-slate-950 text-white">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_12%_10%,rgba(37,99,235,0.28),transparent_38%),radial-gradient(circle_at_82%_18%,rgba(14,116,144,0.2),transparent_35%),linear-gradient(180deg,#020617_0%,#0b1220_100%)]" />
      <Header
        scanning={scanning}
        lastScanCount={lastScanCount}
        onScan={handleScan}
        approvedCount={approvedCount}
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

        <ReviewPanel
          rules={rules}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onApprove={handleApprove}
          onReject={handleReject}
        />

        <ViolationsPanel violations={violations} rules={rules} />
      </main>
    </div>
  )
}
