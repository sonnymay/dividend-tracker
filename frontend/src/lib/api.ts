const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type Holding = {
  id: number
  ticker: string
  shares: number
  price: number
  dividend_yield_percent: number
  annual_dividend_per_share: number
  annual_income: number
  monthly_income: number
  market_value: number
  created_at: string
}

export type Goal = {
  id: number | null
  monthly_target: number
  weekly_investment: number
}

export type Dashboard = {
  current_monthly_income: number
  monthly_target: number
  progress_percent: number
  projection: {
    remaining_monthly_income: number
    estimated_weeks_to_goal: number | null
    estimated_months_to_goal: number | null
    estimated_goal_date: string | null
  }
  recommendation: {
    ticker: string
    monthly_income_per_dollar: number
    annual_dividend_yield_percent: number
    share_price: number
  } | null
  holdings: Holding[]
}

export type ChartPoint = {
  month: string
  total_monthly_income: number
  created_at: string | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const fallback = 'Something went wrong.'
    const data = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(data?.detail ?? fallback)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const api = {
  getGoal: () => request<Goal>('/goal'),
  saveGoal: (payload: Pick<Goal, 'monthly_target' | 'weekly_investment'>) =>
    request<Goal>('/goal', { method: 'POST', body: JSON.stringify(payload) }),
  getHoldings: () => request<Holding[]>('/holdings'),
  addHolding: (payload: { ticker: string; shares: number }) =>
    request<Holding>('/holdings', { method: 'POST', body: JSON.stringify(payload) }),
  deleteHolding: (id: number) => request<void>(`/holdings/${id}`, { method: 'DELETE' }),
  getDashboard: () => request<Dashboard>('/dashboard'),
  getChart: () => request<ChartPoint[]>('/chart'),
}

