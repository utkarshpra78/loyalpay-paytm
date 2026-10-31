"""Tests for Churn Model."""

import pytest
import tempfile
from pathlib import Path
import pandas as pd

from backend.config import config
from backend.generator import create_demo_generator
from backend.database import Database
from backend.churn_model import ChurnModel, ChurnFeatureBuilder, train_churn_model


class TestChurnFeatureBuilder:
    """Tests for feature building."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample payment data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            generator = create_demo_generator(seed=42)
            events = generator.generate_all_events()[:500]
            db.ingest_payments_batch(events)
            
            with db._connect() as conn:
                payments_df = pd.read_sql("SELECT * FROM payments", conn)
                customers_df = pd.read_sql("SELECT * FROM customers", conn)
            
            yield payments_df, customers_df
    
    def test_build_features_single(self, sample_data):
        """Test building features for single customer."""
        payments_df, customers_df = sample_data
        
        # Find a customer with multiple visits
        visit_counts = payments_df.groupby('customer_id').size()
        cid = visit_counts[visit_counts >= 3].index[0]
        
        payments_df['timestamp'] = pd.to_datetime(payments_df['timestamp'])
        ref_date = payments_df['timestamp'].max()
        
        features = ChurnFeatureBuilder.build_features(payments_df, cid, ref_date)
        
        assert features is not None
        assert len(features) == len(ChurnFeatureBuilder.FEATURE_NAMES)
    
    def test_insufficient_visits(self, sample_data):
        """Test that customers with < 2 visits return None."""
        payments_df, customers_df = sample_data
        
        # Find a customer with only 1 visit
        visit_counts = payments_df.groupby('customer_id').size()
        one_visit_customers = visit_counts[visit_counts == 1].index
        
        if len(one_visit_customers) > 0:
            cid = one_visit_customers[0]
            payments_df['timestamp'] = pd.to_datetime(payments_df['timestamp'])
            ref_date = payments_df['timestamp'].max()
            
            features = ChurnFeatureBuilder.build_features(payments_df, cid, ref_date)
            
            assert features is None


class TestChurnModel:
    """Tests for the churn model."""
    
    @pytest.fixture
    def full_data(self):
        """Load full demo data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            generator = create_demo_generator(seed=42)
            events = generator.generate_all_events()
            db.ingest_payments_batch(events)
            
            with db._connect() as conn:
                payments_df = pd.read_sql("SELECT * FROM payments", conn)
                customers_df = pd.read_sql("SELECT * FROM customers", conn)
            
            yield payments_df, customers_df, tmpdir
    
    def test_train_model(self, full_data):
        """Test model training."""
        payments_df, customers_df, tmpdir = full_data
        
        model = ChurnModel(model_path=Path(tmpdir) / "model.pkl")
        metrics = model.train(payments_df, customers_df)
        
        assert model.is_trained
        assert 'accuracy' in metrics
        assert 'roc_auc' in metrics
        assert metrics['accuracy'] > 0.5  # Better than random
    
    def test_predict(self, full_data):
        """Test predictions."""
        payments_df, customers_df, tmpdir = full_data
        
        model = ChurnModel(model_path=Path(tmpdir) / "model.pkl")
        model.train(payments_df, customers_df)
        
        customer_labels = {row['id']: row['label'] for _, row in customers_df.iterrows()}
        customer_ids = customers_df['id'].tolist()[:50]
        
        predictions = model.predict(payments_df, customer_ids, customer_labels)
        
        assert len(predictions) > 0
        assert all(0 <= p.churn_probability <= 1 for p in predictions)
        assert all(p.risk_level in ['high', 'medium', 'low'] for p in predictions)
    
    def test_save_load(self, full_data):
        """Test model persistence."""
        payments_df, customers_df, tmpdir = full_data
        
        model_path = Path(tmpdir) / "model.pkl"
        
        # Train and save
        model1 = ChurnModel(model_path=model_path)
        model1.train(payments_df, customers_df)
        model1.save()
        
        # Load
        model2 = ChurnModel(model_path=model_path)
        loaded = model2.load()
        
        assert loaded
        assert model2.is_trained
    
    def test_feature_importances(self, full_data):
        """Test feature importance retrieval."""
        payments_df, customers_df, tmpdir = full_data
        
        model = ChurnModel(model_path=Path(tmpdir) / "model.pkl")
        model.train(payments_df, customers_df)
        
        importances = model.get_feature_importances()
        
        assert len(importances) == len(ChurnFeatureBuilder.FEATURE_NAMES)
        assert all(v >= 0 for v in importances.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
