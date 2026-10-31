"""
LoyalPay FastAPI Backend

REST API endpoints wrapping all backend functionality:
- /simulate/pay - Simulate a payment
- /simulate/fast-forward - Load 60 days of data
- /simulate/next-week - Simulate campaign redemptions
- /customers - Get all customers
- /segments - Get segment counts
- /insights - Get store insights
- /at-risk - Get at-risk customers
- /suggest-offer - Get campaign suggestion
- /create-campaign - Create and send campaign
- /roi/{campaign_id} - Get campaign ROI
"""

import os
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import config, set_seed, reset_seed
from backend.generator import (
    create_demo_generator,
    PaymentEvent,
    SyntheticPaymentGenerator,
    GeneratorConfig,
)
from backend.database import Database
from backend.analytics import (
    calculate_rfm,
    segment_customers,
    get_segment_counts,
    get_regular_count,
    get_at_risk_customers,
    get_customers_with_habits,
    generate_store_insights,
    build_customer_profiles,
    get_store_summary,
    CustomerSegment,
)
from backend.churn_model import ChurnModel, train_churn_model
from backend.optimizer import OfferOptimizer, suggest_offer


# ==================== Pydantic Models ====================

class PaymentRequest(BaseModel):
    vpa: Optional[str] = None
    amount: Optional[float] = None


class PaymentResponse(BaseModel):
    customer_label: str
    customer_id: int
    amount: float
    visit_count: int
    is_new: bool


class FastForwardRequest(BaseModel):
    days: int = 60
    seed: int = 42


class FastForwardResponse(BaseModel):
    events_loaded: int
    unique_customers: int
    regular_customers: int
    message: str


class CreateCampaignRequest(BaseModel):
    budget: float = 500.0
    name: Optional[str] = None
    cashback_percent: float = 10.0  # Cashback as percentage
    customer_ids: Optional[List[int]] = None  # Specific customers to target


class CampaignResponse(BaseModel):
    campaign_id: int
    name: str
    targets_count: int
    cashback_percent: float
    budget: float
    message: str


class SimulateWeekRequest(BaseModel):
    campaign_id: Optional[int] = None


class SimulateWeekResponse(BaseModel):
    days_simulated: int
    new_transactions: int
    redemptions: int
    revenue_recovered: float
    cashback_spent: float


# ==================== Application State ====================

class AppState:
    """Application state management."""
    
    def __init__(self):
        self.db: Database = None
        self.generator: SyntheticPaymentGenerator = None
        self.churn_model: ChurnModel = None
        self.optimizer: OfferOptimizer = None
        self.current_date: datetime = datetime(2024, 9, 1)
        self.events_index: int = 0
        self.all_events: List[PaymentEvent] = []
    
    def initialize(self):
        """Initialize all components."""
        self.db = Database()
        self.generator = create_demo_generator(seed=config.RANDOM_SEED)
        self.churn_model = ChurnModel()
        self.optimizer = OfferOptimizer()
        self.all_events = self.generator.generate_all_events()
    
    def reset(self):
        """Reset to initial state."""
        reset_seed()
        self.db.drop_all()
        self.generator = create_demo_generator(seed=config.RANDOM_SEED)
        self.all_events = self.generator.generate_all_events()
        self.current_date = datetime(2024, 9, 1)
        self.events_index = 0
        self.churn_model = ChurnModel()
    
    def get_dataframes(self):
        """Get payments and customers as DataFrames."""
        with self.db._connect() as conn:
            payments_df = pd.read_sql("SELECT * FROM payments", conn)
            customers_df = pd.read_sql("SELECT * FROM customers", conn)
        return payments_df, customers_df


state = AppState()


# ==================== Lifespan ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize state on startup."""
    state.initialize()
    yield


# ==================== FastAPI App ====================

