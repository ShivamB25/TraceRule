import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect } from 'vitest'
import RuleCard from './RuleCard'

describe('RuleCard', () => {
  const baseRule = {
    id: 1, title: 'No NULLs in user_id', severity: 'HIGH' as const,
    status: 'pending_review' as const, compiled_sql: 'SELECT id FROM users WHERE user_id IS NULL',
    is_deterministic: true, policy_id: 2, source_quote: 'Quote', ai_explanation: null,
  }

  it('calls onApprove with rule id when Approve is clicked', async () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    const user = userEvent.setup()

    render(<RuleCard rule={baseRule} onApprove={onApprove} onReject={onReject} />)

    await user.click(screen.getByRole('button', { name: /approve/i }))

    expect(onApprove).toHaveBeenCalledOnce()
    expect(onApprove).toHaveBeenCalledWith(1)
    expect(onReject).not.toHaveBeenCalled()
  })
})
