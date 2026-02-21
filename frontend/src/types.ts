import { z } from 'zod'

export const POLICY_UPLOAD_STATUS = {
  PROCESSING: 'processing',
  COMPLETED: 'completed',
} as const

export type PolicyUploadStatus = (typeof POLICY_UPLOAD_STATUS)[keyof typeof POLICY_UPLOAD_STATUS]

export const RULE_SEVERITY = {
  CRITICAL: 'CRITICAL',
  HIGH: 'HIGH',
  MEDIUM: 'MEDIUM',
  LOW: 'LOW',
} as const

export type RuleSeverity = (typeof RULE_SEVERITY)[keyof typeof RULE_SEVERITY]

export const RULE_STATUS = {
  PENDING_REVIEW: 'pending_review',
  APPROVED: 'approved',
  REJECTED: 'rejected',
} as const

export type RuleStatus = (typeof RULE_STATUS)[keyof typeof RULE_STATUS]

export const VIOLATION_STATUS = {
  OPEN: 'open',
  RESOLVED: 'resolved',
} as const

export type ViolationStatus = (typeof VIOLATION_STATUS)[keyof typeof VIOLATION_STATUS]
export type ViolationStatusFilter = ViolationStatus | 'all'

export interface PolicyUploadResponse {
  id: number
  filename: string
  status: PolicyUploadStatus
}

export interface Rule {
  id: number
  policy_id: number
  title: string
  source_quote: string
  severity: RuleSeverity
  compiled_sql: string | null
  is_deterministic: boolean
  status: RuleStatus
}

export interface Violation {
  id: number
  rule_id: number
  record_pk: string
  violating_data: Record<string, unknown>
  ai_explanation: string | null
  status: ViolationStatus
}

export interface ScanResult {
  violations_found: number
}

export const policyUploadResponseSchema = z.object({
  id: z.number(),
  filename: z.string().min(1),
  status: z.enum([POLICY_UPLOAD_STATUS.PROCESSING, POLICY_UPLOAD_STATUS.COMPLETED]),
})

export const ruleSchema = z.object({
  id: z.number(),
  policy_id: z.number(),
  title: z.string().min(1),
  source_quote: z.string(),
  severity: z.enum([
    RULE_SEVERITY.CRITICAL,
    RULE_SEVERITY.HIGH,
    RULE_SEVERITY.MEDIUM,
    RULE_SEVERITY.LOW,
  ]),
  compiled_sql: z.string().nullable(),
  is_deterministic: z.boolean(),
  status: z.enum([RULE_STATUS.PENDING_REVIEW, RULE_STATUS.APPROVED, RULE_STATUS.REJECTED]),
})

export const violationSchema = z.object({
  id: z.number(),
  rule_id: z.number(),
  record_pk: z.string(),
  violating_data: z.record(z.string(), z.unknown()),
  ai_explanation: z.string().nullable(),
  status: z.enum([VIOLATION_STATUS.OPEN, VIOLATION_STATUS.RESOLVED]),
})

export const scanResultSchema = z.object({
  violations_found: z.number(),
})

export const rulesSchema = z.array(ruleSchema)
export const violationsSchema = z.array(violationSchema)