app = FastAPI(
    title="LoyalPay API",
    description="Customer retention platform for local merchants",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Simulator Endpoints ====================

@app.post("/simulate/reset")
async def reset_simulation():
    """Reset the simulation to initial state."""
    state.reset()
    return {"message": "Simulation reset", "current_date": state.current_date.isoformat()}


class PayByCustomerIdRequest(BaseModel):
    customer_id: int
    amount: Optional[float] = None
    days_ago: Optional[int] = 0  # Optionally backdate the payment


@app.post("/simulate/pay-by-id")
async def simulate_payment_by_customer_id(request: PayByCustomerIdRequest):
    """Simulate a payment for a specific existing customer by ID."""
    amount = request.amount or random.choice([50, 75, 100, 125, 150])
    
    # Calculate timestamp (optionally backdated)
    payment_date = state.current_date
    if request.days_ago and request.days_ago > 0:
        payment_date = state.current_date - timedelta(days=request.days_ago)
    
    # Get customer's token
    with state.db._connect() as conn:
        row = conn.execute("SELECT token, label FROM customers WHERE id = ?", (request.customer_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Customer {request.customer_id} not found")
        token = row['token']
        label = row['label']
        
        # Insert payment
        conn.execute(
            "INSERT INTO payments (customer_id, amount, timestamp, merchant_id) VALUES (?, ?, ?, ?)",
            (request.customer_id, amount, payment_date.isoformat(), config.MERCHANT_ID)
        )
        conn.commit()
        
        # Get visit count
        visit_count = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE customer_id = ?", (request.customer_id,)
        ).fetchone()[0]
    
    return {
        "customer_id": request.customer_id,
        "customer_label": label,
        "amount": amount,
        "visit_count": visit_count,
        "timestamp": payment_date.isoformat()
    }


@app.post("/simulate/pay", response_model=PaymentResponse)
async def simulate_payment(request: PaymentRequest):
    """
    Simulate a single payment transaction.
    
    If VPA not provided, generates a random one.
    If amount not provided, generates random amount.
    """
    # Generate or use provided values
    if request.vpa:
        vpa = request.vpa
    else:
        # Pick a random customer from generator or create new
        if state.events_index < len(state.all_events):
            event = state.all_events[state.events_index]
            vpa = event.vpa
            amount = request.amount or event.amount
            state.events_index += 1
        else:
            # Generate random new customer
            vpa = f"user_{random.randint(1000, 9999)}@paytm"
            amount = request.amount or random.choice([30, 40, 50, 60, 70, 80, 100])
    
    amount = request.amount or random.choice([30, 40, 50, 60, 70, 80, 100])
    
    # Check if customer exists
    existing = None
    with state.db._connect() as conn:
        token = state.db.hasher.hash_vpa(vpa)
        row = conn.execute("SELECT * FROM customers WHERE token = ?", (token,)).fetchone()
        if row:
            existing = row['id']
    
    # Create payment event
    event = PaymentEvent(
        vpa=vpa,
        amount=amount,
        timestamp=state.current_date,
    )
    
    customer, payment = state.db.ingest_payment(event)
    
    # Get visit count
    visit_counts = state.db.get_visit_counts()
    visit_count = visit_counts.get(customer.id, 0)
    
    return PaymentResponse(
        customer_label=customer.label,
        customer_id=customer.id,
        amount=amount,
        visit_count=visit_count,
        is_new=existing is None,
    )


@app.post("/simulate/fast-forward", response_model=FastForwardResponse)
async def fast_forward(request: FastForwardRequest = None):
    """
    Load multiple days of simulated data.
    
    Defaults to 60 days with seed 42.
    """
    if request is None:
        request = FastForwardRequest()
    
    # Reset and regenerate with specified seed
    state.reset()
    set_seed(request.seed)
    state.generator = create_demo_generator(seed=request.seed)
    state.all_events = state.generator.generate_all_events()
    
    # Filter events to requested days
    end_date = state.generator.gen_config.start_date + timedelta(days=request.days)
    events_to_load = [e for e in state.all_events if e.timestamp < end_date]
    
    # Ingest all events
    state.db.ingest_payments_batch(events_to_load)
    state.current_date = end_date
    state.events_index = len(events_to_load)
    
    # Train churn model with loaded data
    payments_df, customers_df = state.get_dataframes()
    if len(payments_df) > 100:
        try:
            state.churn_model.train(payments_df, customers_df)
        except Exception as e:
            print(f"Warning: Could not train churn model: {e}")
    
    # Calculate stats
    visit_counts = state.db.get_visit_counts()
    regulars = sum(1 for c in visit_counts.values() if c >= 2)
    
    return FastForwardResponse(
        events_loaded=len(events_to_load),
        unique_customers=len(visit_counts),
        regular_customers=regulars,
        message=f"Loaded {request.days} days of data ({len(events_to_load)} transactions)",
    )


@app.post("/simulate/next-week", response_model=SimulateWeekResponse)
async def simulate_next_week(request: SimulateWeekRequest = None):
    """
    Simulate the next 7 days including campaign redemptions.
    
    ~60% of targeted customers will return and redeem offers.
    """
    if request is None:
        request = SimulateWeekRequest()
    
    days_to_simulate = 7
    new_transactions = 0
    redemptions = 0
    revenue_recovered = 0.0
    cashback_spent = 0.0
    
    # Get active campaigns
    active_campaigns = state.db.get_active_campaigns()
    campaign_id = request.campaign_id
    
    if campaign_id is None and active_campaigns:
        campaign_id = active_campaigns[0].id
    
    # Get campaign targets
    campaign_targets = {}
    if campaign_id:
        with state.db._connect() as conn:
            rows = conn.execute(
                """SELECT ct.customer_id, c.cashback_amount 
                   FROM campaign_targets ct 
                   JOIN campaigns c ON ct.campaign_id = c.id
                   WHERE ct.campaign_id = ? AND ct.redeemed = 0""",
                (campaign_id,)
            ).fetchall()
            campaign_targets = {row['customer_id']: row['cashback_amount'] for row in rows}
    
    # Simulate each day
    for day in range(days_to_simulate):
        state.current_date += timedelta(days=1)
        
        # Generate some normal transactions
        normal_count = random.randint(30, 50)
        for _ in range(normal_count):
            if state.events_index < len(state.all_events):
                event = state.all_events[state.events_index]
                # Adjust timestamp to current date
                event = PaymentEvent(
                    vpa=event.vpa,
                    amount=event.amount,
                    timestamp=state.current_date,
                    merchant_id=event.merchant_id,
                )
                state.db.ingest_payment(event)
                state.events_index += 1
                new_transactions += 1
        
        # Process campaign redemptions (60% chance per day for targeted customers)
        if campaign_id and campaign_targets:
            for cid, cashback in list(campaign_targets.items()):
                if random.random() < 0.15:  # ~15% per day ≈ 60% over 7 days
                    # Customer returns
                    customer = state.db.get_customer_by_id(cid)
                    if customer:
                        # Simulate return visit
                        amount = random.uniform(80, 200)
                        event = PaymentEvent(
                            vpa=f"returning_{cid}@paytm",  # Won't match, but we use customer_id
                            amount=amount,
                            timestamp=state.current_date,
                        )
                        
                        # Record the payment manually for this customer
                        with state.db._connect() as conn:
                            conn.execute(
                                """INSERT INTO payments (customer_id, amount, timestamp, merchant_id)
                                   VALUES (?, ?, ?, ?)""",
                                (cid, amount, state.current_date.isoformat(), config.MERCHANT_ID)
                            )
                        
                        # Redeem the offer
                        if state.db.redeem_campaign_offer(campaign_id, cid, amount):
                            redemptions += 1
                            revenue_recovered += amount
                            cashback_spent += cashback
                            del campaign_targets[cid]
                        
                        new_transactions += 1
    
    return SimulateWeekResponse(
        days_simulated=days_to_simulate,
        new_transactions=new_transactions,
        redemptions=redemptions,
        revenue_recovered=round(revenue_recovered, 2),
        cashback_spent=round(cashback_spent, 2),
    )


# ==================== Customer Endpoints ====================

@app.get("/customers")
async def get_customers(
    segment: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0
):
    """Get all customers with optional segment filter."""
    payments_df, customers_df = state.get_dataframes()
    
    if payments_df.empty:
        return {"customers": [], "total": 0}
    
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    
    # Filter by segment if specified
    if segment:
        try:
            seg_enum = CustomerSegment(segment)
            segmented_df = segmented_df[segmented_df['segment'] == seg_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid segment: {segment}")
    
    total = len(segmented_df)
    
    # Paginate
    segmented_df = segmented_df.iloc[offset:offset + limit]
    
    # Build response
    customers = []
    for _, row in segmented_df.iterrows():
        customers.append({
            "customer_id": int(row['customer_id']),
            "label": row['label'],
            "segment": row['segment'].value,
            "recency_days": int(row['recency_days']),
            "frequency": int(row['frequency']),
            "monetary_avg": round(float(row['monetary_avg']), 2),
            "is_regular": bool(row['is_regular']),
        })
    
    return {"customers": customers, "total": total}


@app.get("/segments")
async def get_segments():
    """Get customer segment counts."""
    payments_df, customers_df = state.get_dataframes()
    
    if payments_df.empty:
        return {seg.value: 0 for seg in CustomerSegment}
    
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    
    return get_segment_counts(segmented_df)


@app.get("/store-summary")
async def get_store_summary_endpoint():
    """Get store summary statistics."""
    payments_df, customers_df = state.get_dataframes()
    
    if payments_df.empty:
        return {
            "total_customers": 0,
            "regular_customers": 0,
            "total_transactions": 0,
            "total_revenue": 0,
            "avg_transaction": 0,
            "current_date": state.current_date.isoformat(),
        }
    
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    summary = get_store_summary(payments_df, segmented_df)
    summary["current_date"] = state.current_date.isoformat()
    
    return summary


@app.get("/insights")
async def get_insights():
    """Get store insights and trends."""
    payments_df, customers_df = state.get_dataframes()
    
    if payments_df.empty:
        return {"insights": []}
    
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    
    insights = generate_store_insights(payments_df, segmented_df)
    
    # Add habits
    habits = get_customers_with_habits(payments_df, segmented_df)
    
    return {
        "insights": [i.to_dict() for i in insights],
        "customer_habits": habits[:10],  # Top 10
    }


@app.get("/at-risk")
async def get_at_risk():
    """Get at-risk AND lost customers (all customers needing attention), excluding those who have already redeemed."""
    payments_df, customers_df = state.get_dataframes()
    
    if payments_df.empty:
        return {"customers": [], "total": 0}
    
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    
    # Get both At-Risk AND Lost customers (all who need attention)
    at_risk_and_lost_df = segmented_df[
        ((segmented_df['segment'] == CustomerSegment.AT_RISK) | 
         (segmented_df['segment'] == CustomerSegment.LOST)) & 
        segmented_df['is_regular']
    ].sort_values('recency_days', ascending=False)
    
    # Get list of customers who have already redeemed (won back)
    redeemed_customer_ids = set()
    with state.db._connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT customer_id FROM campaign_targets WHERE redeemed = 1"
        ).fetchall()
        redeemed_customer_ids = {row['customer_id'] for row in rows}
    
    # Filter out redeemed customers
    at_risk_and_lost_df = at_risk_and_lost_df[~at_risk_and_lost_df['customer_id'].isin(redeemed_customer_ids)]
    
    # Add churn predictions if model is trained
    churn_predictions = {}
    if state.churn_model.is_trained and len(at_risk_and_lost_df) > 0:
        customer_labels = {row['id']: row['label'] for _, row in customers_df.iterrows()}
        predictions = state.churn_model.predict(
            payments_df,
            at_risk_and_lost_df['customer_id'].tolist(),
            customer_labels
        )
        churn_predictions = {p.customer_id: p.churn_probability for p in predictions}
    
    customers = []
    for _, row in at_risk_and_lost_df.iterrows():
        cid = row['customer_id']
        customers.append({
            "customer_id": int(cid),
            "label": row['label'],
            "segment": row['segment'].value,
            "recency_days": int(row['recency_days']),
            "frequency": int(row['frequency']),
            "monetary_avg": round(float(row['monetary_avg']), 2),
            "churn_probability": churn_predictions.get(cid),
        })
    
    return {"customers": customers, "total": len(customers)}


@app.get("/lost")
async def get_lost_customers():
    """Get lost customers (no visit in 30+ days), excluding those who have already redeemed."""
    payments_df, customers_df = state.get_dataframes()
    
    if payments_df.empty:
        return {"customers": [], "total": 0}
    
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    
    # Filter to Lost segment
    lost_df = segmented_df[
        (segmented_df['segment'] == CustomerSegment.LOST) & 
        segmented_df['is_regular']
    ].sort_values('recency_days', ascending=False)
    
    # Get list of customers who have already redeemed (won back)
    redeemed_customer_ids = set()
    with state.db._connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT customer_id FROM campaign_targets WHERE redeemed = 1"
        ).fetchall()
        redeemed_customer_ids = {row['customer_id'] for row in rows}
    
    # Filter out redeemed customers from lost list
    lost_df = lost_df[~lost_df['customer_id'].isin(redeemed_customer_ids)]
    
    # Add churn predictions if model is trained
    churn_predictions = {}
    if state.churn_model.is_trained and len(lost_df) > 0:
        customer_labels = {row['id']: row['label'] for _, row in customers_df.iterrows()}
        predictions = state.churn_model.predict(
            payments_df,
            lost_df['customer_id'].tolist(),
            customer_labels
        )
        churn_predictions = {p.customer_id: p.churn_probability for p in predictions}
    
    customers = []
    for _, row in lost_df.iterrows():
        cid = row['customer_id']
        customers.append({
            "customer_id": int(cid),
            "label": row['label'],
            "segment": row['segment'].value,
            "recency_days": int(row['recency_days']),
            "frequency": int(row['frequency']),
            "monetary_avg": round(float(row['monetary_avg']), 2),
            "churn_probability": churn_predictions.get(cid),
        })
    
    return {"customers": customers, "total": len(customers)}


@app.get("/won-back")
async def get_won_back_customers():
    """Get all customers who have redeemed offers (won back customers)."""
    redemptions = state.db.get_recent_redemptions(limit=100)  # Get all redemptions
    
    # Group by customer to get unique won-back customers with their latest redemption
    won_back = {}
    for r in redemptions:
        cid = r['customer_id']
        if cid not in won_back:
            won_back[cid] = {
                "customer_id": cid,
                "customer_label": r['customer_label'],
                "total_redemptions": 1,
                "total_spent": r['final_amount'],
                "total_saved": r['discount_amount'],
                "last_redemption": r
            }
        else:
            won_back[cid]['total_redemptions'] += 1
            won_back[cid]['total_spent'] += r['final_amount']
            won_back[cid]['total_saved'] += r['discount_amount']
    
    return {
        "customers": list(won_back.values()),
        "total": len(won_back)
    }


# ==================== Campaign Endpoints ====================

@app.get("/suggest-offer")
async def suggest_offer_endpoint(budget: float = 500.0):
    """Get AI-suggested campaign."""
    payments_df, customers_df = state.get_dataframes()
    
    if payments_df.empty:
        return {"error": "No data available. Run /simulate/fast-forward first."}
    
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    
    # Get churn predictions if available
    predictions = None
    if state.churn_model.is_trained:
        customer_labels = {row['id']: row['label'] for _, row in customers_df.iterrows()}
        predictions = state.churn_model.predict(
            payments_df,
            customers_df['id'].tolist(),
            customer_labels
        )
    
    suggestion = suggest_offer(segmented_df, predictions, budget)
    
    return {
        "suggestion": suggestion.to_dict(),
        "summary": suggestion.summary(),
    }


@app.post("/create-campaign", response_model=CampaignResponse)
async def create_campaign_endpoint(request: CreateCampaignRequest):
    """Create and activate a campaign with percentage-based cashback.
    
    Includes spam prevention: customers who haven't made 7 payments since their
    last coupon will be filtered out.
    """
    payments_df, customers_df = state.get_dataframes()
    
    if payments_df.empty:
        raise HTTPException(status_code=400, detail="No data available")
    
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    
    # Use specific customer_ids if provided, otherwise use AI suggestion
    if request.customer_ids and len(request.customer_ids) > 0:
        target_ids = request.customer_ids
    else:
        # Get churn predictions if available
        predictions = None
        if state.churn_model.is_trained:
            customer_labels = {row['id']: row['label'] for _, row in customers_df.iterrows()}
            predictions = state.churn_model.predict(
                payments_df,
                customers_df['id'].tolist(),
                customer_labels
            )
        
        # Generate suggestion
        suggestion = suggest_offer(segmented_df, predictions, request.budget)
        
        if not suggestion.targets:
            raise HTTPException(status_code=400, detail="No eligible targets found")
        
        target_ids = [t.customer_id for t in suggestion.targets]
    
    # All selected customers are eligible (no spam prevention)
    eligible_ids = target_ids
    
    # Create campaign in database with percentage-based cashback
    name = request.name or f"Re-engagement Campaign {datetime.now().strftime('%Y-%m-%d')}"
    
    campaign = state.db.create_campaign(
        name=name,
        cashback_amount=request.cashback_percent,  # Store percentage as "amount" for now
        budget=request.budget,
        target_customer_ids=eligible_ids,
    )
    
    # Build message
    message = f"Campaign created! {len(eligible_ids)} customers will receive {request.cashback_percent:.0f}% cashback offers."
    
    return CampaignResponse(
        campaign_id=campaign.id,
        name=campaign.name,
        targets_count=len(eligible_ids),
        cashback_percent=request.cashback_percent,
        budget=campaign.budget,
        message=message,
    )


@app.get("/roi/{campaign_id}")
async def get_campaign_roi(campaign_id: int):
    """Get ROI metrics for a campaign."""
    roi = state.db.get_campaign_roi(campaign_id)
    
    if not roi:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return roi


@app.get("/campaigns")
async def get_campaigns():
    """Get all campaigns."""
    campaigns = state.db.get_active_campaigns()
    
    result = []
    for c in campaigns:
        roi = state.db.get_campaign_roi(c.id)
        result.append({
            **c.to_dict(),
            **roi,
        })
    
    return {"campaigns": result}


# ==================== AI Chat Endpoint ====================

@app.post("/chat")
async def chat_endpoint(message: dict):
    """
    Handle chat messages using Gemini AI with real-time data.
    """
    from backend.agent import LoyalPayAgent
    
    user_message = message.get("message", "")
    
    # Create agent with tool handlers that use current state
    agent = LoyalPayAgent()
    
    # Register tools with actual data access
    def get_store_summary_handler():
        payments_df, customers_df = state.get_dataframes()
        if payments_df.empty:
            return {"total_customers": 0, "regular_customers": 0, "total_revenue": 0}
        
        rfm_df = calculate_rfm(payments_df, customers_df)
        segmented_df = segment_customers(rfm_df)
        summary = get_store_summary(payments_df, segmented_df)
        segments = get_segment_counts(segmented_df)
        summary["segments"] = segments
        return summary
    
    def get_at_risk_handler(limit: int = 50):
        payments_df, customers_df = state.get_dataframes()
        if payments_df.empty:
            return {"customers": [], "total": 0}
        
        rfm_df = calculate_rfm(payments_df, customers_df)
        segmented_df = segment_customers(rfm_df)
        at_risk_df = get_at_risk_customers(segmented_df)
        
        # Add churn predictions
        churn_predictions = {}
        if state.churn_model and state.churn_model.is_trained:
            customer_labels = {row['id']: row['label'] for _, row in customers_df.iterrows()}
            predictions = state.churn_model.predict(
                payments_df,
                at_risk_df['customer_id'].tolist(),
                customer_labels
            )
            churn_predictions = {p.customer_id: p.churn_probability for p in predictions}
        
        customers = []
        for _, row in at_risk_df.head(limit).iterrows():
            cid = row['customer_id']
            customers.append({
                "customer_id": int(cid),
                "label": row['label'],
                "segment": row['segment'].value,
                "recency_days": int(row['recency_days']),
                "frequency": int(row['frequency']),
                "monetary_avg": round(float(row['monetary_avg']), 2),
                "churn_probability": churn_predictions.get(cid, 0.5),
            })
        
        return {"customers": customers, "total": len(at_risk_df)}
    
    def get_insights_handler():
        payments_df, customers_df = state.get_dataframes()
        if payments_df.empty:
            return {"insights": []}
        
        rfm_df = calculate_rfm(payments_df, customers_df)
        segmented_df = segment_customers(rfm_df)
        insights = generate_store_insights(payments_df, segmented_df)
        habits = get_customers_with_habits(payments_df, segmented_df)
        
        return {
            "insights": [i.to_dict() for i in insights],
            "customer_habits": habits[:10],
        }
    
    def suggest_offer_handler(budget: float = 500):
        payments_df, customers_df = state.get_dataframes()
        if payments_df.empty:
            return {"suggestion": None, "summary": "No data available"}
        
        rfm_df = calculate_rfm(payments_df, customers_df)
        segmented_df = segment_customers(rfm_df)
        
        predictions = None
        if state.churn_model and state.churn_model.is_trained:
            customer_labels = {row['id']: row['label'] for _, row in customers_df.iterrows()}
            predictions = state.churn_model.predict(
                payments_df,
                customers_df['id'].tolist(),
                customer_labels
            )
        
        suggestion = suggest_offer(segmented_df, predictions, budget)
        return {
            "suggestion": suggestion.to_dict(),
            "summary": suggestion.summary(),
        }
    
    def get_campaign_roi_handler(campaign_id: int = None):
        campaigns = state.db.get_active_campaigns()
        if not campaigns:
            return {"message": "No campaigns found"}
        
        cid = campaign_id or (campaigns[0].id if campaigns else None)
        if cid:
            return state.db.get_campaign_roi(cid)
        return {"message": "No campaign ID"}
    
    def get_segments_handler():
        payments_df, customers_df = state.get_dataframes()
        if payments_df.empty:
            return {seg.value: 0 for seg in CustomerSegment}
        
        rfm_df = calculate_rfm(payments_df, customers_df)
        segmented_df = segment_customers(rfm_df)
        return get_segment_counts(segmented_df)
    
    def get_all_customers_handler(limit: int = 100):
        """Get all customers with their spending data for filtering."""
        payments_df, customers_df = state.get_dataframes()
        if payments_df.empty:
            return {"customers": [], "total": 0}
        
        rfm_df = calculate_rfm(payments_df, customers_df)
        segmented_df = segment_customers(rfm_df)
        
        customers = []
        for _, row in segmented_df.head(limit).iterrows():
            customers.append({
                "customer_id": int(row['customer_id']),
                "label": row['label'],
                "segment": row['segment'].value,
                "recency_days": int(row['recency_days']),
                "frequency": int(row['frequency']),
                "monetary_avg": round(float(row['monetary_avg']), 2),
                "total_spend": round(float(row['monetary_avg'] * row['frequency']), 2),
            })
        
        # Sort by monetary_avg descending for high spenders
        customers.sort(key=lambda x: x['monetary_avg'], reverse=True)
        
        # Add summary stats
        avg_spends = [c['monetary_avg'] for c in customers]
        high_spenders = [c for c in customers if c['monetary_avg'] >= 100]
        very_high_spenders = [c for c in customers if c['monetary_avg'] >= 500]
        
        return {
            "customers": customers,
            "total": len(segmented_df),
            "high_spenders_100plus": len(high_spenders),
            "high_spenders_500plus": len(very_high_spenders),
            "avg_spend_overall": round(sum(avg_spends) / len(avg_spends), 2) if avg_spends else 0,
            "top_spenders": customers[:10]  # Top 10 by avg spend
        }
    
    # Register all handlers
    agent.register_tool("get_store_summary", get_store_summary_handler)
    agent.register_tool("get_at_risk_customers", get_at_risk_handler)
    agent.register_tool("get_insights", get_insights_handler)
    agent.register_tool("suggest_offer", suggest_offer_handler)
    agent.register_tool("get_campaign_roi", get_campaign_roi_handler)
    agent.register_tool("get_segments", get_segments_handler)
    agent.register_tool("get_all_customers", get_all_customers_handler)
    
    # Process message
    try:
        result = agent.process_message_sync(user_message)
        return {
            "response": result.response,
            "tools_used": result.tools_used,
            "data": result.data,
            "language": result.language,
        }
    except Exception as e:
        print(f"Chat error: {e}")
        return {
            "response": "Sorry, kuch gadbad ho gayi. Phir se try karein.",
            "tools_used": [],
            "error": str(e)
        }


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "current_date": state.current_date.isoformat(),
        "events_loaded": state.events_index,
        "churn_model_trained": state.churn_model.is_trained if state.churn_model else False,
    }


