import { startTransition, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api, type ChartPoint, type Dashboard, type Holding } from './lib/api'

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
})

const percent = new Intl.NumberFormat('en-US', {
  style: 'percent',
  maximumFractionDigits: 1,
})

function formatCurrency(value: number): string {
  return currency.format(value ?? 0)
}

function formatPercent(value: number): string {
  return percent.format(value / 100)
}

function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [chartPoints, setChartPoints] = useState<ChartPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [savingGoal, setSavingGoal] = useState(false)
  const [savingHolding, setSavingHolding] = useState(false)
  const [savingHoldingId, setSavingHoldingId] = useState<number | null>(null)
  const [removingHoldingId, setRemovingHoldingId] = useState<number | null>(null)
  const [editingHoldingId, setEditingHoldingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [goalForm, setGoalForm] = useState({ monthly_target: '5000' })
  const [holdingForm, setHoldingForm] = useState({ ticker: '', shares: '' })
  const [editingHoldingForm, setEditingHoldingForm] = useState({ ticker: '', shares: '' })

  async function refresh(options?: { preserveError?: boolean; background?: boolean }) {
    if (!options?.preserveError) {
      setError(null)
    }
    if (options?.background) {
      setRefreshing(true)
    }
    try {
      const [goalResponse, dashboardResponse, chartResponse] = await Promise.all([
        api.getGoal(),
        api.getDashboard(),
        api.getChart(),
      ])

      startTransition(() => {
        setGoalForm({
          monthly_target: goalResponse.monthly_target ? String(goalResponse.monthly_target) : '5000',
        })
      setHoldings(dashboardResponse.holdings)
      setDashboard(dashboardResponse)
      setChartPoints(chartResponse)
      })
    } finally {
      if (options?.background) {
        setRefreshing(false)
      }
    }
  }

  useEffect(() => {
    refresh()
      .catch((refreshError: unknown) => {
        setError(refreshError instanceof Error ? refreshError.message : 'Unable to load dashboard.')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  const topHoldings = [...holdings].sort((left, right) => right.monthly_income - left.monthly_income)

  async function handleGoalSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSavingGoal(true)
    setError(null)
    setNotice(null)

    try {
      await api.saveGoal({
        monthly_target: Number(goalForm.monthly_target),
        weekly_investment: 0,
      })
      setNotice('Goal updated.')
      await refresh({ background: true })
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to save goal.')
    } finally {
      setSavingGoal(false)
    }
  }

  async function handleHoldingSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSavingHolding(true)
    setError(null)
    setNotice(null)

    try {
      await api.addHolding({
        ticker: holdingForm.ticker.trim().toUpperCase(),
        shares: Number(holdingForm.shares),
      })
      setHoldingForm({ ticker: '', shares: '' })
      setNotice('Holding added.')
      await refresh({ background: true })
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to add holding.')
    } finally {
      setSavingHolding(false)
    }
  }

  function startEditingHolding(holding: Holding) {
    setEditingHoldingId(holding.id)
    setEditingHoldingForm({
      ticker: holding.ticker,
      shares: String(holding.shares),
    })
    setError(null)
    setNotice(null)
  }

  function cancelEditingHolding() {
    setEditingHoldingId(null)
    setEditingHoldingForm({ ticker: '', shares: '' })
  }

  async function handleEditHoldingSubmit(id: number) {
    setSavingHoldingId(id)
    setError(null)
    setNotice(null)

    try {
      await api.updateHolding(id, {
        ticker: editingHoldingForm.ticker.trim().toUpperCase(),
        shares: Number(editingHoldingForm.shares),
      })
      cancelEditingHolding()
      setNotice('Holding updated.')
      await refresh({ background: true })
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to update holding.')
    } finally {
      setSavingHoldingId(null)
    }
  }

  async function handleDeleteHolding(id: number) {
    setError(null)
    setNotice(null)
    setRemovingHoldingId(id)

    try {
      await api.deleteHolding(id)
      if (editingHoldingId === id) {
        cancelEditingHolding()
      }
      setNotice('Holding removed.')
      await refresh({ background: true })
    } catch (deleteError: unknown) {
      setError(deleteError instanceof Error ? deleteError.message : 'Unable to remove holding.')
    } finally {
      setRemovingHoldingId(null)
    }
  }

  const recommendation = dashboard?.recommendation
  const projection = dashboard?.projection
  const progressPercent = dashboard?.progress_percent ?? 0
  const currentIncome = dashboard?.current_monthly_income ?? 0
  const monthlyTarget = dashboard?.monthly_target ?? 0

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(39,96,75,0.18),_transparent_30%),linear-gradient(180deg,_#f8f5ef_0%,_#f3efe6_55%,_#efe8dc_100%)] text-stone-900">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-8 px-4 py-6 sm:px-6 lg:px-8">
        <header className="overflow-hidden rounded-[2rem] border border-white/70 bg-white/75 p-6 shadow-[0_24px_80px_rgba(51,41,24,0.10)] backdrop-blur motion-safe:animate-[rise_0.6s_ease-out] sm:p-8">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-stone-500">
                Dividend tracker
              </p>
              <h1 className="mt-4 max-w-xl font-heading text-4xl tracking-[-0.04em] text-stone-950 sm:text-5xl">
                Track your stocks and dividend income.
              </h1>
            </div>

            <div className="grid min-w-full gap-3 sm:grid-cols-3 lg:min-w-[28rem]">
              <StatCard label="Monthly income" value={formatCurrency(currentIncome)} />
              <StatCard
                label="Goal progress"
                value={monthlyTarget ? formatPercent(progressPercent) : 'Set a goal'}
              />
              <StatCard label="Stocks" value={String(holdings.length)} />
            </div>
          </div>

          <div className="mt-8">
            <div className="flex items-center justify-between text-sm text-stone-600">
              <span>{formatCurrency(currentIncome)} per month</span>
              <span>{formatCurrency(monthlyTarget)} target</span>
            </div>
            <div className="mt-3 h-4 overflow-hidden rounded-full bg-stone-200">
              <div
                className="h-full rounded-full bg-[linear-gradient(90deg,_#18493b_0%,_#2d7d62_55%,_#9fd6bd_100%)] transition-all duration-500"
                style={{ width: `${Math.min(progressPercent, 100)}%` }}
              />
            </div>
          </div>
        </header>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span>{error}</span>
              <button
                className="rounded-full border border-rose-300 px-3 py-1 text-xs font-medium text-rose-700 transition hover:bg-rose-100"
                onClick={() => {
                  setNotice(null)
                  refresh({ preserveError: true, background: true }).catch((refreshError: unknown) => {
                    setError(
                      refreshError instanceof Error ? refreshError.message : 'Unable to refresh dashboard.',
                    )
                  })
                }}
                type="button"
              >
                Retry
              </button>
            </div>
          </div>
        ) : null}

        {notice ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            {notice}
          </div>
        ) : null}

        <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <Panel title="Goal settings">
            <form className="grid gap-4" onSubmit={handleGoalSubmit}>
              <label className="grid gap-2 text-sm text-stone-700">
                Monthly dividend target
                <input
                  className="h-12 rounded-2xl border border-stone-200 bg-stone-50 px-4 text-base outline-none transition focus:border-emerald-700 focus:bg-white"
                  inputMode="decimal"
                  value={goalForm.monthly_target}
                  onChange={(event) =>
                    setGoalForm((current) => ({ ...current, monthly_target: event.target.value }))
                  }
                />
              </label>
              <button
                className="col-span-full inline-flex h-12 items-center justify-center rounded-2xl bg-stone-950 px-5 font-medium text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:bg-stone-400"
                disabled={savingGoal || refreshing}
                type="submit"
              >
                {savingGoal ? 'Saving goal...' : 'Save goal'}
              </button>
            </form>
          </Panel>

          <Panel title="What to buy next">
            {recommendation ? (
              <div className="grid gap-5">
                <div className="flex items-end justify-between">
                  <div>
                    <p className="font-mono text-xs uppercase tracking-[0.28em] text-stone-500">
                      Best stock
                    </p>
                    <h2 className="mt-2 font-heading text-4xl tracking-[-0.05em] text-stone-950">
                      {recommendation.ticker}
                    </h2>
                  </div>
                  <p className="rounded-full bg-emerald-100 px-3 py-1 text-sm text-emerald-900">
                    {recommendation.annual_dividend_yield_percent.toFixed(2)}% yield
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <MetricRow
                    label="Monthly income per $1"
                    value={formatCurrency(recommendation.monthly_income_per_dollar)}
                  />
                  <MetricRow label="Share price" value={formatCurrency(recommendation.share_price)} />
                </div>
              </div>
            ) : (
              <EmptyState message="Add at least one stock to see a suggestion." />
            )}
          </Panel>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Panel title="Income chart">
            <div className="h-[320px] w-full">
              {chartPoints.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={chartPoints.map((point) => ({
                      ...point,
                      label: new Date(point.month).toLocaleDateString('en-US', {
                        month: 'short',
                        year: 'numeric',
                      }),
                    }))}
                  >
                    <defs>
                      <linearGradient id="incomeFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#266f58" stopOpacity={0.42} />
                        <stop offset="100%" stopColor="#266f58" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#d7d1c7" vertical={false} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={10} />
                    <YAxis
                      tickFormatter={(value: number) => `$${value}`}
                      tickLine={false}
                      axisLine={false}
                      width={64}
                    />
                    <Tooltip
                      formatter={(value) => formatCurrency(Number(value ?? 0))}
                      contentStyle={{
                        borderRadius: '16px',
                        borderColor: '#d6d0c4',
                        background: '#fffdfa',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="total_monthly_income"
                      stroke="#18493b"
                      strokeWidth={3}
                      fill="url(#incomeFill)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Your chart will appear after your first saved update." />
              )}
            </div>
          </Panel>

          <Panel title="Projection">
            {projection ? (
              <div className="grid gap-3">
                <MetricRow
                  label="Remaining monthly income"
                  value={formatCurrency(projection.remaining_monthly_income)}
                />
                <MetricRow
                  label="Estimated weeks"
                  value={
                    projection.estimated_weeks_to_goal !== null
                      ? String(projection.estimated_weeks_to_goal)
                      : 'Not available'
                  }
                />
                <MetricRow
                  label="Estimated months"
                  value={
                    projection.estimated_months_to_goal !== null
                      ? String(projection.estimated_months_to_goal)
                      : 'Not available'
                  }
                />
                <MetricRow
                  label="Estimated goal date"
                  value={
                    projection.estimated_goal_date
                      ? new Date(projection.estimated_goal_date).toLocaleDateString('en-US', {
                          month: 'long',
                          day: 'numeric',
                          year: 'numeric',
                        })
                      : 'Not enough data yet'
                  }
                />
              </div>
            ) : (
              <EmptyState message="Projection details will show here." />
            )}
          </Panel>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel title="Add stock">
            <form className="grid gap-4 sm:grid-cols-[0.9fr_1.1fr]" onSubmit={handleHoldingSubmit}>
              <label className="grid gap-2 text-sm text-stone-700">
                Ticker
                <input
                  className="h-12 rounded-2xl border border-stone-200 bg-stone-50 px-4 text-base uppercase outline-none transition focus:border-emerald-700 focus:bg-white"
                  placeholder="AAPL"
                  value={holdingForm.ticker}
                  onChange={(event) =>
                    setHoldingForm((current) => ({ ...current, ticker: event.target.value }))
                  }
                />
              </label>
              <label className="grid gap-2 text-sm text-stone-700">
                Shares
                <input
                  className="h-12 rounded-2xl border border-stone-200 bg-stone-50 px-4 text-base outline-none transition focus:border-emerald-700 focus:bg-white"
                  inputMode="decimal"
                  placeholder="42"
                  value={holdingForm.shares}
                  onChange={(event) =>
                    setHoldingForm((current) => ({ ...current, shares: event.target.value }))
                  }
                />
              </label>
              <button
                className="col-span-full inline-flex h-12 items-center justify-center rounded-2xl bg-emerald-800 px-5 font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-400"
                disabled={savingHolding || refreshing}
                type="submit"
              >
                {savingHolding ? 'Adding stock...' : 'Add stock'}
              </button>
            </form>
          </Panel>

          <Panel title="Your stocks">
            {topHoldings.length > 0 ? (
              <div className="overflow-hidden rounded-[1.5rem] border border-stone-200">
                <div className="grid grid-cols-[1.05fr_0.75fr_0.85fr_0.85fr_auto] gap-3 bg-stone-100 px-4 py-3 text-xs font-medium uppercase tracking-[0.22em] text-stone-500">
                  <span>Ticker</span>
                  <span>Shares</span>
                  <span>Price</span>
                  <span>Monthly</span>
                  <span />
                </div>
                <div className="divide-y divide-stone-200">
                  {topHoldings.map((holding) => {
                    const isEditing = editingHoldingId === holding.id
                    const isSavingEdit = savingHoldingId === holding.id
                    const isRemoving = removingHoldingId === holding.id

                    return (
                      <div
                        key={holding.id}
                        className="grid grid-cols-[1.05fr_0.75fr_0.85fr_0.85fr_auto] items-center gap-3 px-4 py-3 text-sm text-stone-700"
                      >
                        <div>
                          {isEditing ? (
                            <input
                              className="h-10 w-full rounded-xl border border-stone-200 bg-white px-3 text-sm uppercase outline-none transition focus:border-emerald-700"
                              value={editingHoldingForm.ticker}
                              onChange={(event) =>
                                setEditingHoldingForm((current) => ({
                                  ...current,
                                  ticker: event.target.value,
                                }))
                              }
                            />
                          ) : (
                            <p className="font-heading text-lg text-stone-950">{holding.ticker}</p>
                          )}
                          <p className="text-xs text-stone-500">
                            {holding.dividend_yield_percent.toFixed(2)}% yield
                          </p>
                        </div>
                        {isEditing ? (
                          <input
                            className="h-10 w-full rounded-xl border border-stone-200 bg-white px-3 text-sm outline-none transition focus:border-emerald-700"
                            inputMode="decimal"
                            value={editingHoldingForm.shares}
                            onChange={(event) =>
                              setEditingHoldingForm((current) => ({
                                ...current,
                                shares: event.target.value,
                              }))
                            }
                          />
                        ) : (
                          <span>{holding.shares}</span>
                        )}
                        <span>{formatCurrency(holding.price)}</span>
                        <span className="font-medium text-emerald-900">
                          {formatCurrency(holding.monthly_income)}
                        </span>
                        <div className="flex flex-wrap justify-end gap-2">
                          {isEditing ? (
                            <>
                              <button
                                className="rounded-full border border-emerald-300 px-3 py-1 text-xs text-emerald-800 transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                                disabled={isSavingEdit || refreshing}
                                onClick={() => handleEditHoldingSubmit(holding.id)}
                                type="button"
                              >
                                {isSavingEdit ? 'Saving...' : 'Save'}
                              </button>
                              <button
                                className="rounded-full border border-stone-300 px-3 py-1 text-xs text-stone-600 transition hover:border-stone-400 hover:bg-stone-50"
                                disabled={isSavingEdit}
                                onClick={cancelEditingHolding}
                                type="button"
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <button
                              className="rounded-full border border-stone-300 px-3 py-1 text-xs text-stone-600 transition hover:border-emerald-400 hover:text-emerald-700"
                              disabled={refreshing || removingHoldingId !== null || savingHolding}
                              onClick={() => startEditingHolding(holding)}
                              type="button"
                            >
                              Edit
                            </button>
                          )}
                          <button
                            className="rounded-full border border-stone-300 px-3 py-1 text-xs text-stone-600 transition hover:border-rose-400 hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
                            disabled={isSavingEdit || isRemoving || refreshing}
                            onClick={() => handleDeleteHolding(holding.id)}
                            type="button"
                          >
                            {isRemoving ? 'Removing...' : 'Remove'}
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : (
                <EmptyState message="No stocks yet. Add your first one to get started." />
              )}
          </Panel>
        </section>

        <footer className="pb-4 text-center text-xs uppercase tracking-[0.24em] text-stone-500">
          {loading
            ? 'Loading dividend dashboard...'
            : refreshing
              ? 'Syncing live dividend data...'
              : 'Dividend Tracker ready'}
        </footer>
      </div>
    </main>
  )
}

function Panel(props: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="rounded-[2rem] border border-white/70 bg-white/75 p-6 shadow-[0_24px_70px_rgba(51,41,24,0.08)] backdrop-blur motion-safe:animate-[rise_0.8s_ease-out] sm:p-7">
      <div className="mb-5">
        <h2 className="font-heading text-2xl tracking-[-0.04em] text-stone-950">{props.title}</h2>
        {props.subtitle ? (
          <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">{props.subtitle}</p>
        ) : null}
      </div>
      {props.children}
    </section>
  )
}

function StatCard(props: { label: string; value: string }) {
  return (
    <div className="rounded-[1.5rem] border border-stone-200 bg-stone-50 px-4 py-4">
      <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{props.label}</p>
      <p className="mt-3 font-heading text-2xl tracking-[-0.04em] text-stone-950">{props.value}</p>
    </div>
  )
}

function MetricRow(props: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-[1.4rem] border border-stone-200 bg-stone-50 px-4 py-4">
      <span className="text-sm text-stone-600">{props.label}</span>
      <span className="font-medium text-stone-950">{props.value}</span>
    </div>
  )
}

function EmptyState(props: { message: string }) {
  return (
    <div className="rounded-[1.5rem] border border-dashed border-stone-300 bg-stone-50 px-4 py-8 text-center text-sm text-stone-500">
      {props.message}
    </div>
  )
}

export default App
