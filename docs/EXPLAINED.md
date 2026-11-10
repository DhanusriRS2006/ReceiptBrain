
# ReceiptBrain — Engineering Notes

This document explains how ReceiptBrain works, the technical decisions behind it, and some of the problems I encountered while building it.

## 1. Project Overview

ReceiptBrain is a full-stack expense tracking application built with React, FastAPI, and Supabase.

It supports three ways of recording expenses:

- Uploading receipt images
- Importing bills from Gmail
- Adding expenses manually

After an expense is recorded, the backend stores it in PostgreSQL and can generate embeddings, detect anomalies, and run AI agents to produce insights.

The application also includes spending dashboards, monthly trends, forecasting, and natural-language expense search.

## 2. System Architecture

```text
Receipt Image ──► Gemini Vision ──┐
                                  │
Gmail Bills ────► Email Parser ───┼──► FastAPI
                                  │       │
Manual Entry ─────────────────────┘       │
                                          ▼
                                  Data Validation
                                          │
                                          ▼
                                  Supabase PostgreSQL
                                          │
                    ┌─────────────────────┼────────────────────┐
                    │                     │                    │
                    ▼                     ▼                    ▼
               Embeddings             Analytics            CrewAI
                    │                     │                    │
                    ▼                     ▼                    ▼
                 pgvector              Anomalies            Insights
                    │                     │                    │
                    └─────────────────────┼────────────────────┘
                                          │
                                          ▼
                                     React UI
```

The frontend communicates with FastAPI through REST endpoints. Supabase stores the transactions, while background tasks handle additional processing.

## 3. Receipt Extraction — `ocr.py`

Receipt images are processed using a multimodal model accessed through OpenRouter.

I chose this approach because receipts have different layouts. Some place the total at the bottom, while others include multiple tax fields, item quantities, and discounts.

A traditional OCR engine primarily extracts text. A vision-language model can also interpret the relationship between fields.

The extraction pipeline is:

1. Receive the receipt image.
2. Send it to the configured vision model.
3. Extract structured JSON.
4. Validate and normalize the fields.
5. Save the transaction.

The extracted fields include:

- Merchant
- Date
- Total amount
- Currency
- Category
- Payment method
- Line items
- Taxes
- Parsing confidence

### Problem I encountered

Initially, some model responses contained additional text or incomplete JSON. This caused parsing failures.

I added defensive JSON handling in `jsonutil.py` and validation before inserting data into Supabase.

The main lesson was that LLM output should never be treated as guaranteed valid data.

## 4. Database Design — Supabase

ReceiptBrain uses PostgreSQL through Supabase.

The main tables are:

| Table | Purpose |
|---|---|
| `receipts` | Stores original input and source information |
| `expenses` | Stores normalized transactions |
| `anomalies` | Stores detected unusual transactions |
| `insights` | Stores generated financial insights |

I separated receipts from expenses because the original source and the extracted transaction serve different purposes.

For example, keeping the original receipt information allows the transaction to be reprocessed if extraction logic changes.

The `expenses` table also includes a `vector(384)` embedding column for semantic search.

### Manual expense integration

When I added manual expense entry, the database initially rejected the new source type.

The `receipts.source` constraint allowed image, Gmail, PDF, and text sources, but not `manual`.

I updated the constraint to support manual entries.

Another issue involved the `taxes` field. The database expected a numeric value, but the request initially supplied an empty array. Changing it to `0.0` resolved the type mismatch.

These errors reinforced the importance of keeping API validation and database schemas consistent.

## 5. Semantic Search — `embeddings.py`

One of the main features of ReceiptBrain is searching expenses using natural language.

I used `all-MiniLM-L6-v2` from Sentence Transformers to generate embeddings.

Each embedding contains 384 dimensions and is stored in PostgreSQL using pgvector.

Cosine similarity is used to identify semantically related transactions.

For example, a search for:

`food delivery`

can retrieve expenses associated with food-ordering services.

### Why pure vector search was not enough

Initially, I relied mainly on embedding similarity.

This worked reasonably well for general descriptions, but exact financial queries were less reliable.