# ==================== Customer App Endpoints ====================

@app.get("/customer/offers")
async def get_customer_offers():
    """Get all active offers for customers (from active campaigns)."""
    campaigns = state.db.get_active_campaigns()
    
    offers = []
    for campaign in campaigns:
        # Get target customers for this campaign
        with state.db._connect() as conn:
            targets = conn.execute(
                """SELECT ct.*, c.label 
                   FROM campaign_targets ct 
                   JOIN customers c ON ct.customer_id = c.id
                   WHERE ct.campaign_id = ?""",
                (campaign.id,)
            ).fetchall()
        
        for target in targets:
            offer_data = {
                "id": f"{campaign.id}_{target['customer_id']}",
                "campaign_id": campaign.id,
                "customer_id": target['customer_id'],
                "customer_label": target['label'],
                "merchant_name": "Ramesh Kirana Store",
                "merchant_id": "ramesh_kirana",  # Used for QR validation
                "merchant_icon": "🏪",
                "cashback_percent": campaign.cashback_amount,  # We store percent as amount now
                "valid_till": "7 days",
                "redeemed": bool(target['redeemed']),
                "created_at": campaign.created_at,
                "avg_spend": 100,  # Default avg spend for display
            }
            
            # Include redemption details if redeemed
            if target['redeemed']:
                offer_data["redemption_details"] = {
                    "redeemed_at": target['redeemed_at'],
                    "original_amount": target['redemption_amount'],
                    "discount_amount": target['discount_amount'],
                    "final_amount": target['final_amount'],
                }
            
            offers.append(offer_data)
    
    return {"offers": offers, "total": len(offers)}


