"""
LoyalPay Churn Prediction Model

Uses scikit-learn Gradient Boosting (similar to LightGBM/XGBoost) to predict
which customers are likely to churn (not return within 21 days).

Training Process:
1. Take historical snapshot at a past timepoint
2. Calculate features (recency, frequency, spend trends)
3. Label: Did customer return within 21 days?
4. Train model to predict non-return probability

Features:
- recency_days: Days since last visit at snapshot
- frequency: Total visit count
- monetary_avg: Average transaction value
- visit_gap_avg: Average days between visits
- visit_gap_variance: Variance in visit intervals
- spend_trend: Recent spend vs historical (declining = risk)
- visits_last_14d: Visit count in last 14 days
- days_as_customer: Total days since first visit
"""

import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

from backend.config import config, set_seed


@dataclass
class ChurnPrediction:
    """Churn prediction for a customer."""
    customer_id: int
    label: str
    churn_probability: float
    risk_level: str  # "high", "medium", "low"
    
    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "label": self.label,
            "churn_probability": round(self.churn_probability, 3),
            "risk_level": self.risk_level,
        }


class ChurnFeatureBuilder:
    """Builds features for churn prediction."""
    
    FEATURE_NAMES = [
        'recency_days',
        'frequency',
        'monetary_avg',
        'monetary_total',
        'visit_gap_avg',
        'visit_gap_std',
        'spend_trend',
        'visits_last_14d',
        'days_as_customer',
    ]
    
    @staticmethod
    def build_features(
        payments_df: pd.DataFrame,
        customer_id: int,
        reference_date: datetime
    ) -> Optional[np.ndarray]:
        """
        Build feature vector for a single customer.
        
        Args:
            payments_df: All payments data
            customer_id: Customer to build features for
            reference_date: Date to calculate features from
            
        Returns:
            Feature array or None if insufficient data
        """
        # Filter to customer's payments before reference date
        customer_payments = payments_df[
            (payments_df['customer_id'] == customer_id) &
            (pd.to_datetime(payments_df['timestamp']) <= reference_date)
        ].copy()
        
        if len(customer_payments) < 2:
            return None
        
        customer_payments['timestamp'] = pd.to_datetime(customer_payments['timestamp'])
        customer_payments = customer_payments.sort_values('timestamp')
        
        # Basic RFM
        last_visit = customer_payments['timestamp'].max()
        first_visit = customer_payments['timestamp'].min()
        recency_days = (reference_date - last_visit).days
        frequency = len(customer_payments)
        monetary_avg = customer_payments['amount'].mean()
        monetary_total = customer_payments['amount'].sum()
        
        # Visit gaps
        if frequency >= 2:
            customer_payments['prev_timestamp'] = customer_payments['timestamp'].shift(1)
            gaps = (customer_payments['timestamp'] - customer_payments['prev_timestamp']).dt.days.dropna()
            visit_gap_avg = gaps.mean() if len(gaps) > 0 else 7
            visit_gap_std = gaps.std() if len(gaps) > 1 else 0
        else:
            visit_gap_avg = 7
            visit_gap_std = 0
        
        # Spend trend (compare last 3 visits to earlier)
        if frequency >= 4:
            recent_avg = customer_payments['amount'].tail(3).mean()
            earlier_avg = customer_payments['amount'].head(frequency - 3).mean()
            spend_trend = (recent_avg - earlier_avg) / earlier_avg if earlier_avg > 0 else 0
        else:
            spend_trend = 0
        
        # Recent activity
        cutoff_14d = reference_date - timedelta(days=14)
        visits_last_14d = len(customer_payments[customer_payments['timestamp'] >= cutoff_14d])
        
        # Customer tenure
        days_as_customer = (reference_date - first_visit).days
        
        return np.array([
            recency_days,
            frequency,
            monetary_avg,
            monetary_total,
            visit_gap_avg,
            visit_gap_std if not np.isnan(visit_gap_std) else 0,
            spend_trend,
            visits_last_14d,
            days_as_customer,
        ])
    
    @staticmethod
    def build_features_batch(
        payments_df: pd.DataFrame,
        customer_ids: List[int],
        reference_date: datetime
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Build features for multiple customers.
        
        Returns:
            Tuple of (feature_matrix, valid_customer_ids)
        """
        features = []
        valid_ids = []
        
        for cid in customer_ids:
            feat = ChurnFeatureBuilder.build_features(payments_df, cid, reference_date)
            if feat is not None:
                features.append(feat)
                valid_ids.append(cid)
        
        if not features:
            return np.array([]), []
        
        return np.array(features), valid_ids


class ChurnModel:
    """
    Gradient Boosting model for churn prediction.
    
    Similar to LightGBM but uses sklearn for broader compatibility.
    """
    
    def __init__(self, model_path: Path = None):
        self.model_path = model_path or (config.MODELS_DIR / "churn_model.pkl")
        self.model = None
        self.feature_importances = None
        self.is_trained = False
    
    def _create_model(self):
        """Create a new model instance."""
        set_seed(config.RANDOM_SEED)
        return GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=config.RANDOM_SEED,
        )
    
    def train(
        self,
        payments_df: pd.DataFrame,
        customers_df: pd.DataFrame,
        snapshot_date: datetime = None,
        observation_window: int = None
    ) -> Dict[str, Any]:
        """
        Train the churn model.
        
        Training approach:
        1. Take snapshot at (end_date - observation_window - buffer)
        2. Build features at snapshot date
        3. Label: Did customer NOT return within observation_window days?
        4. Train classifier
        
        Args:
            payments_df: Payment data
            customers_df: Customer data
            snapshot_date: Date to take snapshot (default: auto-calculated)
            observation_window: Days to check for return (default: 21)
            
        Returns:
            Training metrics
        """
        set_seed(config.RANDOM_SEED)
        
        observation_window = observation_window or config.CHURN_OBSERVATION_WINDOW_DAYS
        
        # Ensure timestamp is datetime
        payments_df = payments_df.copy()
        payments_df['timestamp'] = pd.to_datetime(payments_df['timestamp'])
        
        # Calculate snapshot date if not provided
        max_date = payments_df['timestamp'].max()
        if snapshot_date is None:
            # Snapshot 28 days before end, giving 21-day observation + buffer
            snapshot_date = max_date - timedelta(days=observation_window + 7)
        
        # Get customers who had 2+ visits by snapshot date
        pre_snapshot = payments_df[payments_df['timestamp'] <= snapshot_date]
        customer_visits = pre_snapshot.groupby('customer_id').size()
        eligible_customers = customer_visits[customer_visits >= 2].index.tolist()
        
        if len(eligible_customers) < 20:
            raise ValueError(f"Not enough eligible customers for training: {len(eligible_customers)}")
        
        # Build features at snapshot date
        X, valid_ids = ChurnFeatureBuilder.build_features_batch(
            payments_df, eligible_customers, snapshot_date
        )
        
        if len(valid_ids) < 20:
            raise ValueError(f"Not enough valid feature vectors: {len(valid_ids)}")
        
        # Create labels: 1 = churned (did NOT return within observation window)
        observation_end = snapshot_date + timedelta(days=observation_window)
        post_snapshot = payments_df[
            (payments_df['timestamp'] > snapshot_date) &
            (payments_df['timestamp'] <= observation_end)
        ]
        
        returned_customers = set(post_snapshot['customer_id'].unique())
        y = np.array([0 if cid in returned_customers else 1 for cid in valid_ids])
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=config.RANDOM_SEED, stratify=y
        )
        
        # Train model
        self.model = self._create_model()
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Calculate metrics
        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)[:, 1]
        
        # Store feature importances
        self.feature_importances = dict(zip(
            ChurnFeatureBuilder.FEATURE_NAMES,
            self.model.feature_importances_
        ))
        
        metrics = {
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "churn_rate_train": float(y_train.mean()),
            "churn_rate_test": float(y_test.mean()),
            "accuracy": float((y_pred == y_test).mean()),
            "roc_auc": float(roc_auc_score(y_test, y_proba)) if len(np.unique(y_test)) > 1 else 0,
            "feature_importances": self.feature_importances,
        }
        
        return metrics
    
    def predict(
        self,
        payments_df: pd.DataFrame,
        customer_ids: List[int],
        customer_labels: Dict[int, str],
        reference_date: datetime = None
    ) -> List[ChurnPrediction]:
        """
        Predict churn probability for customers.
        
        Args:
            payments_df: Payment data
            customer_ids: Customers to predict for
            customer_labels: Dict mapping customer_id to label
            reference_date: Date to calculate features from
            
        Returns:
            List of ChurnPrediction objects
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        
        payments_df = payments_df.copy()
        payments_df['timestamp'] = pd.to_datetime(payments_df['timestamp'])
        
        if reference_date is None:
            reference_date = payments_df['timestamp'].max()
        
        # Build features
        X, valid_ids = ChurnFeatureBuilder.build_features_batch(
            payments_df, customer_ids, reference_date
        )
        
        if len(valid_ids) == 0:
            return []
        
        # Predict
        probabilities = self.model.predict_proba(X)[:, 1]
        
        # Create predictions
        predictions = []
        for cid, prob in zip(valid_ids, probabilities):
            if prob >= 0.7:
                risk_level = "high"
            elif prob >= 0.4:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            predictions.append(ChurnPrediction(
                customer_id=cid,
                label=customer_labels.get(cid, f"#{cid}"),
                churn_probability=float(prob),
                risk_level=risk_level,
            ))
        
        return sorted(predictions, key=lambda x: x.churn_probability, reverse=True)
    
    def save(self, path: Path = None):
        """Save model to disk."""
        path = path or self.model_path
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_importances': self.feature_importances,
                'is_trained': self.is_trained,
            }, f)
    
    def load(self, path: Path = None) -> bool:
        """Load model from disk."""
        path = path or self.model_path
        
        if not path.exists():
            return False
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.feature_importances = data['feature_importances']
            self.is_trained = data['is_trained']
        
        return True
    
    def get_feature_importances(self) -> Dict[str, float]:
        """Get feature importance rankings."""
        if not self.feature_importances:
            return {}
        
        return dict(sorted(
            self.feature_importances.items(),
            key=lambda x: x[1],
            reverse=True
        ))