For example:

`Swiggy in 2025`

could return semantically related transactions without correctly prioritizing the merchant and year.

Similarly:

`food expenses above 400`

requires an exact numerical condition that embeddings cannot reliably enforce.

### Hybrid search

To improve this, I introduced a hybrid search approach combining:

- Semantic similarity
- Merchant matching
- Category matching
- Amount filters
- Date filters
- Relevance ranking

The idea is to use embeddings for meaning and structured filters for exact conditions.

For financial data, this distinction is important because an expense that is semantically similar is not necessarily a correct answer.

### Current limitation

The current approach is intended for a relatively small dataset.

For larger datasets, structured filtering and ranking should be pushed further into PostgreSQL instead of processing large result sets in Python.

## 6. Expense Ingestion — `ingest.py`

The ingestion module handles database insertion.

Different input sources eventually produce a normalized expense dictionary.

The common ingestion function saves:

1. A receipt/source record.
2. A structured expense record.

It returns the expense ID, which can then be used for background processing.

This keeps the storage logic reusable across image uploads, Gmail imports, and manual expenses.

One improvement I would make is wrapping the receipt and expense inserts in a single database transaction.

Currently, if the first insert succeeds and the second fails, an incomplete record may remain.

## 7. Analytics and Forecasting — `analytics.py`

ReceiptBrain calculates spending information using Python and database records.

The analytics features include:

- Monthly spending totals
- Category-wise spending
- Historical trends
- Spending forecasts
- Lifestyle inflation detection
- Anomaly detection

### Forecasting

The project uses a weighted-average approach based on historical spending.

Recent spending can receive greater weight than older spending.

This provides a simple, explainable baseline without requiring a large training dataset.

It is useful for estimating future expenses, but the result should not be treated as a guaranteed prediction.

### Why calculations are done in code

I chose to keep financial calculations separate from the AI agents.

LLMs can make arithmetic mistakes, so totals, thresholds, and comparisons are calculated deterministically.

The agents receive these results and generate interpretations rather than independently calculating the numbers.

## 8. Anomaly Detection

ReceiptBrain checks transactions for three main types of anomalies.

### Duplicate transactions

Potential duplicates are identified using transaction similarity, amount differences, and nearby dates.

The documented rule considers high embedding similarity, amounts within approximately 1%, and transactions within a seven-day window.

### Spending spikes

A spending spike is flagged when spending is significantly higher than the historical baseline.

The documented rule compares spending against recent averages and applies an additional minimum increase threshold.

### New merchants

Transactions involving merchants that have not appeared previously can be flagged for review.

### Why rule-based detection?

The project does not have a large labeled fraud dataset.

Rule-based detection is easier to implement, test, and explain for the available data.

These alerts indicate unusual behavior, not confirmed fraud.

## 9. Multi-Agent Pipeline — `agents/`

ReceiptBrain includes a CrewAI pipeline for processing and interpreting expenses.

The pipeline contains four responsibilities:

1. Parser/Validator
2. Categorizer
3. Anomaly Detector
4. Insight Generator

The agents execute sequentially.

I chose sequential execution because the steps have a clear dependency order and are easier to debug.

Groq-hosted Llama models are used for agent processing.

The agent pipeline is optional and can be disabled using:

```env
RUN_AGENTS_ON_UPLOAD=false
```

This is useful when API limits are reached or when running the application on a resource-constrained server.

The core expense tracker does not depend on the agents being available.

## 10. Gmail Integration — `gmail_sync.py`

ReceiptBrain can import supported bills and order confirmations from Gmail.

It uses Google's OAuth 2.0 authorization flow with the Gmail read-only scope.

The workflow is:

1. Authorize Gmail access.
2. Retrieve matching emails.
3. Extract message content.
4. Parse expense details.
5. Save transactions.
6. Skip previously imported messages.

Gmail message IDs are used to prevent repeated imports.

The implementation also handles MIME message structures and HTML email content.

### Current limitation

The OAuth flow is configured for local development.

Deploying Gmail synchronization publicly would require a web-based OAuth flow, secure token storage, and user-specific authorization.