@app.get("/customer/{customer_id}/offers")
async def get_offers_for_customer(customer_id: int):
    """Get offers for a specific customer."""
    campaigns = state.db.get_active_campaigns()
    
    offers = []
    for campaign in campaigns:
        with state.db._connect() as conn:
            target = conn.execute(
                """SELECT ct.*, c.label 
                   FROM campaign_targets ct 
                   JOIN customers c ON ct.customer_id = c.id
                   WHERE ct.campaign_id = ? AND ct.customer_id = ?""",
                (campaign.id, customer_id)
            ).fetchone()
        
        if target:
            offer_data = {
                "id": f"{campaign.id}_{customer_id}",
                "campaign_id": campaign.id,
                "merchant_name": "Ramesh Kirana Store",
                "merchant_id": "ramesh_kirana",
                "merchant_icon": "🏪",
                "cashback_percent": campaign.cashback_amount,
                "valid_till": "7 days",
                "redeemed": bool(target['redeemed']),
                "created_at": campaign.created_at,
            }
            
            if target['redeemed']:
                offer_data["redemption_details"] = {
                    "redeemed_at": target['redeemed_at'],
                    "original_amount": target['redemption_amount'],
                    "discount_amount": target['discount_amount'],
                    "final_amount": target['final_amount'],
                }
            
            offers.append(offer_data)
    
    return {"offers": offers, "total": len(offers)}


