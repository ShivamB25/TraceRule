export interface PolicyUploadResponse {
  id: number
  filename: string
  status: string
}

export interface Rule {
  id: number
  policy_id: number
  title: string
  source_quote: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  compiled_sql: string | null
  is_deterministic: boolean
  status: 'pending_review' | 'approved' | 'rejected'
}

export interface Violation {
  id: number
  rule_id: number
  record_pk: string
  violating_data: Record<string, unknown>
  ai_explanation: string | null
  status: string
}

export interface ScanResult {
  violations_found: number
}
