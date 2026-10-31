# LoyalPay

**Simple, Data-Driven Customer Retention for Local Merchants**

LoyalPay helps small shopkeepers identify regular customers and re-engage those who stop visiting using the UPI/Paytm payments they already accept.

## 🎯 Demo Numbers (Fixed Seed = 42)

| Metric | Value |
|--------|-------|
| Regular Customers | ~307 |
| At-Risk Customers | ~38 (churners) |
| Campaign Targets | ~34 |
| Expected Redemptions | ~21 |
| Expected Revenue | ~₹3,300 |
| Cashback Spent | ~₹420 |
| ROI | ~7.6x |

## 🏗️ Architecture

```
Backend (Python)                 Frontend (React)
┌─────────────────────────────┐  ┌─────────────────────┐
│ FastAPI Server              │  │ Vite + Tailwind     │
│ ├── generator.py (Phase 1)  │  │ ├── PhoneFrame      │
│ ├── database.py  (Phase 2)  │  │ ├── Home/Regulars   │
│ ├── analytics.py (Phase 3)  │  │ ├── Insights/Offers │
│ ├── churn_model.py (Phase 4)│  │ ├── ChatPage        │
│ ├── optimizer.py (Phase 5)  │  │ └── SimulatorPanel  │
│ ├── api.py       (Phase 6)  │  └─────────────────────┘
│ └── agent.py     (Phase 8)  │
└─────────────────────────────┘
```

## 🚀 Quick Start

### Backend Setup

```bash
# Create virtual environment
cd /Users/utkrsshh/personal/loyalpay
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start backend server
uvicorn backend.api:app --reload --port 8000
```

### Frontend Setup

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173

### Using the Simulator

1. Click **"Simulate 60 Days"** to load demo data
2. Explore **Regulars** and **Insights** tabs
3. Go to **Offers** → Click **"Send Campaign"**
4. Click **"Simulate Next Week"** to process redemptions
5. See ROI results! 🎉

## 📁 Project Structure

```
loyalpay/
├── backend/
│   ├── __init__.py
│   ├── config.py        # Seed control & configuration
│   ├── generator.py     # Synthetic payment generator
│   ├── database.py      # SQLite + privacy hashing
│   ├── analytics.py     # RFM, segmentation, habits
│   ├── churn_model.py   # Gradient Boosting churn model
│   ├── optimizer.py     # Campaign optimization
│   ├── api.py           # FastAPI REST endpoints
│   └── agent.py         # Conversational AI (Gemini)
├── frontend/
│   ├── src/
│   │   ├── components/  # PhoneFrame, BottomNav, SimulatorPanel
│   │   ├── pages/       # Home, Regulars, Insights, Offers, Chat
│   │   ├── hooks/       # useApi
│   │   ├── utils/       # api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── test_config.py
│   ├── test_generator.py
│   ├── test_database.py
│   ├── test_analytics.py
│   ├── test_churn_model.py
│   └── test_optimizer.py
├── data/                # SQLite database
├── models/              # Trained ML models
├── requirements.txt
└── README.md
```

## 🔌 API Endpoints

### Simulator
- `POST /simulate/reset` - Reset simulation
- `POST /simulate/pay` - Simulate single payment
- `POST /simulate/fast-forward` - Load 60 days of data
- `POST /simulate/next-week` - Simulate campaign redemptions

### Data
- `GET /store-summary` - Store statistics
- `GET /customers` - Customer list with segments
- `GET /segments` - Segment counts
- `GET /insights` - AI insights & habits
- `GET /at-risk` - At-risk customers

### Campaigns
- `GET /suggest-offer` - AI campaign suggestion
- `POST /create-campaign` - Create & send campaign
- `GET /campaigns` - List campaigns
- `GET /roi/{campaign_id}` - Campaign ROI

### Chat
- `POST /chat` - AI chat (Hindi/Hinglish/English)

## 🧪 Running Tests

```bash
# All tests
pytest tests/ -v

# Specific phase
pytest tests/test_generator.py -v  # Phase 1
pytest tests/test_database.py -v   # Phase 2
pytest tests/test_analytics.py -v  # Phase 3
pytest tests/test_churn_model.py -v # Phase 4
pytest tests/test_optimizer.py -v   # Phase 5
```

## 🔐 Privacy

Customer VPAs are hashed using HMAC-SHA256:
- `rahul123@paytm` → `ff87beac...` → `#A12`
- Deterministic (same VPA → same hash)
- Irreversible (cannot recover VPA)
- DPDP Act compliant

## 📊 Segmentation Rules

| Segment | Criteria |
|---------|----------|
| Champion | 15+ visits AND active ≤3 days |
| Loyal | 5+ visits AND active ≤7 days |
| New | First visit within 14 days |
| At-Risk | Regular, 14-30 days inactive |
| Lost | 30+ days inactive |
| Casual | Irregular visitor |
| One-Time | Only 1 visit |

## 🤖 AI Features

### Churn Prediction
- Gradient Boosting classifier
- Features: recency, frequency, spend trends, visit gaps
- Trained on historical snapshot with 21-day observation window

### Offer Optimizer
- Ranks by: `churn_probability × avg_spend`
- Greedy budget fill
- Cashback = ~15% of basket
- Projects ROI based on 60% redemption rate

### Conversational Agent
- Hindi/Hinglish/English support
- Tool calling: `get_at_risk`, `suggest_offer`, `create_campaign`
- Grounded responses (no hallucination)
- Offline fallback for demo reliability

## 🎬 Demo Flow (5 minutes)

1. **Hook (30s)**: "80% of customers pay via UPI, yet Ramesh doesn't know when regulars stop coming"
2. **Live payment (45s)**: Click "Customer Pays" → Tag appears
3. **Fast-forward (60s)**: Load 60 days → 307 regulars, 38 at-risk
4. **AI chat (60s)**: "Kaun se customers wapas nahi aaye?" → Hindi reply with offer
5. **Close loop (45s)**: Send campaign → Simulate week → ₹3,200 recovered
6. **Architecture (30s)**: Show hashed VPAs, model features
7. **Business (30s)**: Pricing, ₹18 Cr ARR target

## 📜 License

MIT