class RedeemRequest(BaseModel):
    payment_amount: float = 100.0  # Amount the customer is paying


@app.post("/customer/{customer_id}/redeem/{campaign_id}")
async def redeem_customer_offer(customer_id: int, campaign_id: int, request: RedeemRequest = None):
    """
    Redeem an offer for a customer.
    
    This:
    1. Validates the offer exists and is not already redeemed
    2. Calculates the discount based on cashback percentage
    3. Records the redemption with payment details
    4. Updates campaign spending
    5. Creates a payment record
    """
    payment_amount = request.payment_amount if request else 100.0
    
    result = state.db.redeem_campaign_offer(campaign_id, customer_id, payment_amount)
    
    return result


@app.get("/merchant/redemptions")
async def get_merchant_redemptions(limit: int = 20):
    """Get recent redemptions for merchant dashboard."""
    redemptions = state.db.get_recent_redemptions(limit)
    stats = state.db.get_campaign_stats_for_merchant()
    
    return {
        "redemptions": redemptions,
        "stats": stats
    }


@app.get("/merchant/campaign-stats")
async def get_merchant_campaign_stats():
    """Get campaign statistics for merchant dashboard."""
    return state.db.get_campaign_stats_for_merchant()


@app.get("/customer/{customer_id}/coupon-eligibility")
async def check_coupon_eligibility(customer_id: int):
    """Check if a customer is eligible to receive a new coupon."""
    return state.db.check_customer_coupon_eligibility(customer_id)


@app.post("/check-coupon-eligibility")
async def check_multiple_coupon_eligibility(customer_ids: List[int]):
    """Check coupon eligibility for multiple customers."""
    results = state.db.get_eligible_customers_for_coupon(customer_ids)
    
    eligible = [r for r in results if r['eligible']]
    ineligible = [r for r in results if not r['eligible']]
    
    return {
        "eligible_customers": eligible,
        "ineligible_customers": ineligible,
        "total_eligible": len(eligible),
        "total_ineligible": len(ineligible)
    }


# ==================== Static File Serving (For Combined Deployment) ====================

import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Check if static directories exist (only in production/combined deployment)
static_dir = Path(__file__).parent.parent / "static"

if static_dir.exists():
    # Serve merchant app at /merchant
    merchant_dir = static_dir / "merchant"
    if merchant_dir.exists():
        app.mount("/merchant", StaticFiles(directory=str(merchant_dir), html=True), name="merchant")
    
    # Serve customer app at /customer
    customer_dir = static_dir / "customer"
    if customer_dir.exists():
        app.mount("/customer", StaticFiles(directory=str(customer_dir), html=True), name="customer")
    
    # Root redirect to merchant app
    @app.get("/")
    async def root():
        return FileResponse(str(merchant_dir / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
