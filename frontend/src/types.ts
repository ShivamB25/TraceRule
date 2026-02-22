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
  rule_id: string
  title: string
  source_quote: string
  severity: RuleSeverity
  target_table: string
  logic_tree_json: Record<string, unknown> | null
  requires_semantic_scan: boolean
  compiled_sql: string | null
  status: RuleStatus
}

export interface Violation {
  id: number
  v3_rule_id: number
  record_id: number
  violation_data: Record<string, unknown>
  verdict_reasoning: string | null
  confidence_score: number | null
  status: ViolationStatus
}

export interface PaginatedViolations {
  items: Violation[]
  total_count: number
  limit: number
  offset: number
}

export interface ScanResult {
  deterministic_violations: number
  semantic_violations: number
  total: number
}

export const policyUploadResponseSchema = z.object({
  id: z.number(),
  filename: z.string().min(1),
  status: z.enum([POLICY_UPLOAD_STATUS.PROCESSING, POLICY_UPLOAD_STATUS.COMPLETED]),
})

export const ruleSchema = z.object({
  id: z.number(),
  policy_id: z.number(),
  rule_id: z.string().min(1),
  title: z.string().min(1),
  source_quote: z.string(),
  severity: z.enum([
    RULE_SEVERITY.CRITICAL,
    RULE_SEVERITY.HIGH,
    RULE_SEVERITY.MEDIUM,
    RULE_SEVERITY.LOW,
  ]),
  target_table: z.string().min(1),
  logic_tree_json: z.record(z.string(), z.unknown()).nullable(),
  requires_semantic_scan: z.boolean(),
  compiled_sql: z.string().nullable(),
  status: z.enum([RULE_STATUS.PENDING_REVIEW, RULE_STATUS.APPROVED, RULE_STATUS.REJECTED]),
})

export const violationSchema = z.object({
  id: z.number(),
  v3_rule_id: z.number(),
  record_id: z.number(),
  violation_data: z.record(z.string(), z.unknown()),
  verdict_reasoning: z.string().nullable(),
  confidence_score: z.number().nullable(),
  status: z.enum([VIOLATION_STATUS.OPEN, VIOLATION_STATUS.RESOLVED]),
})

export const scanResultSchema = z.object({
  deterministic_violations: z.number(),
  semantic_violations: z.number(),
  total: z.number(),
})

export const rulesSchema = z.array(ruleSchema)
export const violationsSchema = z.array(violationSchema)

export const paginatedViolationsSchema = z.object({
  items: violationsSchema,
  total_count: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
})
