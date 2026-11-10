
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'

const API =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const samples = [
  {
    id: '441',
    title: 'Restaurant bill 01',
    amount: 441,
    file: '/samples/restaurant-441.png',
    filename: 'restaurant-441.png',
    expected: 'Garlic Naan ×2, Paneer Butter Masala ×1'
  },
  {
    id: '420',
    title: 'Restaurant bill 02',
    amount: 420,
    file: '/samples/restaurant-420.png',
    filename: 'restaurant-420.png',
    expected: 'Spl Meals ×2'
  }
]

const money = value =>
  `₹${Number(value || 0).toLocaleString('en-IN', {
    maximumFractionDigits: 2
  })}`

const errorMessage = (err, fallback) => {
  const detail = err.response?.data?.detail

  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail)

  return err.message || fallback
}

const getBadgeClass = category => {
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

export default function Upload() {
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')
  const [result, setResult] = useState(null)
  const [selected, setSelected] = useState(null)

  const [gmailSyncing, setGmailSyncing] = useState(false)
  const [gmailResult, setGmailResult] = useState(null)
  const [gmailError, setGmailError] = useState('')

  const uploadFile = useCallback(async file => {
    if (!file) return

    setStatus('uploading')
    setMessage('Reading receipt and extracting details...')
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await axios.post(
        `${API}/upload`,
        formData
      )

      setResult(res.data.parsed_data || null)
      setStatus('success')
      setMessage(
        'Receipt saved. Background analysis is running.'
      )
    } catch (err) {
      setStatus('error')
      setMessage(
        errorMessage(err, 'Could not analyze this receipt.')
      )
    }
  }, [])

  const onDrop = useCallback(
    files => {
      setSelected(null)
      uploadFile(files[0])
    },
    [uploadFile]
  )

  const {
    getRootProps,
    getInputProps,
    isDragActive
  } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp']
    },
    maxFiles: 1,
    disabled: status === 'uploading'
  })

  const analyzeSample = async () => {
    if (!selected || status === 'uploading') return

    try {
      setStatus('uploading')
      setMessage('Loading sample image...')
      setResult(null)

      const response = await fetch(selected.file)

      if (!response.ok) {
        throw new Error(
          'Sample image not found. Check public/samples.'
        )
      }

      const blob = await response.blob()

      const file = new File(
        [blob],
        selected.filename,
        { type: 'image/png' }
      )

      await uploadFile(file)
    } catch (err) {
      setStatus('error')
      setMessage(
        err.message || 'Could not load sample receipt'
      )
    }
  }

  const handleGmailSync = async () => {
    setGmailSyncing(true)
    setGmailResult(null)
    setGmailError('')

    try {
      const res = await axios.get(`${API}/gmail-sync`)

      setGmailResult(
        `Imported ${res.data.bills_imported ?? 0} bills (${res.data.skipped ?? 0} skipped)`
      )
    } catch (err) {
      setGmailError(
        errorMessage(err, 'Gmail synchronization failed')
      )
    } finally {
      setGmailSyncing(false)
    }
  }

  return (
    <div>
      <div className="upload-intro">
        <div>
          <div className="eyebrow">EXPENSE CAPTURE</div>
          <h1>Add expenses</h1>
          <p className="page-subtitle">
            Your receipts, organized without the busywork.
          </p>
        </div>

        <span className="upload-tag">
          SMART RECEIPT SCANNER
        </span>
      </div>

      <div className="upload-layout">
        <section className="card">
          <h2>Upload a receipt</h2>

          <p
            className="muted"
            style={{ marginBottom: 18 }}
          >
            Take a photo or choose one from your device.
          </p>

          <div
            {...getRootProps()}
            className={`upload-dropzone ${
              isDragActive ? 'dragging' : ''
            } ${
              status === 'uploading' ? 'disabled' : ''
            }`}
          >
            <input {...getInputProps()} />

            <div className="upload-drop-icon">↥</div>

            <p>
              {isDragActive ? (
                'Drop your receipt here'
              ) : (
                <>
                  Drag your receipt here, or{' '}
                  <strong>browse files</strong>
                </>
              )}
            </p>

            <p className="upload-help">
              JPG, PNG, WEBP · One receipt at a time
            </p>
          </div>

          <div className="upload-section-label">
            NO RECEIPT? TRY A SAMPLE
          </div>

          <div className="sample-grid">
            {samples.map(sample => (
              <button
                key={sample.id}
                type="button"
                className={`sample-tile ${
                  selected?.id === sample.id
                    ? 'selected'
                    : ''
                }`}
                onClick={() => {
                  setSelected(sample)
                  setResult(null)
                  setStatus('idle')
                  setMessage('')
                }}
              >
                <img
                  src={sample.file}
                  alt={`${sample.title} showing ${money(sample.amount)}`}
                />

                <strong>{sample.title}</strong>

                <small>
                  Hotel Amirtha · {money(sample.amount)}
                </small>
              </button>
            ))}
          </div>

          {selected && (
            <div className="sample-detail">
              <strong>
                {selected.title} — {money(selected.amount)}
              </strong>

              <p className="sample-note">
                Expected items: {selected.expected}.
                Compare the OCR output with the original
                receipt to check extraction accuracy.
              </p>

              <img
                src={selected.file}
                alt={`Full-size ${selected.title}`}
              />

              <p className="sample-note">
                <strong>Demo notice:</strong> Analyzing
                this sample saves it as an expense.
                Repeated tests may create duplicates.
              </p>

              <button
                type="button"
                className="btn-primary"
                disabled={status === 'uploading'}
                onClick={analyzeSample}
              >
                {status === 'uploading'
                  ? 'Analyzing...'
                  : 'Analyze sample receipt'}
              </button>
            </div>
          )}

          {status !== 'idle' && (
            <div
              role="status"
              className={`upload-notice ${
                status === 'error' ? 'error' : ''
              }`}
            >
              {message}
            </div>
          )}

          {result && (
            <div className="parsed-result">
              <h2>Extracted details</h2>

              <div className="parsed-grid">
                <div>
                  <small>MERCHANT</small>
                  <strong>
                    {result.merchant || '—'}
                  </strong>
                </div>

                <div>
                  <small>DATE</small>
                  <strong>
                    {result.date || '—'}
                  </strong>
                </div>

                <div>
                  <small>TOTAL</small>
                  <strong className="parsed-total">
                    {money(result.total)}
                  </strong>
                </div>

                <div>
                  <small>CATEGORY</small>
                  <span
                    className={`badge ${getBadgeClass(
                      result.category ||
                      result.merchant_category_hint
                    )}`}
                  >
                    {result.category ||
                      result.merchant_category_hint ||
                      'Other'}
                  </span>
                </div>
              </div>

              {Array.isArray(result.line_items) &&
                result.line_items.length > 0 && (
                  <>
                    <div className="upload-section-label">
                      LINE ITEMS
                    </div>

                    {result.line_items.map((item, i) => (
                      <div
                        className="parsed-item"
                        key={i}
                      >
                        <span>
                          {item.name || 'Item'} ×
                          {item.qty ?? 1}
                        </span>

                        <strong>
                          {money(item.amount)}
                        </strong>
                      </div>
                    ))}
                  </>
                )}
            </div>
          )}
        </section>

        <aside className="card">
          <h2>Connect your Gmail</h2>

          <p
            className="muted"
            style={{ marginBottom: 18 }}
          >
            Bring bills and order confirmations into
            ReceiptBrain. Supports merchants like
            Swiggy, Zomato, Amazon and Airtel.
          </p>

          <button
            type="button"
            className="btn-primary"
            onClick={handleGmailSync}
            disabled={gmailSyncing}
          >
            {gmailSyncing
              ? 'Syncing...'
              : 'Sync Gmail bills'}
          </button>

          {gmailResult && (
            <div
              className="form-success"
              style={{ marginTop: 14 }}
            >
              {gmailResult}
            </div>
          )}

          {gmailError && (
            <div
              className="form-error"
              style={{ marginTop: 14 }}
            >
              {gmailError}
            </div>
          )}

          <div className="upload-promo">
            <div className="promo-label">
              RECEIPTBRAIN
            </div>

            <div className="promo-title">
              Spend smarter.
            </div>

            <p>
              Search your transactions, spot unusual
              spending and understand where your
              money goes.
            </p>

            <div className="promo-line" />
          </div>
        </aside>
      </div>
    </div>
  )
}
