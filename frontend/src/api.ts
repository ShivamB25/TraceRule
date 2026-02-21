import type { PolicyUploadResponse, Rule, Violation, ScanResult } from './types'

const BASE = '/api/v1'

export async function uploadPolicy(file: File): Promise<PolicyUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/policies/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function getRules(status?: string, policyId?: number): Promise<Rule[]> {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (policyId) params.set('policy_id', String(policyId))
  const res = await fetch(`${BASE}/rules?${params}`)
  if (!res.ok) throw new Error(`Failed to fetch rules: ${res.status}`)
  return res.json()
}

export async function approveRule(id: number): Promise<Rule> {
  const res = await fetch(`${BASE}/rules/${id}/approve`, { method: 'PATCH' })
  if (!res.ok) throw new Error(`Failed to approve rule: ${res.status}`)
  return res.json()
}

export async function rejectRule(id: number): Promise<Rule> {
  const res = await fetch(`${BASE}/rules/${id}/reject`, { method: 'PATCH' })
  if (!res.ok) throw new Error(`Failed to reject rule: ${res.status}`)
  return res.json()
}

export async function getViolations(): Promise<Violation[]> {
  const res = await fetch(`${BASE}/violations`)
  if (!res.ok) throw new Error(`Failed to fetch violations: ${res.status}`)
  return res.json()
}

export async function triggerScan(): Promise<ScanResult> {
  const res = await fetch(`${BASE}/scan`, { method: 'POST' })
  if (!res.ok) throw new Error(`Scan failed: ${res.status}`)
  return res.json()
}
