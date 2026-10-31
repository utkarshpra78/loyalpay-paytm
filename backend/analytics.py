"""
LoyalPay Analytics Module

Provides:
- RFM (Recency, Frequency, Monetary) scoring
- Customer segmentation (Champion, Loyal, New, At-Risk, Lost)
- Habit detection (day/hour patterns)
- Store-level insights

All functions are pure - they take data and return results without side effects.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from backend.config import config


class CustomerSegment(Enum):
    """Customer segments based on RFM analysis."""
    CHAMPION = "Champion"      # High frequency, very recent
    LOYAL = "Loyal"            # Regular visits, recent
    NEW = "New"                # First visit within last 14 days
    AT_RISK = "At-Risk"        # Previously regular, 14-30 days inactive
    LOST = "Lost"              # 30+ days inactive
    CASUAL = "Casual"          # Irregular, but still visiting
    ONE_TIME = "One-Time"      # Only 1 visit (not a regular)


@dataclass
class RFMScore:
    """RFM scores for a customer."""
    customer_id: int
    label: str
    recency_days: int         # Days since last visit
    frequency: int            # Total visit count
    monetary_avg: float       # Average transaction value
    monetary_total: float     # Total spent
    first_visit: datetime
    last_visit: datetime
    
    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "label": self.label,
            "recency_days": self.recency_days,
            "frequency": self.frequency,
            "monetary_avg": round(self.monetary_avg, 2),
            "monetary_total": round(self.monetary_total, 2),
            "first_visit": self.first_visit.isoformat() if self.first_visit else None,
            "last_visit": self.last_visit.isoformat() if self.last_visit else None,
        }


@dataclass
class CustomerProfile:
    """Complete customer profile with RFM, segment, and habits."""
    customer_id: int
    label: str
    opt_in: bool
    
    # RFM metrics
    recency_days: int
    frequency: int
    monetary_avg: float
    monetary_total: float
    first_visit: datetime
    last_visit: datetime
    
    # Segmentation
    segment: CustomerSegment
    is_regular: bool  # 2+ visits
    
    # Habits (if detected)
    habit_day: Optional[str] = None      # e.g., "Sunday"
    habit_hour: Optional[int] = None     # e.g., 8
    habit_description: Optional[str] = None  # e.g., "Visits Sunday at 8 AM"
    
    # Churn risk (populated by churn model)
    churn_probability: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "label": self.label,
            "opt_in": self.opt_in,
            "recency_days": self.recency_days,
            "frequency": self.frequency,
            "monetary_avg": round(self.monetary_avg, 2),
            "monetary_total": round(self.monetary_total, 2),
            "first_visit": self.first_visit.isoformat() if self.first_visit else None,
            "last_visit": self.last_visit.isoformat() if self.last_visit else None,
            "segment": self.segment.value,
            "is_regular": self.is_regular,
            "habit_day": self.habit_day,
            "habit_hour": self.habit_hour,
            "habit_description": self.habit_description,
            "churn_probability": self.churn_probability,
        }


@dataclass
class StoreInsight:
    """A store-level insight or trend."""
    insight_type: str  # "habit", "trend", "alert"
    title: str
    description: str
    value: Optional[float] = None
    change_percent: Optional[float] = None
    customers_affected: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "insight_type": self.insight_type,
            "title": self.title,
            "description": self.description,
            "value": self.value,
            "change_percent": self.change_percent,
            "customers_affected": self.customers_affected,
        }


# ==================== RFM Scoring ====================

def calculate_rfm(
    payments_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    reference_date: datetime = None
) -> pd.DataFrame:
    """
    Calculate RFM scores for all customers.
    
    Args:
        payments_df: DataFrame with columns [customer_id, amount, timestamp]
        customers_df: DataFrame with columns [id, label, opt_in]
        reference_date: Date to calculate recency from (default: max payment date)
        
    Returns:
        DataFrame with RFM scores per customer
    """
    if payments_df.empty:
        return pd.DataFrame()
    
    # Ensure timestamp is datetime
    payments_df = payments_df.copy()
    if payments_df['timestamp'].dtype == 'object':
        payments_df['timestamp'] = pd.to_datetime(payments_df['timestamp'], format='ISO8601')
    
    # Reference date for recency calculation
    if reference_date is None:
        reference_date = payments_df['timestamp'].max()
    
    # Calculate RFM metrics per customer
    rfm = payments_df.groupby('customer_id').agg({
        'timestamp': ['max', 'min', 'count'],
        'amount': ['mean', 'sum']
    }).reset_index()
    
    # Flatten column names
    rfm.columns = ['customer_id', 'last_visit', 'first_visit', 'frequency', 
                   'monetary_avg', 'monetary_total']
    
    # Calculate recency in days
    rfm['recency_days'] = (reference_date - rfm['last_visit']).dt.days
    
    # Merge with customer info
    rfm = rfm.merge(
        customers_df[['id', 'label', 'opt_in']].rename(columns={'id': 'customer_id'}),
        on='customer_id',
        how='left'
    )
    
    return rfm


def get_rfm_scores(
    payments_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    reference_date: datetime = None
) -> List[RFMScore]:
    """
    Get RFM scores as a list of RFMScore objects.
    
    Args:
        payments_df: DataFrame with payment data
        customers_df: DataFrame with customer data
        reference_date: Reference date for recency
        
    Returns:
        List of RFMScore objects
    """
    rfm_df = calculate_rfm(payments_df, customers_df, reference_date)
    
    if rfm_df.empty:
        return []
    
    return [
        RFMScore(
            customer_id=row['customer_id'],
            label=row['label'],
            recency_days=int(row['recency_days']),
            frequency=int(row['frequency']),
            monetary_avg=float(row['monetary_avg']),
            monetary_total=float(row['monetary_total']),
            first_visit=row['first_visit'],
            last_visit=row['last_visit'],
        )
        for _, row in rfm_df.iterrows()
    ]


# ==================== Customer Segmentation ====================

def segment_customer(
    recency_days: int,
    frequency: int,
    first_visit: datetime,
    reference_date: datetime
) -> CustomerSegment:
    """
    Determine customer segment based on RFM metrics.
    
    Segmentation rules:
    - Champion: 15+ visits AND active within 3 days
    - Loyal: Regular visits AND active within 7 days
    - New: First visit within last 14 days
    - At-Risk: Previously regular (5+ visits), 14-30 days inactive
    - Lost: 30+ days inactive
    - Casual: Everyone else who visits occasionally
    - One-Time: Only 1 visit
    
    Args:
        recency_days: Days since last visit
        frequency: Total visit count
        first_visit: Date of first visit
        reference_date: Reference date for calculations
        
    Returns:
        CustomerSegment enum value
    """
    # One-time visitors (not regulars)
    if frequency < config.MIN_VISITS_FOR_REGULAR:
        return CustomerSegment.ONE_TIME
    
    # Check if customer is new (first visit within 14 days)
    days_since_first = (reference_date - first_visit).days if first_visit else 999
    if days_since_first <= config.NEW_MAX_AGE_DAYS:
        return CustomerSegment.NEW
    
    # Lost: 30+ days inactive
    if recency_days >= config.LOST_MIN_RECENCY_DAYS:
        return CustomerSegment.LOST
    
    # At-Risk: 14-30 days inactive (previously was regular)
    if recency_days >= config.AT_RISK_MIN_RECENCY_DAYS:
        return CustomerSegment.AT_RISK
    
    # Champion: 15+ visits AND active within 3 days
    if frequency >= config.CHAMPION_MIN_VISITS and recency_days <= config.CHAMPION_MAX_RECENCY_DAYS:
        return CustomerSegment.CHAMPION
    
    # Loyal: Regular visits AND active within 7 days
    if frequency >= 5 and recency_days <= config.LOYAL_MAX_RECENCY_DAYS:
        return CustomerSegment.LOYAL
    
    # Everyone else is Casual
    return CustomerSegment.CASUAL


def segment_customers(
    rfm_df: pd.DataFrame,
    reference_date: datetime = None
) -> pd.DataFrame:
    """
    Segment all customers based on RFM scores.
    
    Args:
        rfm_df: DataFrame from calculate_rfm()
        reference_date: Reference date for segmentation
        
    Returns:
        DataFrame with segment column added
    """
    if rfm_df.empty:
        return rfm_df
    
    if reference_date is None:
        reference_date = rfm_df['last_visit'].max()
    
    def get_segment(row):
        return segment_customer(
            recency_days=int(row['recency_days']),
            frequency=int(row['frequency']),
            first_visit=row['first_visit'],
            reference_date=reference_date
        )
    
    rfm_df = rfm_df.copy()
    rfm_df['segment'] = rfm_df.apply(get_segment, axis=1)
    rfm_df['is_regular'] = rfm_df['frequency'] >= config.MIN_VISITS_FOR_REGULAR
    
    return rfm_df


def get_segment_counts(segmented_df: pd.DataFrame) -> Dict[str, int]:
    """
    Get count of customers in each segment.
    
    Args:
        segmented_df: DataFrame with segment column
        
    Returns:
        Dict mapping segment name to count
    """
    if segmented_df.empty:
        return {seg.value: 0 for seg in CustomerSegment}
    
    counts = segmented_df['segment'].value_counts()
    
    result = {}
    for seg in CustomerSegment:
        result[seg.value] = int(counts.get(seg, 0))
    
    return result


def get_regular_count(segmented_df: pd.DataFrame) -> int:
    """Get count of regular customers (2+ visits)."""
    if segmented_df.empty:
        return 0
    return int(segmented_df['is_regular'].sum())


def get_at_risk_customers(segmented_df: pd.DataFrame) -> pd.DataFrame:
    """Get customers in At-Risk segment who are regulars (excludes Lost)."""
    if segmented_df.empty:
        return pd.DataFrame()
    
    # Only At-Risk, not Lost (Lost has its own section)
    mask = (
        (segmented_df['segment'] == CustomerSegment.AT_RISK) & 
        segmented_df['is_regular']
    )
    
    return segmented_df[mask].sort_values('recency_days', ascending=False)


# ==================== Habit Detection ====================

def detect_habits(
    payments_df: pd.DataFrame,
    customer_id: int,
    day_threshold: float = None,
    hour_threshold: float = None
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Detect visit habits for a customer.
    
    A habit is detected if:
    - ≥60% of visits occur on the same day of week
    - ≥60% of visits occur within the same hour
    
    Args:
        payments_df: DataFrame with all payments
        customer_id: Customer to analyze
        day_threshold: Threshold for day habit (default: 0.60)
        hour_threshold: Threshold for hour habit (default: 0.60)
        
    Returns:
        Tuple of (habit_day, habit_hour, description)
    """
    day_threshold = day_threshold or config.HABIT_DAY_THRESHOLD
    hour_threshold = hour_threshold or config.HABIT_HOUR_THRESHOLD
    
    # Filter to customer's payments
    customer_payments = payments_df[payments_df['customer_id'] == customer_id].copy()
    
    if len(customer_payments) < 3:
        # Need at least 3 visits to detect a pattern
        return None, None, None
    
    # Ensure timestamp is datetime
    if customer_payments['timestamp'].dtype == 'object':
        customer_payments['timestamp'] = pd.to_datetime(customer_payments['timestamp'], format='ISO8601')
    
    # Extract day and hour
    customer_payments['day_of_week'] = customer_payments['timestamp'].dt.dayofweek
    customer_payments['hour'] = customer_payments['timestamp'].dt.hour
    
    total_visits = len(customer_payments)
    
    # Detect day habit
    day_counts = customer_payments['day_of_week'].value_counts()
    top_day = day_counts.idxmax()
    day_ratio = day_counts.iloc[0] / total_visits
    
    habit_day = None
    if day_ratio >= day_threshold:
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        habit_day = day_names[top_day]
    
    # Detect hour habit
    hour_counts = customer_payments['hour'].value_counts()
    top_hour = hour_counts.idxmax()
    hour_ratio = hour_counts.iloc[0] / total_visits
    
    habit_hour = None
    if hour_ratio >= hour_threshold:
        habit_hour = int(top_hour)
    
    # Generate description
    description = None
    if habit_day and habit_hour:
        hour_str = f"{habit_hour}:00" if habit_hour < 12 else f"{habit_hour-12}:00 PM" if habit_hour > 12 else "12:00 PM"
        if habit_hour < 12:
            hour_str = f"{habit_hour} AM" if habit_hour > 0 else "12 AM"
        description = f"Visits {habit_day} at {habit_hour} AM" if habit_hour < 12 else f"Visits {habit_day} at {habit_hour-12 if habit_hour > 12 else 12} PM"
    elif habit_day:
        description = f"Visits on {habit_day}s"
    elif habit_hour:
        if habit_hour < 12:
            description = f"Visits around {habit_hour} AM"
        else:
            description = f"Visits around {habit_hour-12 if habit_hour > 12 else 12} PM"
    
    return habit_day, habit_hour, description


