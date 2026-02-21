import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import SeverityBadge from './SeverityBadge'
import { RULE_SEVERITY } from '../types'

describe('SeverityBadge', () => {
  it('renders critical severity with correct text', () => {
    render(<SeverityBadge severity={RULE_SEVERITY.CRITICAL} />)
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
  })
})
