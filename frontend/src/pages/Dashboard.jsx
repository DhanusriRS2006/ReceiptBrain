
import { useEffect, useMemo, useState } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const COLORS = [
  '#8cffab', '#37c98b', '#c5ff73', '#58a6ff',
  '#ffbe65', '#d5a2ff', '#ff829e', '#82d7ce'
]

const money = value =>
  `₹${Number(value || 0).toLocaleString('en-IN', {
    maximumFractionDigits: 2
  })}`

const currentMonth = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

const shiftMonth = (month, offset) => {
  const [year, m] = month.split('-').map(Number)
  const date = new Date(year, m - 1 + offset, 1)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

const monthLabel = month => {
  if (month === 'all') return 'All Time'
  const [year, m] = month.split('-').map(Number)
  return new Date(year, m - 1, 1).toLocaleDateString('en-IN', {
    month: 'long', year: 'numeric'
  })
}

const badgeClass = category => {
  const classes = {
    Food: 'badge-food',
    Travel: 'badge-travel',
    Shopping: 'badge-shopping',
    Utilities: 'badge-utilities',
    Entertainment: 'badge-entertainment',
    Subscriptions: 'badge-subscriptions',
    Healthcare: 'badge-healthcare'
  }
  return classes[category] || 'badge-other'
}

export default function Dashboard() {
  const [month, setMonth] = useState(currentMonth)
  const [expenses, setExpenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError('')

      try {
        const response = await axios.get(`${API}/expenses`, {
          params: {
            month: month === 'all' ? 'all' : month,
            limit: 1000
          }
        })

        if (!cancelled) {
          setExpenses(response.data.expenses || [])
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message)
          setExpenses([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [month])

  const summary = useMemo(() => {
    const byCategory = {}
    let total = 0

    expenses.forEach(exp => {
      const amount = Number(exp.total || 0)
      const category = exp.category || 'Other'
      total += amount
      byCategory[category] = (byCategory[category] || 0) + amount
    })

    const chartData = Object.entries(byCategory)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)

    return {
      total,
      count: expenses.length,
      average: expenses.length ? total / expenses.length : 0,
      topCategory: chartData[0]?.name || '—',
      chartData
    }
  }, [expenses])

  const chartData = summary.chartData

  return (
    <div>
      <div className="dashboard-header">
        <div>
          <div className="eyebrow">YOUR FINANCIAL OVERVIEW</div>
          <h1>Dashboard</h1>
          <p className="page-subtitle">
            Track your spending and understand where your money goes.
          </p>
        </div>

        <div className="month-controls">
          <button
            className="month-arrow"
            disabled={month === 'all'}
            onClick={() => setMonth(m => shiftMonth(m, -1))}
            aria-label="Previous month"
          >
            ‹
          </button>

          <input
            type="month"
            value={month === 'all' ? currentMonth() : month}
            onChange={e => {
              if (e.target.value) setMonth(e.target.value)
            }}
            aria-label="Choose month"
          />

          <button
            className="month-arrow"
            disabled={month === 'all' || month >= currentMonth()}
            onClick={() => setMonth(m => shiftMonth(m, 1))}
            aria-label="Next month"
          >
            ›
          </button>

          <button
            className={month === 'all' ? 'period-active' : 'btn-secondary'}
            onClick={() => setMonth(m => m === 'all' ? currentMonth() : 'all')}
          >
            {month === 'all' ? 'This Month' : 'All Time'}
          </button>
        </div>
      </div>

      <div className="period-caption">
        Showing {monthLabel(month)}
      </div>

      {error && <div className="form-error">{error}</div>}
      {loading && <div className="loading">Loading expenses...</div>}

      {!loading && !error && (
        <>
          <div className="stat-grid">
            <div className="stat-card stat-primary">
              <div className="label">Total Spent</div>
              <div className="value">{money(summary.total)}</div>
              <div className="stat-footnote">{monthLabel(month)}</div>
            </div>

            <div className="stat-card">
              <div className="label">Transactions</div>
              <div className="value">{summary.count}</div>
              <div className="stat-footnote">Recorded expenses</div>
            </div>

            <div className="stat-card">
              <div className="label">Top Category</div>
              <div className="value category-value">
                {summary.topCategory}
              </div>
              <div className="stat-footnote">Highest spending</div>
            </div>

            <div className="stat-card">
              <div className="label">Average Transaction</div>
              <div className="value">{money(summary.average)}</div>
              <div className="stat-footnote">Per expense</div>
            </div>
          </div>

          <div className="dashboard-charts">
            <div className="card">
              <h2>Spending by Category</h2>
              <p className="muted">Distribution of your expenses</p>

              {chartData.length ? (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={chartData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={68}
                      outerRadius={103}
                      paddingAngle={3}
                    >
                      {chartData.map((item, i) => (
                        <Cell
                          key={item.name}
                          fill={COLORS[i % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip formatter={value => money(value)} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-state">
                  <div className="empty-icon">◉</div>
                  <p>No expenses for this period.</p>
                </div>
              )}
            </div>

            <div className="card">
              <h2>Category Breakdown</h2>
              <p className="muted">Your spending, ranked</p>

              {chartData.length ? chartData.map((item, i) => {
                const percent = summary.total > 0
                  ? (item.value / summary.total) * 100
                  : 0

                return (
                  <div className="category-row" key={item.name}>
                    <div className="category-row-top">
                      <span className={`badge ${badgeClass(item.name)}`}>
                        {item.name}
                      </span>
                      <span>{money(item.value)}</span>
                    </div>
                    <div className="progress-track">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${percent}%`,
                          background: COLORS[i % COLORS.length]
                        }}
                      />
                    </div>
                    <div className="category-percent">
                      {percent.toFixed(1)}%
                    </div>
                  </div>
                )
              }) : (
                <div className="empty-state">
                  <p>No category data for this period.</p>
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="section-heading">
              <div>
                <h2>Transactions</h2>
                <p className="muted">{monthLabel(month)} expenses</p>
              </div>
              <span className="count-pill">{expenses.length} records</span>
            </div>

            {expenses.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Merchant</th>
                      <th>Category</th>
                      <th>Date</th>
                      <th>Payment</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expenses.map(exp => (
                      <tr key={exp.id}>
                        <td><strong>{exp.merchant}</strong></td>
                        <td>
                          <span className={`badge ${badgeClass(exp.category)}`}>
                            {exp.category || 'Other'}
                          </span>
                        </td>
                        <td className="muted">{exp.date}</td>
                        <td className="muted">{exp.payment_method || '—'}</td>
                        <td className="amount-cell">{money(exp.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">▤</div>
                <p>No transactions found for {monthLabel(month)}.</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
