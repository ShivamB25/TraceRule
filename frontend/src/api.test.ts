import { describe, it, expect, vi, afterEach } from 'vitest'
import { getRules } from './api'
import { RULE_STATUS } from './types'

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
})
