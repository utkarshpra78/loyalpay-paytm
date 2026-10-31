"""Tests for Offer Optimizer."""

import pytest
import tempfile
from pathlib import Path
import pandas as pd

from backend.config import config
from backend.generator import create_demo_generator
from backend.database import Database
from backend.analytics import calculate_rfm, segment_customers
from backend.optimizer import OfferOptimizer, suggest_offer, CampaignSuggestion


class TestOfferOptimizer:
    """Tests for offer optimization."""
    
    @pytest.fixture
    def segmented_data(self):
        """Create segmented customer data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            generator = create_demo_generator(seed=42)
            events = generator.generate_all_events()
            db.ingest_payments_batch(events)
            
            with db._connect() as conn:
                payments_df = pd.read_sql("SELECT * FROM payments", conn)
                customers_df = pd.read_sql("SELECT * FROM customers", conn)
            
            rfm_df = calculate_rfm(payments_df, customers_df)
            segmented_df = segment_customers(rfm_df)
            
            yield segmented_df
    
    def test_calculate_cashback(self):
        """Test cashback calculation."""
        optimizer = OfferOptimizer()
        
        # 15% of 100, rounded to nearest 5
        assert optimizer.calculate_cashback(100) == 15
        
        # 15% of 150 = 22.5, rounds to 20
        assert optimizer.calculate_cashback(150) == 20
        
        # Minimum cashback is 10
        assert optimizer.calculate_cashback(50) >= 10
    
    def test_rank_customers(self, segmented_data):
        """Test customer ranking."""
        optimizer = OfferOptimizer()
        
        ranked = optimizer.rank_customers(segmented_data)
        
        # Should have some targets
        assert len(ranked) > 0
        
        # Should be sorted by expected value (descending)
        for i in range(len(ranked) - 1):
            assert ranked[i].expected_value >= ranked[i + 1].expected_value
    
    def test_select_targets_budget(self, segmented_data):
        """Test budget constraint."""
        optimizer = OfferOptimizer()
        
        ranked = optimizer.rank_customers(segmented_data)
        targets, cost = optimizer.select_targets(ranked, budget=500)
        
        # Cost should not exceed budget
        assert cost <= 500
        
        # Total cashback should match cost
        total_cashback = sum(t.cashback_amount for t in targets)
        assert abs(total_cashback - cost) < 0.01
    
    def test_suggest_campaign(self, segmented_data):
        """Test full campaign suggestion."""
        suggestion = suggest_offer(segmented_data, budget=500)
        
        assert isinstance(suggestion, CampaignSuggestion)
        assert suggestion.total_budget == 500
        assert len(suggestion.targets) > 0
        assert suggestion.expected_roi > 0
    
    def test_target_count_limit(self, segmented_data):
        """Test that targets stay within budget."""
        optimizer = OfferOptimizer()
        
        ranked = optimizer.rank_customers(segmented_data)
        
        # With ₹500 budget and ~₹15-20 cashback, should get ~25-33 targets
        targets, cost = optimizer.select_targets(ranked, budget=500)
        
        assert len(targets) <= 35  # Reasonable upper bound
        assert cost <= 500
    
    def test_roi_projection(self, segmented_data):
        """Test ROI projections."""
        optimizer = OfferOptimizer()
        
        ranked = optimizer.rank_customers(segmented_data)
        targets, cost = optimizer.select_targets(ranked, budget=500)
        
        roi = optimizer.project_roi(targets, cost)
        
        assert roi['expected_redemptions'] > 0
        assert roi['expected_revenue'] > roi['expected_cashback_spent']
        assert roi['expected_roi'] > 1  # Should be profitable


class TestDemoNumbers:
    """Test that demo produces expected numbers."""
    
    @pytest.fixture
    def suggestion(self):
        """Generate suggestion with demo data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            generator = create_demo_generator(seed=42)
            events = generator.generate_all_events()
            db.ingest_payments_batch(events)
            
            with db._connect() as conn:
                payments_df = pd.read_sql("SELECT * FROM payments", conn)
                customers_df = pd.read_sql("SELECT * FROM customers", conn)
            
            rfm_df = calculate_rfm(payments_df, customers_df)
            segmented_df = segment_customers(rfm_df)
            
            yield suggest_offer(segmented_df, budget=500)
    
    def test_expected_revenue_range(self, suggestion):
        """Expected revenue should be in reasonable range (~₹3,300)."""
        # Allow for variance
        assert 2000 <= suggestion.expected_revenue <= 5000
    
    def test_expected_roi_range(self, suggestion):
        """ROI should be positive."""
        assert suggestion.expected_roi > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