def detect_all_habits(
    payments_df: pd.DataFrame,
    customer_ids: List[int] = None
) -> Dict[int, Tuple[Optional[str], Optional[int], Optional[str]]]:
    """
    Detect habits for multiple customers.
    
    Args:
        payments_df: DataFrame with all payments
        customer_ids: List of customer IDs to analyze (default: all)
        
    Returns:
        Dict mapping customer_id to (habit_day, habit_hour, description)
    """
    if customer_ids is None:
        customer_ids = payments_df['customer_id'].unique()
    
    habits = {}
    for cid in customer_ids:
        habits[cid] = detect_habits(payments_df, cid)
    
    return habits


def get_customers_with_habits(
    payments_df: pd.DataFrame,
    segmented_df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    Get list of customers with detected habits.
    
    Args:
        payments_df: DataFrame with all payments
        segmented_df: DataFrame with segmentation
        
    Returns:
        List of customer dicts with habit info
    """
    results = []
    
    for _, row in segmented_df.iterrows():
        if row['frequency'] >= 3:  # Need 3+ visits for habits
            habit_day, habit_hour, description = detect_habits(
                payments_df, row['customer_id']
            )
            
            if description:
                results.append({
                    "customer_id": row['customer_id'],
                    "label": row['label'],
                    "frequency": int(row['frequency']),
                    "habit_day": habit_day,
                    "habit_hour": habit_hour,
                    "habit_description": description,
                })
    
    return results


# ==================== Store Insights ====================

def generate_store_insights(
    payments_df: pd.DataFrame,
    segmented_df: pd.DataFrame,
    reference_date: datetime = None
) -> List[StoreInsight]:
    """
    Generate store-level insights and trends.
    
    Args:
        payments_df: DataFrame with all payments
        segmented_df: DataFrame with segmentation
        reference_date: Reference date for analysis
        
    Returns:
        List of StoreInsight objects
    """
    insights = []
    
    if payments_df.empty or segmented_df.empty:
        return insights
    
    if reference_date is None:
        reference_date = payments_df['timestamp'].max()
    
    # Ensure timestamp is datetime
    if payments_df['timestamp'].dtype == 'object':
        payments_df = payments_df.copy()
        payments_df['timestamp'] = pd.to_datetime(payments_df['timestamp'], format='ISO8601')
    
    # 1. Regular customer count
    regular_count = get_regular_count(segmented_df)
    insights.append(StoreInsight(
        insight_type="summary",
        title="Regular Customers",
        description=f"You have {regular_count} regular customers (2+ visits)",
        value=regular_count,
    ))
    
    # 2. At-risk alert
    at_risk_df = get_at_risk_customers(segmented_df)
    at_risk_count = len(at_risk_df)
    if at_risk_count > 0:
        insights.append(StoreInsight(
            insight_type="alert",
            title="At-Risk Customers",
            description=f"{at_risk_count} regular customers haven't visited in 2+ weeks",
            value=at_risk_count,
            customers_affected=at_risk_count,
        ))
    
    # 3. Weekend vs weekday analysis
    payments_df['day_of_week'] = payments_df['timestamp'].dt.dayofweek
    weekend_mask = payments_df['day_of_week'].isin([5, 6])
    
    weekend_revenue = payments_df[weekend_mask]['amount'].sum()
    weekday_revenue = payments_df[~weekend_mask]['amount'].sum()
    total_revenue = weekend_revenue + weekday_revenue
    
    if total_revenue > 0:
        weekend_pct = (weekend_revenue / total_revenue) * 100
        insights.append(StoreInsight(
            insight_type="trend",
            title="Weekend Revenue",
            description=f"Weekend sales account for {weekend_pct:.0f}% of total revenue",
            value=weekend_revenue,
            change_percent=weekend_pct,
        ))
    
    # 4. Peak hours
    payments_df['hour'] = payments_df['timestamp'].dt.hour
    hourly_revenue = payments_df.groupby('hour')['amount'].sum()
    peak_hour = hourly_revenue.idxmax()
    
    if peak_hour < 12:
        peak_str = f"{peak_hour} AM"
    elif peak_hour == 12:
        peak_str = "12 PM"
    else:
        peak_str = f"{peak_hour - 12} PM"
    
    insights.append(StoreInsight(
        insight_type="trend",
        title="Peak Hour",
        description=f"Most revenue comes at {peak_str}",
        value=float(hourly_revenue[peak_hour]),
    ))
    
    # 5. Champion customers
    segment_counts = get_segment_counts(segmented_df)
    champion_count = segment_counts.get("Champion", 0)
    if champion_count > 0:
        insights.append(StoreInsight(
            insight_type="summary",
            title="Champion Customers",
            description=f"{champion_count} champion customers (15+ visits, very active)",
            value=champion_count,
        ))
    
    # 6. Customers with habits
    habits = get_customers_with_habits(payments_df, segmented_df)
    if habits:
        # Find most common habit day
        day_counts = {}
        for h in habits:
            if h['habit_day']:
                day_counts[h['habit_day']] = day_counts.get(h['habit_day'], 0) + 1
        
        if day_counts:
            top_day = max(day_counts, key=day_counts.get)
            insights.append(StoreInsight(
                insight_type="habit",
                title=f"{top_day} Regulars",
                description=f"{day_counts[top_day]} customers prefer visiting on {top_day}s",
                value=day_counts[top_day],
                customers_affected=day_counts[top_day],
            ))
    
    return insights


# ==================== Customer Profiles ====================

def build_customer_profiles(
    payments_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    reference_date: datetime = None
) -> List[CustomerProfile]:
    """
    Build complete profiles for all customers.
    
    Combines RFM scoring, segmentation, and habit detection.
    
    Args:
        payments_df: DataFrame with payment data
        customers_df: DataFrame with customer data
        reference_date: Reference date for analysis
        
    Returns:
        List of CustomerProfile objects
    """
    if payments_df.empty or customers_df.empty:
        return []
    
    # Calculate RFM
    rfm_df = calculate_rfm(payments_df, customers_df, reference_date)
    
    if rfm_df.empty:
        return []
    
    if reference_date is None:
        reference_date = rfm_df['last_visit'].max()
    
    # Segment customers
    rfm_df = segment_customers(rfm_df, reference_date)
    
    # Detect habits for all
    habits = detect_all_habits(payments_df, rfm_df['customer_id'].tolist())
    
    # Build profiles
    profiles = []
    for _, row in rfm_df.iterrows():
        cid = row['customer_id']
        habit_day, habit_hour, habit_desc = habits.get(cid, (None, None, None))
        
        profiles.append(CustomerProfile(
            customer_id=cid,
            label=row['label'],
            opt_in=bool(row.get('opt_in', True)),
            recency_days=int(row['recency_days']),
            frequency=int(row['frequency']),
            monetary_avg=float(row['monetary_avg']),
            monetary_total=float(row['monetary_total']),
            first_visit=row['first_visit'],
            last_visit=row['last_visit'],
            segment=row['segment'],
            is_regular=bool(row['is_regular']),
            habit_day=habit_day,
            habit_hour=habit_hour,
            habit_description=habit_desc,
        ))
    
    return profiles


# ==================== Summary Statistics ====================

def get_store_summary(
    payments_df: pd.DataFrame,
    segmented_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Get summary statistics for the store.
    
    Args:
        payments_df: DataFrame with payment data
        segmented_df: DataFrame with segmentation
        
    Returns:
        Dict with summary statistics
    """
    if payments_df.empty:
        return {
            "total_customers": 0,
            "regular_customers": 0,
            "total_transactions": 0,
            "total_revenue": 0,
            "avg_transaction": 0,
            "segment_counts": {seg.value: 0 for seg in CustomerSegment},
        }
    
    return {
        "total_customers": len(segmented_df) if not segmented_df.empty else 0,
        "regular_customers": get_regular_count(segmented_df),
        "total_transactions": len(payments_df),
        "total_revenue": float(payments_df['amount'].sum()),
        "avg_transaction": float(payments_df['amount'].mean()),
        "segment_counts": get_segment_counts(segmented_df),
    }


if __name__ == "__main__":
    # Quick verification
    from backend.generator import create_demo_generator
    from backend.database import Database
    
    print("Testing Analytics Module...")
    print("=" * 60)
    
    # Generate and ingest data
    generator = create_demo_generator(seed=42)
    events = generator.generate_all_events()
    
    db = Database()
    db.drop_all()
    
    print(f"Ingesting {len(events)} events...")
    db.ingest_payments_batch(events)
    
    # Get data as DataFrames
    with db._connect() as conn:
        payments_df = pd.read_sql("SELECT * FROM payments", conn)
        customers_df = pd.read_sql("SELECT * FROM customers", conn)
    
    # Calculate RFM and segment
    print("\nCalculating RFM scores...")
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    
    # Print segment counts
    segment_counts = get_segment_counts(segmented_df)
    print("\nSegment Counts:")
    for seg, count in segment_counts.items():
        print(f"  {seg}: {count}")
    
    print(f"\nRegular Customers (2+ visits): {get_regular_count(segmented_df)}")
    
    # At-risk customers
    at_risk = get_at_risk_customers(segmented_df)
    print(f"At-Risk + Lost Regulars: {len(at_risk)}")
    
    # Habits
    print("\nCustomers with Habits (first 5):")
    habits = get_customers_with_habits(payments_df, segmented_df)
    for h in habits[:5]:
        print(f"  {h['label']}: {h['habit_description']}")
    
    # Store insights
    print("\nStore Insights:")
    insights = generate_store_insights(payments_df, segmented_df)
    for insight in insights:
        print(f"  [{insight.insight_type}] {insight.title}: {insight.description}")
    
    print("\n" + "=" * 60)
    print("Analytics module tests passed! ✓")
