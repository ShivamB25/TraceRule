import { describe, it, expect, vi, afterEach } from 'vitest'
import { getRules, getViolations } from './api'
import { RULE_STATUS, VIOLATION_STATUS } from './types'

describe('API tests', () => {
  afterEach(() => vi.restoreAllMocks())

  it('getRules construct query string properly', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    } as unknown as Response)

    await getRules(RULE_STATUS.PENDING_REVIEW, 123)

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]
    const url = new URL(calledUrl, 'http://localhost')
    expect(url.searchParams.get('status')).toBe(RULE_STATUS.PENDING_REVIEW)
    expect(url.searchParams.get('policy_id')).toBe('123')
  })

  it('getViolations accepts legacy array response shape', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: 1,
          v3_rule_id: 2,
          record_id: 10,
          violation_data: { amount_paid: 15000 },
          verdict_reasoning: null,
          confidence_score: 1,
          status: VIOLATION_STATUS.OPEN,
        },
      ],
    } as unknown as Response)

    const result = await getViolations(undefined, VIOLATION_STATUS.OPEN, 25, 0)

    expect(result.items).toHaveLength(1)
    expect(result.total_count).toBe(1)
    expect(result.limit).toBe(25)
    expect(result.offset).toBe(0)
  })
})
