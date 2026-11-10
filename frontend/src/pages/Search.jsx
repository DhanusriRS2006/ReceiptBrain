
import { useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const EXAMPLE_QUERIES = [
  'Swiggy orders last month',
  'food delivery above 400',
  'travel and transport',
  'subscriptions and streaming',
  'electricity and utilities bills'
]

const getBadgeClass = (category) => {
  const map = {
    Food: 'badge-food',
    Travel: 'badge-travel',
    Shopping: 'badge-shopping',
    Utilities: 'badge-utilities',
    Entertainment: 'badge-entertainment',
    Subscriptions: 'badge-subscriptions',
    Healthcare: 'badge-healthcare'
  }
  return map[category] || 'badge-other'
}

const money = (value) =>
  `₹${Number(value || 0).toLocaleString('en-IN', {
    maximumFractionDigits: 2
  })}`

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [totalFound, setTotalFound] = useState(0)
  const [error, setError] = useState('')

  const handleSearch = async (searchQuery = query) => {
    const text = searchQuery.trim()
    if (!text || loading) return

    setLoading(true)
    setSearched(true)
    setQuery(text)
    setError('')

    try {
      const res = await axios.get(`${API}/query`, {
        params: { q: text, limit: 20 }
      })

      const found = res.data.results || []
      setResults(found)
      setTotalFound(found.length)
    } catch (err) {
      console.error('Search failed:', err)
      setResults([])
      setTotalFound(0)
      setError(
        typeof err.response?.data?.detail === 'string'
          ? err.response.data.detail
          : err.message || 'Search failed'
      )
    } finally {
      setLoading(false)
    }
  }

  const totalAmount = results.reduce(
    (sum, r) => sum + Number(r.total || 0), 0
  )

  return (
    <div>
      <div className="eyebrow">SMART EXPENSE DISCOVERY</div>
      <h1>Search Expenses</h1>
      <p className="page-subtitle" style={{ marginBottom: '2rem' }}>
        Search in plain English — powered by semantic vector search.
      </p>

      <div className="card">
        <h2>Find a transaction</h2>

        <div style={{
          display: 'flex',
          gap: '10px',
          alignItems: 'center',
          flexWrap: 'wrap'
        }}>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') handleSearch()
            }}
            placeholder="e.g. Swiggy food orders above 300 last month"
            aria-label="Search expenses"
            style={{
              flex: 1,
              minWidth: '200px',
              padding: '12px 16px',
              borderRadius: '10px',
              border: '1px solid #365542',
              background: '#0b1810',
              color: '#edfff2',
              fontSize: '14px'
            }}
          />

          <button
            className="btn-primary"
            onClick={() => handleSearch()}
            disabled={loading || !query.trim()}
          >
            {loading ? '⏳ Searching...' : '🔍 Search'}
          </button>
        </div>

        <div style={{ marginTop: '18px' }}>
          <span style={{
            color: '#94ae9c',
            fontSize: '12px',
            marginRight: '6px'
          }}>
            Try:
          </span>

          {EXAMPLE_QUERIES.map(q => (
            <button
              key={q}
              type="button"
              onClick={() => handleSearch(q)}
              disabled={loading}
              style={{
                background: '#172c1e',
                border: '1px solid #365542',
                borderRadius: '20px',
                padding: '6px 12px',
                fontSize: '12px',
                color: '#8cffab',
                margin: '4px',
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {searched && (
        <div className="card">
          {loading ? (
            <div className="loading">Searching expenses...</div>
          ) : error ? (
            <div className="form-error">
              ❌ {error}
            </div>
          ) : results.length > 0 ? (
            <>
              <div className="section-heading" style={{
                marginBottom: '1rem',
                flexWrap: 'wrap'
              }}>
                <h2>
                  {totalFound} result{totalFound !== 1 ? 's' : ''}
                  {' '}for "{query}"
                </h2>

                <span style={{
                  fontWeight: 700,
                  color: '#8cffab'
                }}>
                  Total: {money(totalAmount)}
                </span>
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Merchant</th>
                      <th>Category</th>
                      <th>Date</th>
                      <th>Match Score</th>
                      <th style={{ textAlign: 'right' }}>
                        Amount
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {results.map((result, index) => {
                      const score = Math.max(
                        0,
                        Math.min(100, Number(result.similarity || 0) * 100)
                      )

                      return (
                        <tr key={result.id || index}>
                          <td>
                            <strong>{result.merchant || 'Unknown'}</strong>
                          </td>

                          <td>
                            <span className={`badge ${getBadgeClass(result.category)}`}>
                              {result.category || 'Other'}
                            </span>
                          </td>

                          <td style={{ color: '#94ae9c' }}>
                            {result.date || '—'}
                          </td>

                          <td>
                            <div style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px'
                            }}>
                              <div style={{
                                width: '65px',
                                height: '7px',
                                background: '#294232',
                                borderRadius: '5px',
                                overflow: 'hidden'
                              }}>
                                <div style={{
                                  width: `${score}%`,
                                  height: '100%',
                                  background: '#8cffab',
                                  borderRadius: '5px'
                                }} />
                              </div>

                              <span style={{
                                fontSize: '12px',
                                color: '#94ae9c'
                              }}>
                                {Math.round(score)}%
                              </span>
                            </div>
                          </td>

                          <td className="amount-cell">
                            {money(result.total)}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">⌕</div>
              <h2>No results found</h2>
              <p>
                Try a different search term or upload more receipts first.
              </p>
            </div>
          )}
        </div>
      )}

      {!searched && (
        <div className="card" style={{
          background: '#14271d'
        }}>
          <h2>How Search Works</h2>
          <p style={{
            fontSize: '14px',
            color: '#94ae9c',
            lineHeight: 1.7
          }}>
            ReceiptBrain converts your search query into a semantic
            vector embedding and finds similar expenses using
            pgvector cosine similarity.
            You can search by meaning, not just exact words.
            For example, "food delivery" can find Swiggy and
            Zomato transactions even without those merchant names
            appearing in your query.
          </p>
        </div>
      )}
    </div>
  )
}
