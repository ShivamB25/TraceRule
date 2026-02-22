import { z } from 'zod'
import {
  policyUploadResponseSchema,
  ruleSchema,
  rulesSchema,
  scanResultSchema,
  violationsSchema,
} from './types'
import type {
  PolicyUploadResponse,
  Rule,
  RuleStatus,
  ScanResult,
  Violation,
  ViolationStatus,
} from './types'

const BASE = '/api/v3'

async function parseJsonResponse<T>(res: Response, parser: (data: unknown) => T): Promise<T> {
  let data: unknown
  try {
    data = await res.json()
  } catch (err) {
    throw new Error(`Invalid JSON response: ${err instanceof Error ? err.message : 'Unknown error'}`)
  }

  try {
    return parser(data)
  } catch (err) {
    if (err instanceof z.ZodError) {
      const issues = err.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('; ')
      throw new Error(`Response validation failed: ${issues}`)
    }
    throw err
  }
}

/**
 * Uploads a policy document for background compilation.
 * @param file File selected by the user.
 * @returns Upload response with policy id and processing status.
 */
export async function uploadPolicy(file: File): Promise<PolicyUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/policies/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return parseJsonResponse(res, (data) => policyUploadResponseSchema.parse(data))
}

/**
 * Fetches rules with optional status and policy filters.
 * @param status Optional rule status filter.
 * @param policyId Optional policy id filter.
 * @returns Parsed list of rules.
 */
export async function getRules(status?: RuleStatus, policyId?: number): Promise<Rule[]> {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (policyId) params.set('policy_id', String(policyId))
  const query = params.toString()
  const res = await fetch(`${BASE}/rules${query ? `?${query}` : ''}`)
  if (!res.ok) throw new Error(`Failed to fetch rules: ${res.status}`)
  return parseJsonResponse(res, (data) => rulesSchema.parse(data))
}

/**
 * Approves a pending rule.
 * @param id Rule id.
 * @returns Parsed rule after approval.
 */
export async function approveRule(id: number): Promise<Rule> {
  const res = await fetch(`${BASE}/rules/${id}/approve`, { method: 'PATCH' })
  if (!res.ok) throw new Error(`Failed to approve rule: ${res.status}`)
  return parseJsonResponse(res, (data) => ruleSchema.parse(data))
}

/**
 * Rejects a pending rule.
 * @param id Rule id.
 * @returns Parsed rule after rejection.
 */
export async function rejectRule(id: number): Promise<Rule> {
  const res = await fetch(`${BASE}/rules/${id}/reject`, { method: 'PATCH' })
  if (!res.ok) throw new Error(`Failed to reject rule: ${res.status}`)
  return parseJsonResponse(res, (data) => ruleSchema.parse(data))
}

/**
 * Fetches violations with optional rule and status filters.
 * @param ruleId Optional rule id filter.
 * @param status Optional violation status filter.
 * @returns Parsed list of violations.
 */
export async function getViolations(ruleId?: number, status?: ViolationStatus): Promise<Violation[]> {
  const params = new URLSearchParams()
  if (ruleId !== undefined) params.set('v3_rule_id', String(ruleId))
  if (status) params.set('status', status)
  const query = params.toString()
  const res = await fetch(`${BASE}/violations${query ? `?${query}` : ''}`)
  if (!res.ok) throw new Error(`Failed to fetch violations: ${res.status}`)
  return parseJsonResponse(res, (data) => violationsSchema.parse(data))
}

/**
 * Triggers a V3 scan run.
 * @returns Parsed scan result split by deterministic vs semantic violations.
 */
export async function triggerScan(): Promise<ScanResult> {
  const res = await fetch(`${BASE}/scan`, { method: 'POST' })
  if (!res.ok) throw new Error(`Scan failed: ${res.status}`)
  return parseJsonResponse(res, (data) => scanResultSchema.parse(data))
}