For now, Gmail synchronization is best demonstrated locally.

## 11. FastAPI Backend — `main.py`

FastAPI connects the frontend, AI services, and database.

Some important endpoints are:

| Endpoint | Purpose |
|---|---|
| `POST /upload` | Upload and process a receipt |
| `POST /upload-text` | Extract expenses from text |
| `POST /expenses/manual` | Add a manual expense |
| `GET /expenses` | Retrieve transactions |
| `GET /summary` | Retrieve spending summaries |
| `GET /expenses/by-month` | Monthly spending data |
| `GET /query` | Search expenses |
| `GET /anomalies` | Retrieve anomaly alerts |
| `GET /insights` | Retrieve generated insights |
| `POST /analyze/{expense_id}` | Run agent analysis |
| `GET /gmail-sync` | Import Gmail bills |

### Background processing

After saving an uploaded expense, FastAPI can schedule additional work using `BackgroundTasks`.

This includes:

- Embedding generation
- Anomaly checks
- Optional agent processing

This reduces the time spent waiting for the initial HTTP response.

However, `BackgroundTasks` is not a persistent job queue. A server restart can interrupt unfinished work.

For production, I would replace this with a queue and dedicated worker.

## 12. React Frontend

The frontend is built with React and Vite.

The main pages are:

| Page | Function |
|---|---|
| Upload | Receipt uploads, sample receipts, Gmail sync |
| Dashboard | Spending summaries and transactions |
| Add Expense | Manual expense entry |
| Trends | Spending patterns and forecasts |
| Alerts | Anomaly review |
| Search | Natural-language expense retrieval |

I redesigned the interface using a lighter fintech-style theme with lime-green accents, white cards, and navy highlights.

The frontend uses Axios for API requests, React Router for navigation, and Recharts for data visualization.

### Sample receipt testing

The Upload page includes two restaurant receipt examples:

- Hotel Amirtha Darling Classic — ₹441
- Hotel Amirtha Darling Classic — ₹420

These allow users to test the extraction flow without uploading their own receipts.

Currently, sample analysis uses the normal upload endpoint, so the transaction is saved to the database.

A future improvement is to add a preview-only endpoint and save the expense only after user confirmation.

## 13. Deployment Considerations

The planned deployment uses:

- Vercel for the React frontend
- Render for the FastAPI backend
- Supabase for PostgreSQL
- OpenRouter and Groq for model access

The main challenge is backend resource usage.

Sentence Transformers and CrewAI introduce dependencies that may exceed the memory available on some free hosting plans.

The backend needs to be tested under actual deployment constraints.

### Security work still required

Before making the application available to public users with personal financial information, I need to implement:

- User authentication
- Per-user data isolation
- Supabase Row Level Security
- Authorization checks on API endpoints
- Secure OAuth token storage
- API rate limiting
- Improved upload validation

Until these are implemented, a public demo should use synthetic data and avoid exposing private financial records.

## 14. What I Would Improve Next

### Receipt processing

Add an editable preview so users can correct extracted values before saving.

### Search

Move more filtering into PostgreSQL and improve exact merchant, date, and amount matching.

### Background jobs

Replace FastAPI BackgroundTasks with a persistent queue and worker.

### Database reliability

Use transactional insertion for related receipt and expense records.

### Testing

Add automated tests for receipt parsing, financial calculations, anomaly rules, and API endpoints.

### Deployment

Optimize memory usage and separate heavy AI processing from the main API where necessary.

## 15. Key Takeaways

Building ReceiptBrain involved more than integrating AI APIs.

The main engineering challenges were:

- Handling malformed LLM responses
- Validating extracted financial information
- Maintaining consistency between API requests and database schemas
- Improving semantic search for exact financial queries
- Separating deterministic calculations from AI-generated interpretations
- Managing background processing and external API limitations

The most important lesson was that AI features work best when combined with conventional software engineering practices.

ReceiptBrain is still being improved, particularly around deployment, security, and reliability, but the project has provided practical experience building an AI-powered full-stack application.
