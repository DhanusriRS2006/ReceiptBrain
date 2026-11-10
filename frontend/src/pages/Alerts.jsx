
import { useEffect, useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const ANOMALY_CONFIG = {
  spike: {
    icon: '📈',
    label: 'Spending Spike',
    bg: '#332a16',
    border: '#d6a34d',
    color: '#ffdc93'
  },
  duplicate: {
    icon: '🔁',
    label: 'Possible Duplicate',
    bg: '#3c2028',
    border: '#db697e',
    color: '#ffadbc'
  },
  unusual_merchant: {
    icon: '⚠️',
    label: 'Unusual Merchant',
    bg: '#30253f',
    border: '#a17ad9',
    color: '#d9c0ff'
  }
}

const money = value =>
  `₹${Number(value || 0).toLocaleString('en-IN', {
    maximumFractionDigits: 2
  })}`

export default function Alerts() {
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dismissing, setDismissing] = useState(null)

  useEffect(() => {
    let cancelled = false

    axios.get(`${API}/anomalies`)
      .then(res => {
        if (!cancelled) {
          setAnomalies(res.data.anomalies || [])
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(
            typeof err.response?.data?.detail === 'string'
              ? err.response.data.detail
              : 'Could not load anomaly alerts'
          )
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  const dismissAlert = async (id) => {
    setDismissing(id)
    setError('')

    try {
      await axios.post(`${API}/anomalies/${id}/resolve`)
      setAnomalies(prev => prev.filter(a => a.id !== id))
    } catch (err) {
      console.error('Failed to dismiss:', err)
      setError(
        typeof err.response?.data?.detail === 'string'
          ? err.response.data.detail
          : 'Could not dismiss the alert'
      )
    } finally {
      setDismissing(null)
    }
  }

  if (loading) {
    return <div className="loading">Loading alerts...</div>
  }

  return (
    <div>
      <div className="eyebrow">SPENDING MONITORING</div>
      <h1>Alerts</h1>

      <p className="page-subtitle" style={{
        marginBottom: '2rem'
      }}>
        Anomalies and warnings detected by the AI agent.
      </p>

      {error && (
        <div className="form-error">
          ❌ {error}
        </div>
      )}

      {!error && anomalies.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div style={{
              fontSize: '2.5rem',
              marginBottom: '10px'
            }}>
              ✅
            </div>

            <h2>All Clear!</h2>
            <p>No anomalies detected in your spending.</p>
          </div>
        </div>
      ) : (
        <>
          {anomalies.length > 0 && (
            <p style={{
              color: '#94ae9c',
              fontSize: '14px',
              marginBottom: '1rem'
            }}>
              {anomalies.length} alert
              {anomalies.length !== 1 ? 's' : ''}
              {' '}need your attention.
            </p>
          )}

          {anomalies.map(anomaly => {
            const config =
              ANOMALY_CONFIG[anomaly.type] ||
              ANOMALY_CONFIG.unusual_merchant

            return (
              <div
                key={anomaly.id}
                style={{
                  background: config.bg,
                  border: `1px solid ${config.border}`,
                  borderLeft: `4px solid ${config.border}`,
                  borderRadius: '12px',
                  padding: '1.25rem',
                  marginBottom: '1rem'
                }}
              >
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  flexWrap: 'wrap',
                  gap: '16px'
                }}>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      marginBottom: '8px'
                    }}>
                      <span style={{ fontSize: '1.3rem' }}>
                        {config.icon}
                      </span>

                      <span style={{
                        fontWeight: 700,
                        color: config.color
                      }}>
                        {config.label}
                      </span>
                    </div>

                    <p style={{
                      color: config.color,
                      fontSize: '14px',
                      lineHeight: 1.6
                    }}>
                      {anomaly.description}
                    </p>

                    {anomaly.expenses && (
                      <p style={{
                        color: '#c0d2c4',
                        fontSize: '12px',
                        marginTop: '8px'
                      }}>
                        {anomaly.expenses.merchant}
                        {' · '}
                        {money(anomaly.expenses.total)}
                        {' · '}
                        {anomaly.expenses.date}
                      </p>
                    )}

                    {anomaly.flagged_at && (
                      <p style={{
                        color: '#94ae9c',
                        fontSize: '12px',
                        marginTop: '8px'
                      }}>
                        Detected{' '}
                        {new Date(anomaly.flagged_at)
                          .toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric'
                          })}
                      </p>
                    )}
                  </div>

                  <button
                    className="btn-danger"
                    onClick={() => dismissAlert(anomaly.id)}
                    disabled={dismissing === anomaly.id}
                  >
                    {dismissing === anomaly.id
                      ? 'Dismissing...'
                      : 'Dismiss'}
                  </button>
                </div>
              </div>
            )
          })}
        </>
      )}

      <div className="card" style={{
        marginTop: '2rem',
        background: '#102018'
      }}>
        <h2>How Anomaly Detection Works</h2>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
          gap: '1rem',
          marginTop: '1rem'
        }}>
          {[
            {
              icon: '📈',
              title: 'Spending Spike',
              desc: 'A category total exceeds 2× your 3-month average.'
            },
            {
              icon: '🔁',
              title: 'Duplicate Charge',
              desc: 'The same merchant and amount appear within 7 days.'
            },
            {
              icon: '⚠️',
              title: 'Unusual Merchant',
              desc: 'A first-time high-value merchant transaction.'
            }
          ].map(item => (
            <div
              key={item.title}
              style={{
                background: '#14271d',
                padding: '1.15rem',
                borderRadius: '10px',
                border: '1px solid #254333'
              }}
            >
              <div style={{
                fontSize: '1.5rem',
                marginBottom: '8px'
              }}>
                {item.icon}
              </div>

              <div style={{
                fontWeight: 600,
                fontSize: '14px',
                marginBottom: '6px',
                color: '#edfff2'
              }}>
                {item.title}
              </div>

              <div style={{
                fontSize: '12px',
                color: '#94ae9c',
                lineHeight: 1.6
              }}>
                {item.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
