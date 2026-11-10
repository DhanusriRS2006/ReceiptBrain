
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const categories = [
  'Food', 'Travel', 'Shopping', 'Utilities',
  'Entertainment', 'Subscriptions', 'Healthcare', 'Other'
]

const initialForm = () => ({
  merchant: '',
  total: '',
  date: new Date().toLocaleDateString('en-CA'),
  category: 'Food',
  payment_method: 'UPI',
  notes: ''
})

export default function ManualExpense() {
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const update = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const save = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')

    const amount = Number(form.total)

    if (!form.merchant.trim() || !Number.isFinite(amount) || amount <= 0) {
      setError('Enter a merchant and a valid amount greater than zero.')
      return
    }

    setSaving(true)

    try {
      await axios.post(`${API}/expenses/manual`, {
        ...form,
        merchant: form.merchant.trim(),
        total: amount
      })

      setMessage('Expense saved successfully!')
      setForm(initialForm())
    } catch (err) {
      setError(
        err.response?.data?.detail
          ? JSON.stringify(err.response.data.detail)
          : err.message
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="form-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">TRANSACTIONS</div>
          <h1>Add Expense</h1>
          <p className="page-subtitle">
            Record your spending without uploading a receipt.
          </p>
        </div>
      </div>

      <form className="card manual-form" onSubmit={save}>
        <div className="form-header">
          <div className="form-icon">＋</div>
          <div>
            <h2>New transaction</h2>
            <p className="muted">Enter your expense details below.</p>
          </div>
        </div>

        <div className="form-field">
          <label htmlFor="merchant">Merchant name</label>
          <input
            id="merchant"
            required
            maxLength={150}
            placeholder="e.g. Swiggy, Amazon, Uber"
            value={form.merchant}
            onChange={e => update('merchant', e.target.value)}
          />
        </div>

        <div className="form-grid">
          <div className="form-field">
            <label htmlFor="amount">Amount (₹)</label>
            <input
              id="amount"
              type="number"
              required
              min="0.01"
              step="0.01"
              placeholder="0.00"
              value={form.total}
              onChange={e => update('total', e.target.value)}
            />
          </div>

          <div className="form-field">
            <label htmlFor="date">Transaction date</label>
            <input
              id="date"
              type="date"
              required
              value={form.date}
              onChange={e => update('date', e.target.value)}
            />
          </div>

          <div className="form-field">
            <label htmlFor="category">Category</label>
            <select
              id="category"
              value={form.category}
              onChange={e => update('category', e.target.value)}
            >
              {categories.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="payment">Payment method</label>
            <select
              id="payment"
              value={form.payment_method}
              onChange={e => update('payment_method', e.target.value)}
            >
              {['UPI', 'Cash', 'Credit Card', 'Debit Card', 'Net Banking', 'Other']
                .map(p => <option key={p}>{p}</option>)}
            </select>
          </div>
        </div>

        <div className="form-field">
          <label htmlFor="notes">Notes (optional)</label>
          <textarea
            id="notes"
            rows={3}
            maxLength={1000}
            placeholder="What was this expense for?"
            value={form.notes}
            onChange={e => update('notes', e.target.value)}
          />
        </div>

        {error && <div className="form-error">{error}</div>}
        {message && <div className="form-success">{message}</div>}

        <div className="form-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => navigate('/dashboard')}
          >
            View Dashboard
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving...' : '＋ Save Expense'}
          </button>
        </div>
      </form>
    </div>
  )
}
