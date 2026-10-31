"""
LoyalPay Offer Optimizer

Selects optimal customers for re-engagement campaigns and projects ROI.

Algorithm:
1. Rank customers by: churn_probability × avg_spend (expected value at risk)
2. Greedy budget fill: Add customers until budget exhausted
3. Cashback = ~15% of average basket size
4. Project ROI based on expected redemption rate

Deterministic: Given same inputs, produces same outputs.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from backend.config import config
from backend.analytics import CustomerProfile, CustomerSegment, get_at_risk_customers
from backend.churn_model import ChurnPrediction


@dataclass
class CampaignTarget:
    """A customer targeted for a campaign."""
    customer_id: int
    label: str
    churn_probability: float
    avg_spend: float
    expected_value: float  # churn_prob × avg_spend
    cashback_amount: float
    
    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "label": self.label,
            "churn_probability": round(self.churn_probability, 3),
            "avg_spend": round(self.avg_spend, 2),
            "expected_value": round(self.expected_value, 2),
            "cashback_amount": round(self.cashback_amount, 2),
        }


@dataclass
class CampaignSuggestion:
    """A suggested campaign with projected ROI."""
    name: str
    targets: List[CampaignTarget]
    cashback_per_customer: float
    total_budget: float
    expected_redemptions: int
    expected_revenue: float
    expected_roi: float
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "target_count": len(self.targets),
            "targets": [t.to_dict() for t in self.targets],
            "cashback_per_customer": round(self.cashback_per_customer, 2),
            "total_budget": round(self.total_budget, 2),
            "expected_redemptions": self.expected_redemptions,
            "expected_revenue": round(self.expected_revenue, 2),
            "expected_roi": round(self.expected_roi, 1),
        }
    
    def summary(self) -> str:
        """Get a human-readable summary."""
        return (
            f"Send ₹{self.cashback_per_customer:.0f} cashback to {len(self.targets)} "
            f"at-risk regulars. Budget: ₹{self.total_budget:.0f}. "
            f"Expected Return: ₹{self.expected_revenue:.0f}."
        )


class OfferOptimizer:
    """
    Optimizes campaign targeting and ROI projection.
    
    Pure function approach - all methods are stateless.
    """
    
    def __init__(
        self,
        cashback_percent: float = None,
        default_budget: float = None,
        redemption_rate: float = None
    ):
        self.cashback_percent = cashback_percent or config.DEFAULT_CASHBACK_PERCENT
        self.default_budget = default_budget or config.DEFAULT_CAMPAIGN_BUDGET
        self.redemption_rate = redemption_rate or config.EXPECTED_REDEMPTION_RATE
    
    def calculate_cashback(self, avg_spend: float) -> float:
        """
        Calculate cashback amount based on average spend.
        
        Cashback = ~15% of basket size, rounded to nearest ₹5
        """
        raw = avg_spend * self.cashback_percent
        # Round to nearest 5, minimum ₹10
        rounded = max(10, round(raw / 5) * 5)
        return float(rounded)
    
    def rank_customers(
        self,
        segmented_df: pd.DataFrame,
        churn_predictions: List[ChurnPrediction] = None
    ) -> List[CampaignTarget]:
        """
        Rank customers by expected value at risk.
        
        Score = churn_probability × avg_spend
        
        Higher score = higher priority for re-engagement.
        
        Args:
            segmented_df: DataFrame with RFM and segment data
            churn_predictions: Optional churn predictions (uses recency heuristic if None)
            
        Returns:
            List of CampaignTarget sorted by expected value (descending)
        """
        # Filter to at-risk/lost regulars who are opted in
        at_risk = get_at_risk_customers(segmented_df)
        
        if at_risk.empty:
            return []
        
        # Filter to opted-in customers
        if 'opt_in' in at_risk.columns:
            at_risk = at_risk[at_risk['opt_in'] == 1]
        
        if at_risk.empty:
            return []
        
        # Build churn probability lookup
        churn_lookup = {}
        if churn_predictions:
            churn_lookup = {p.customer_id: p.churn_probability for p in churn_predictions}
        
        targets = []
        for _, row in at_risk.iterrows():
            cid = row['customer_id']
            
            # Get churn probability (use prediction or recency heuristic)
            if cid in churn_lookup:
                churn_prob = churn_lookup[cid]
            else:
                # Heuristic: probability increases with recency
                # 14 days → 0.4, 30 days → 0.9
                recency = min(row['recency_days'], 45)
                churn_prob = 0.3 + (recency - 14) * 0.03
                churn_prob = min(0.95, max(0.3, churn_prob))
            
            avg_spend = row['monetary_avg']
            expected_value = churn_prob * avg_spend
            cashback = self.calculate_cashback(avg_spend)
            
            targets.append(CampaignTarget(
                customer_id=cid,
                label=row['label'],
                churn_probability=churn_prob,
                avg_spend=avg_spend,
                expected_value=expected_value,
                cashback_amount=cashback,
            ))
        
        # Sort by expected value (highest first)
        return sorted(targets, key=lambda x: x.expected_value, reverse=True)
    
    def select_targets(
        self,
        ranked_targets: List[CampaignTarget],
        budget: float = None,
        max_targets: int = None
    ) -> Tuple[List[CampaignTarget], float]:
        """
        Select targets using greedy budget fill.
        
        Args:
            ranked_targets: Pre-ranked list of potential targets
            budget: Maximum budget (default: 500)
            max_targets: Maximum number of targets (optional)
            
        Returns:
            Tuple of (selected_targets, total_cost)
        """
        budget = budget or self.default_budget
        
        selected = []
        total_cost = 0.0
        
        for target in ranked_targets:
            if max_targets and len(selected) >= max_targets:
                break
            
            if total_cost + target.cashback_amount <= budget:
                selected.append(target)
                total_cost += target.cashback_amount
        
        return selected, total_cost
    
    def project_roi(
        self,
        targets: List[CampaignTarget],
        total_cost: float,
        visits_per_return: float = 1.5
    ) -> Dict[str, Any]:
        """
        Project ROI for a campaign.
        
        Args:
            targets: Selected targets
            total_cost: Total cashback budget used
            visits_per_return: Expected visits per returned customer
            
        Returns:
            Dict with ROI projections
        """
        if not targets:
            return {
                "expected_redemptions": 0,
                "expected_cashback_spent": 0,
                "expected_revenue": 0,
                "expected_roi": 0,
            }
        
        # Expected redemptions = targets × redemption_rate
        expected_redemptions = int(len(targets) * self.redemption_rate)
        
        # Expected cashback actually spent (only paid on redemption)
        expected_cashback_spent = sum(
            t.cashback_amount for t in targets[:expected_redemptions]
        )
        
        # Expected revenue = returned customers × avg spend × visits
        avg_spend = np.mean([t.avg_spend for t in targets])
        expected_revenue = expected_redemptions * avg_spend * visits_per_return
        
        # ROI = revenue / cashback spent
        expected_roi = expected_revenue / expected_cashback_spent if expected_cashback_spent > 0 else 0
        
        return {
            "expected_redemptions": expected_redemptions,
            "expected_cashback_spent": round(expected_cashback_spent, 2),
            "expected_revenue": round(expected_revenue, 2),
            "expected_roi": round(expected_roi, 1),
        }
    
    def suggest_campaign(
        self,
        segmented_df: pd.DataFrame,
        churn_predictions: List[ChurnPrediction] = None,
        budget: float = None,
        name: str = None
    ) -> CampaignSuggestion:
        """
        Generate a complete campaign suggestion.
        
        Args:
            segmented_df: DataFrame with customer data
            churn_predictions: Optional churn predictions
            budget: Campaign budget (default: 500)
            name: Campaign name
            
        Returns:
            CampaignSuggestion with targets and projections
        """
        budget = budget or self.default_budget
        name = name or f"Re-engagement Campaign"
        
        # Rank and select targets
        ranked = self.rank_customers(segmented_df, churn_predictions)
        targets, total_cost = self.select_targets(ranked, budget)
        
        if not targets:
            return CampaignSuggestion(
                name=name,
                targets=[],
                cashback_per_customer=0,
                total_budget=budget,
                expected_redemptions=0,
                expected_revenue=0,
                expected_roi=0,
            )
        
        # Calculate uniform cashback (use median for consistency)
        cashbacks = [t.cashback_amount for t in targets]
        cashback_per_customer = float(np.median(cashbacks))
        
        # Project ROI
        roi = self.project_roi(targets, total_cost)
        
        return CampaignSuggestion(
            name=name,
            targets=targets,
            cashback_per_customer=cashback_per_customer,
            total_budget=budget,
            expected_redemptions=roi['expected_redemptions'],
            expected_revenue=roi['expected_revenue'],
            expected_roi=roi['expected_roi'],
        )


def suggest_offer(
    segmented_df: pd.DataFrame,
    churn_predictions: List[ChurnPrediction] = None,
    budget: float = 500.0
) -> CampaignSuggestion:
    """
    Convenience function to generate a campaign suggestion.
    
    Args:
        segmented_df: DataFrame with customer data
        churn_predictions: Optional churn predictions
        budget: Campaign budget
        
    Returns:
        CampaignSuggestion
    """
    optimizer = OfferOptimizer()
    return optimizer.suggest_campaign(segmented_df, churn_predictions, budget)


if __name__ == "__main__":
    # Quick verification
    from backend.generator import create_demo_generator
    from backend.database import Database
    from backend.analytics import calculate_rfm, segment_customers
    from backend.churn_model import ChurnModel
    
    print("Testing Offer Optimizer...")
    print("=" * 60)
    
    # Generate and ingest data
    generator = create_demo_generator(seed=42)
    events = generator.generate_all_events()
    
    db = Database()
    db.drop_all()
    db.ingest_payments_batch(events)
    
    # Get data
    with db._connect() as conn:
        payments_df = pd.read_sql("SELECT * FROM payments", conn)
        customers_df = pd.read_sql("SELECT * FROM customers", conn)
    
    # Calculate segments
    rfm_df = calculate_rfm(payments_df, customers_df)
    segmented_df = segment_customers(rfm_df)
    
    # Train churn model
    print("\nTraining churn model for predictions...")
    model = ChurnModel()
    model.train(payments_df, customers_df)
    
    # Get predictions
    customer_labels = {row['id']: row['label'] for _, row in customers_df.iterrows()}
    predictions = model.predict(
        payments_df,
        customers_df['id'].tolist(),
        customer_labels
    )
    
    # Generate campaign suggestion
    print("\nGenerating campaign suggestion...")
    optimizer = OfferOptimizer()
    suggestion = optimizer.suggest_campaign(
        segmented_df,
        predictions,
        budget=500.0
    )
    
    print(f"\nCampaign: {suggestion.name}")
    print(f"  Targets: {len(suggestion.targets)}")
    print(f"  Cashback per customer: ₹{suggestion.cashback_per_customer:.0f}")
    print(f"  Total budget: ₹{suggestion.total_budget:.0f}")
    print(f"  Expected redemptions: {suggestion.expected_redemptions}")
    print(f"  Expected revenue: ₹{suggestion.expected_revenue:.0f}")
    print(f"  Expected ROI: {suggestion.expected_roi:.1f}x")
    
    print(f"\nSummary: {suggestion.summary()}")
    
    print(f"\nTop 10 Targets:")
    for target in suggestion.targets[:10]:
        print(f"  {target.label}: {target.churn_probability:.0%} churn risk, "
              f"₹{target.avg_spend:.0f} avg, ₹{target.cashback_amount:.0f} cashback")
    
    # Verify constraints
    assert len(suggestion.targets) <= 25, f"Too many targets: {len(suggestion.targets)}"
    
    total_cashback = sum(t.cashback_amount for t in suggestion.targets)
    assert total_cashback <= 500, f"Budget exceeded: ₹{total_cashback}"
    
    print("\n" + "=" * 60)
    print("Offer optimizer tests passed! ✓")
    print(f"  Targets ≤ 25: {len(suggestion.targets)} ✓")
    print(f"  Budget ≤ ₹500: ₹{total_cashback:.0f} ✓")
    print(f"  Expected revenue ~₹3,300: ₹{suggestion.expected_revenue:.0f}")
