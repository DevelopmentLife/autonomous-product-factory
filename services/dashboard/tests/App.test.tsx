import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StatusBadge } from '../src/components/StatusBadge'
import { StageTimeline } from '../src/components/StageTimeline'

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={qc}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
)

describe('StatusBadge', () => {
  it('renders completed badge', () => {
    render(<StatusBadge status="completed" />, { wrapper: Wrapper })
    expect(screen.getByText('completed')).toBeInTheDocument()
  })

  it('renders running badge with animate-pulse class', () => {
    const { container } = render(<StatusBadge status="running" />, { wrapper: Wrapper })
    expect(container.firstChild).toHaveClass('animate-pulse')
  })
})

describe('StageTimeline', () => {
  const stages = [
    { id: '1', pipeline_id: 'p1', name: 'prd', status: 'completed' as const, started_at: new Date().toISOString(), completed_at: null, error_message: null },
    { id: '2', pipeline_id: 'p1', name: 'architect', status: 'running' as const, started_at: new Date().toISOString(), completed_at: null, error_message: null },
  ]

  it('renders all stages in order', () => {
    render(<StageTimeline stages={stages} />, { wrapper: Wrapper })
    expect(screen.getByText('prd')).toBeInTheDocument()
    expect(screen.getByText('architect')).toBeInTheDocument()
  })
})
