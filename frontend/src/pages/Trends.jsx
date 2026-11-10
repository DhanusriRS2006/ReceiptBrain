
import { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const COLORS = {
  Food: '#ffcf78',
  Travel: '#79bbff',
  Shopping: '#ff9ed3',
  Utilities: '#8cffab',
  Entertainment: '#c7a5ff',
  Subscriptions: '#7edce7',
  Healthcare: '#ff829e',
  Other: '#a3b5a8'
}

const money = value =>
  `₹${Number(value || 0).toLocaleString('en-IN', {
    maximumFractionDigits: 2
  })}`

export default function Trends() {
  const [monthly, setMonthly] = useState([])
  const [cats, setCats] = useState([])
  const [insight, setInsight] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const res = await axios.get(`${API}/expenses/by-month`)
        const categories = new Set()

        const rows = Object.entries(res.data.monthly_data || {})
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([month, categoryTotals]) => {
            const row = { month }

            Object.entries(categoryTotals || {}).forEach(([k, v]) => {
              row[k] = Number(v || 0)
              categories.add(k)
            })

            return row
          })

        if (!cancelled) {
          setMonthly(rows)
          setCats([...categories])
        }
      } catch (e) {
        if (!cancelled) {
          setLoadError(
            typeof e.response?.data?.detail === 'string'
              ? e.response.data.detail
              : 'Could not load spending trends'
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    const loadInsights = async () => {
      try {
        const res = await axios.get(`${API}/insights`)
        if (!cancelled) setInsight(res.data.insight || null)
      } catch (e) {
        console.error('Could not load saved insights:', e)
      }
    }

    load()
    loadInsights()

    return () => { cancelled = true }
  }, [])

  const generate = async () => {
    setBusy(true)
    setErr('')

    try {
      const res = await axios.get(`${API}/insights`, {
        params: { refresh: true }
      })
      setInsight(res.data.insight || null)
    } catch (e) {
      setErr(
        typeof e.response?.data?.detail === 'string'
          ? e.response.data.detail
          : 'Could not generate insights'
      )
    } finally {
      setBusy(false)
    }
  }

  const mom = (() => {
    if (monthly.length < 2) return []

    const last = monthly[monthly.length - 1]
    const prev = monthly[monthly.length - 2]

    return cats.map(category => {
      const current = Number(last[category] || 0)
      const previous = Number(prev[category] || 0)

      const change = previous > 0
        ? Math.round(((current - previous) / previous) * 100)
        : current > 0 ? null : 0

      return {
        category,
        current,
        previous,
        change
      }
    }).sort((a, b) =>
      Math.abs(b.change ?? 0) - Math.abs(a.change ?? 0)
    )
  })()

  const flags = insight?.inflation_flags || []
  const preds = insight?.predictions || {}

  if (loading) {
    return <div className="loading">Loading trends...</div>
  }

  return (
    <div>
      <div className="eyebrow">SPENDING ANALYTICS</div>
      <h1>Spending Trends</h1>

      <p className="page-subtitle" style={{
        marginBottom: '2rem'
      }}>
        Understand month-on-month spending and discover
        changes in your financial habits.
      </p>

      {loadError && (
        <div className="form-error">
          ❌ {loadError}
        </div>
      )}

      {flags.length > 0 && (
        <div style={{
          background: '#332a16',
          border: '1px solid #d6a34d',
          borderRadius: 10,
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem'
        }}>
          <strong style={{ color: '#ffdc93' }}>
            ⚠️ Lifestyle inflation detected
          </strong>

          {flags.map((f, i) => (
            <p key={i} style={{
              color: '#f4d9a3',
              fontSize: 14,
              marginTop: 6
            }}>
              {f.message ||
                `${f.category} spending is up ${f.increase_percent}% over the last 3 months.`}
            </p>
          ))}
        </div>
      )}

      <div className="card">
        <h2>Category Trends</h2>
        <p className="muted" style={{
          marginBottom: '1.25rem'
        }}>
          Spending across different months.
        </p>

        {monthly.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={monthly}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#294232"
              />

              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fill: '#94ae9c' }}
              />

              <YAxis
                tick={{ fontSize: 12, fill: '#94ae9c' }}
                tickFormatter={v => `₹${v}`}
              />

              <Tooltip
                contentStyle={{
                  background: '#13261a',
                  border: '1px solid #365542',
                  borderRadius: 10,
                  color: '#edfff2'
                }}
                labelStyle={{ color: '#edfff2' }}
                formatter={(v, n) => [money(v), n]}
              />

              <Legend />

              {cats.map(c => (
                <Line
                  key={c}
                  type="monotone"
                  dataKey={c}
                  stroke={COLORS[c] || '#a3b5a8'}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state">
            <p>No monthly expense data available yet.</p>
          </div>
        )}
      </div>

      {mom.length > 0 && (
        <div className="card">
          <h2>Month-on-Month Change</h2>

          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th style={{ textAlign: 'right' }}>Previous</th>
                  <th style={{ textAlign: 'right' }}>Latest</th>
                  <th style={{ textAlign: 'right' }}>Change</th>
                </tr>
              </thead>

              <tbody>
                {mom.map(r => (
                  <tr key={r.category}>
                    <td>
                      <strong>{r.category}</strong>
                    </td>

                    <td style={{
                      textAlign: 'right',
                      color: '#94ae9c'
                    }}>
                      {money(r.previous)}
                    </td>

                    <td style={{
                      textAlign: 'right',
                      color: '#edfff2'
                    }}>
                      {money(r.current)}
                    </td>

                    <td style={{
                      textAlign: 'right',
                      fontWeight: 600,
                      color:
                        r.change === null ? '#8cffab' :
                        r.change > 15 ? '#ff829e' :
                        r.change < 0 ? '#8cffab' :
                        '#ffcf78'
                    }}>
                      {r.change === null
                        ? 'New'
                        : `${r.change > 0 ? '+' : ''}${r.change}%`}
                      {r.change !== null && r.change > 15 && ' ⚠️'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="card">
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '16px',
          flexWrap: 'wrap'
        }}>
          <div>
            <h2>AI Insights</h2>
            <p className="muted">
              Next-month forecast and savings tips from
              the Insight agent.
            </p>
          </div>

          <button
            className="btn-primary"
            onClick={generate}
            disabled={busy}
          >
            {busy ? '⏳ Analysing...' : '🤖 Generate Insights'}
          </button>
        </div>

        {err && (
          <div className="form-error" style={{
            marginTop: '1rem'
          }}>
            ❌ {err}
          </div>
        )}

        {insight && (
          <div style={{ marginTop: '1.25rem' }}>
            <div style={{
              background: '#183825',
              borderLeft: '4px solid #8cffab',
              borderRadius: 10,
              padding: '1rem'
            }}>
              <p style={{
                color: '#c8f9d5',
                fontSize: 14,
                lineHeight: 1.6
              }}>
                {insight.summary || insight.summary_text}
              </p>

              {insight.savings_tip && (
                <p style={{
                  color: '#8cffab',
                  fontSize: 14,
                  marginTop: 8
                }}>
                  💡 {insight.savings_tip}
                </p>
              )}
            </div>

            {Object.keys(preds).length > 0 && (
              <>
                <h2 style={{
                  marginTop: '1.5rem'
                }}>
                  Predicted Next Month
                </h2>

                <div className="stat-grid">
                  {Object.entries(preds)
                    .filter(([, v]) => Number(v) > 0)
                    .map(([k, v]) => (
                      <div className="stat-card" key={k}>
                        <div className="label">
                          {k === 'total' ? 'Total' : k}
                        </div>

                        <div className="value" style={{
                          fontSize: '1.3rem'
                        }}>
                          {money(v)}
                        </div>
                      </div>
                    ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