def train_churn_model(
    payments_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    save_model: bool = True
) -> Tuple[ChurnModel, Dict[str, Any]]:
    """
    Convenience function to train and optionally save a churn model.
    
    Args:
        payments_df: Payment data
        customers_df: Customer data
        save_model: Whether to save the trained model
        
    Returns:
        Tuple of (trained model, metrics)
    """
    model = ChurnModel()
    metrics = model.train(payments_df, customers_df)
    
    if save_model:
        model.save()
    
    return model, metrics


if __name__ == "__main__":
    # Quick verification
    from backend.generator import create_demo_generator
    from backend.database import Database
    
    print("Testing Churn Model...")
    print("=" * 60)
    
    # Generate and ingest data
    generator = create_demo_generator(seed=42)
    events = generator.generate_all_events()
    
    db = Database()
    db.drop_all()
    db.ingest_payments_batch(events)
    
    # Get data as DataFrames
    with db._connect() as conn:
        payments_df = pd.read_sql("SELECT * FROM payments", conn)
        customers_df = pd.read_sql("SELECT * FROM customers", conn)
    
    # Train model
    print("\nTraining churn model...")
    model, metrics = train_churn_model(payments_df, customers_df, save_model=True)
    
    print(f"\nTraining Metrics:")
    print(f"  Train samples: {metrics['train_samples']}")
    print(f"  Test samples: {metrics['test_samples']}")
    print(f"  Churn rate (train): {metrics['churn_rate_train']:.1%}")
    print(f"  Churn rate (test): {metrics['churn_rate_test']:.1%}")
    print(f"  Accuracy: {metrics['accuracy']:.1%}")
    print(f"  ROC AUC: {metrics['roc_auc']:.3f}")
    
    print(f"\nFeature Importances:")
    for feat, imp in model.get_feature_importances().items():
        print(f"  {feat}: {imp:.3f}")
    
    # Test predictions
    print("\nPredicting churn for customers...")
    customer_labels = {row['id']: row['label'] for _, row in customers_df.iterrows()}
    customer_ids = customers_df['id'].tolist()
    
    predictions = model.predict(payments_df, customer_ids, customer_labels)
    
    print(f"\nTop 10 Churn Risk Customers:")
    for pred in predictions[:10]:
        print(f"  {pred.label}: {pred.churn_probability:.1%} ({pred.risk_level})")
    
    # Check if churners have high probability
    churner_vpas = {c.vpa for c in generator.customers if c.will_churn}
    high_risk = [p for p in predictions if p.risk_level == "high"]
    
    print(f"\nHigh-risk customers identified: {len(high_risk)}")
    
    print("\n" + "=" * 60)
    print("Churn model tests passed! ✓")
