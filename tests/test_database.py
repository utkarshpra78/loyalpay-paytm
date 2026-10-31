"""
Tests for the Database Module.

Verifies:
1. HMAC-SHA256 hashing is deterministic and irreversible
2. Same VPA produces same hash and label
3. Database schema and operations work correctly
4. Visit counts are accurate
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from backend.database import (
    Database,
    PrivacyHasher,
    Customer,
    Payment,
    Campaign,
)
from backend.generator import PaymentEvent, create_demo_generator


class TestPrivacyHasher:
    """Tests for the privacy hashing functionality."""
    
    def test_same_vpa_same_hash(self):
        """Same VPA should always produce the same hash."""
        hasher = PrivacyHasher()
        
        vpa = "rahul123@paytm"
        hash1 = hasher.hash_vpa(vpa)
        hash2 = hasher.hash_vpa(vpa)
        
        assert hash1 == hash2, "Same VPA should produce identical hash"
    
    def test_different_vpa_different_hash(self):
        """Different VPAs should produce different hashes."""
        hasher = PrivacyHasher()
        
        hash1 = hasher.hash_vpa("rahul123@paytm")
        hash2 = hasher.hash_vpa("priya456@paytm")
        
        assert hash1 != hash2, "Different VPAs should produce different hashes"
    
    def test_hash_is_hex_string(self):
        """Hash should be a valid hex string."""
        hasher = PrivacyHasher()
        
        hash_value = hasher.hash_vpa("test@paytm")
        
        # SHA256 produces 64 hex characters
        assert len(hash_value) == 64
        assert all(c in '0123456789abcdef' for c in hash_value)
    
    def test_hash_irreversible(self):
        """Hash should not contain the original VPA."""
        hasher = PrivacyHasher()
        
        vpa = "rahul123@paytm"
        hash_value = hasher.hash_vpa(vpa)
        
        assert vpa not in hash_value
        assert "rahul" not in hash_value
        assert "paytm" not in hash_value
    
    def test_different_secret_different_hash(self):
        """Different secret keys should produce different hashes."""
        hasher1 = PrivacyHasher(secret_key="key1")
        hasher2 = PrivacyHasher(secret_key="key2")
        
        vpa = "test@paytm"
        hash1 = hasher1.hash_vpa(vpa)
        hash2 = hasher2.hash_vpa(vpa)
        
        assert hash1 != hash2
    
    def test_label_generation(self):
        """Labels should be generated correctly."""
        hasher = PrivacyHasher()
        
        token1 = hasher.hash_vpa("user1@paytm")
        label1 = hasher.generate_label(token1)
        
        assert label1.startswith("#")
        assert len(label1) >= 3
    
    def test_same_token_same_label(self):
        """Same token should always get same label."""
        hasher = PrivacyHasher()
        
        token = hasher.hash_vpa("user@paytm")
        label1 = hasher.generate_label(token)
        label2 = hasher.generate_label(token)
        
        assert label1 == label2
    
    def test_different_tokens_different_labels(self):
        """Different tokens should get different labels."""
        hasher = PrivacyHasher()
        
        token1 = hasher.hash_vpa("user1@paytm")
        token2 = hasher.hash_vpa("user2@paytm")
        
        label1 = hasher.generate_label(token1)
        label2 = hasher.generate_label(token2)
        
        assert label1 != label2
    
    def test_label_format(self):
        """Labels should follow #<letter><number> format."""
        hasher = PrivacyHasher()
        
        # Generate several labels
        for i in range(10):
            token = hasher.hash_vpa(f"user{i}@paytm")
            label = hasher.generate_label(token)
            
            assert label.startswith("#")
            # Should have letter(s) followed by digits
            rest = label[1:]
            assert any(c.isalpha() for c in rest)
            assert any(c.isdigit() for c in rest)


class TestDatabase:
    """Tests for the Database class."""
    
    @pytest.fixture
    def db(self):
        """Create a fresh database for each test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            yield db
    
    def test_create_database(self, db):
        """Database should be created with schema."""
        # Should be able to query tables
        with db._connect() as conn:
            # Check tables exist
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t['name'] for t in tables]
            
            assert 'customers' in table_names
            assert 'payments' in table_names
            assert 'campaigns' in table_names
            assert 'campaign_targets' in table_names
    
    def test_get_or_create_customer_new(self, db):
        """Should create new customer for new VPA."""
        customer = db.get_or_create_customer("new_user@paytm")
        
        assert customer.id is not None
        assert customer.token is not None
        assert customer.label.startswith("#")
        assert customer.opt_in is True
    
    def test_get_or_create_customer_existing(self, db):
        """Should return existing customer for same VPA."""
        c1 = db.get_or_create_customer("same_user@paytm")
        c2 = db.get_or_create_customer("same_user@paytm")
        
        assert c1.id == c2.id
        assert c1.token == c2.token
        assert c1.label == c2.label
    
    def test_ingest_payment(self, db):
        """Should ingest payment and create customer."""
        event = PaymentEvent(
            vpa="test_user@paytm",
            amount=50.0,
            timestamp=datetime(2024, 9, 15, 10, 30, 0),
        )
        
        customer, payment = db.ingest_payment(event)
        
        assert customer.id is not None
        assert payment.id is not None
        assert payment.customer_id == customer.id
        assert payment.amount == 50.0
    
    def test_ingest_same_customer_twice(self, db):
        """Two payments from same VPA should have same customer_id."""
        event1 = PaymentEvent(
            vpa="repeat_customer@paytm",
            amount=50.0,
            timestamp=datetime(2024, 9, 15, 10, 0, 0),
        )
        event2 = PaymentEvent(
            vpa="repeat_customer@paytm",
            amount=75.0,
            timestamp=datetime(2024, 9, 15, 11, 0, 0),
        )
        
        customer1, payment1 = db.ingest_payment(event1)
        customer2, payment2 = db.ingest_payment(event2)
        
        assert customer1.id == customer2.id
        assert customer1.label == customer2.label
        assert payment1.id != payment2.id
    
    def test_visit_counts(self, db):
        """Visit counts should be accurate."""
        # Create customer with 3 visits
        for i in range(3):
            event = PaymentEvent(
                vpa="frequent_customer@paytm",
                amount=50.0 + i * 10,
                timestamp=datetime(2024, 9, 15 + i, 10, 0, 0),
            )
            db.ingest_payment(event)
        
        # Create customer with 1 visit
        event = PaymentEvent(
            vpa="one_time@paytm",
            amount=30.0,
            timestamp=datetime(2024, 9, 15, 12, 0, 0),
        )
        db.ingest_payment(event)
        
        visit_counts = db.get_visit_counts()
        
        # Should have 2 customers
        assert len(visit_counts) == 2
        
        # Check counts
        counts = list(visit_counts.values())
        assert 3 in counts
        assert 1 in counts
    
    def test_customer_stats(self, db):
        """Customer stats should be calculated correctly."""
        # Create customer with multiple visits
        for i in range(3):
            event = PaymentEvent(
                vpa="stats_customer@paytm",
                amount=100.0,
                timestamp=datetime(2024, 9, 15 + i, 10, 0, 0),
            )
            db.ingest_payment(event)
        
        stats = db.get_customer_stats()
        
        assert len(stats) == 1
        assert stats[0]['visit_count'] == 3
        assert stats[0]['total_spent'] == 300.0
        assert stats[0]['avg_spent'] == 100.0
    
    def test_reset_clears_data(self, db):
        """Reset should clear all data."""
        # Add some data
        db.ingest_payment(PaymentEvent(
            vpa="test@paytm",
            amount=50.0,
            timestamp=datetime(2024, 9, 15, 10, 0, 0),
        ))
        
        # Verify data exists
        assert len(db.get_all_customers()) > 0
        
        # Reset
        db.reset()
        
        # Verify data cleared
        assert len(db.get_all_customers()) == 0
        assert len(db.get_visit_counts()) == 0


class TestCampaigns:
    """Tests for campaign functionality."""
    
    @pytest.fixture
    def db(self):
        """Create a fresh database with some customers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            
            # Create some customers
            for i in range(5):
                db.ingest_payment(PaymentEvent(
                    vpa=f"customer{i}@paytm",
                    amount=100.0,
                    timestamp=datetime(2024, 9, 15, 10 + i, 0, 0),
                ))
            
            yield db
    
    def test_create_campaign(self, db):
        """Should create campaign with targets."""
        customers = db.get_all_customers()
        target_ids = [c.id for c in customers[:3]]
        
        campaign = db.create_campaign(
            name="Test Campaign",
            cashback_amount=20.0,
            budget=100.0,
            target_customer_ids=target_ids,
        )
        
        assert campaign.id is not None
        assert campaign.name == "Test Campaign"
        assert campaign.cashback_amount == 20.0
        assert campaign.budget == 100.0
        assert campaign.status == 'active'
    
    def test_get_campaign(self, db):
        """Should retrieve campaign by ID."""
        customers = db.get_all_customers()
        target_ids = [c.id for c in customers[:2]]
        
        created = db.create_campaign(
            name="Retrievable Campaign",
            cashback_amount=15.0,
            budget=50.0,
            target_customer_ids=target_ids,
        )
        
        retrieved = db.get_campaign(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Retrievable Campaign"
    
    def test_campaign_redemption(self, db):
        """Should record redemption correctly."""
        customers = db.get_all_customers()
        target_id = customers[0].id
        
        campaign = db.create_campaign(
            name="Redemption Test",
            cashback_amount=20.0,
            budget=100.0,
            target_customer_ids=[target_id],
        )
        
        # Redeem
        success = db.redeem_campaign_offer(
            campaign_id=campaign.id,
            customer_id=target_id,
            redemption_amount=150.0,
        )
        
        assert success is True
        
        # Check ROI
        roi = db.get_campaign_roi(campaign.id)
        assert roi['redemptions_count'] == 1
        assert roi['cashback_spent'] == 20.0
        assert roi['revenue_recovered'] == 150.0
    
    def test_campaign_budget_limit(self, db):
        """Should not allow redemption beyond budget."""
        customers = db.get_all_customers()
        target_ids = [c.id for c in customers[:3]]
        
        # Small budget for only 1 redemption
        campaign = db.create_campaign(
            name="Limited Budget",
            cashback_amount=20.0,
            budget=25.0,  # Only enough for 1 redemption
            target_customer_ids=target_ids,
        )
        
        # First redemption should succeed
        success1 = db.redeem_campaign_offer(
            campaign_id=campaign.id,
            customer_id=target_ids[0],
            redemption_amount=100.0,
        )
        assert success1 is True
        
        # Second redemption should fail (budget exceeded)
        success2 = db.redeem_campaign_offer(
            campaign_id=campaign.id,
            customer_id=target_ids[1],
            redemption_amount=100.0,
        )
        assert success2 is False


class TestBatchIngestion:
    """Tests for batch payment ingestion."""
    
    @pytest.fixture
    def db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            yield Database(db_path)
    
    def test_batch_ingest(self, db):
        """Should ingest batch of events correctly."""
        generator = create_demo_generator(seed=42)
        events = generator.generate_all_events()[:50]
        
        count = db.ingest_payments_batch(events)
        
        assert count == 50
        
        # Check data is in database
        visit_counts = db.get_visit_counts()
        total_visits = sum(visit_counts.values())
        
        assert total_visits == 50
    
    def test_batch_maintains_customer_identity(self, db):
        """Batch ingestion should maintain consistent customer identity."""
        # Create events from same customer
        events = [
            PaymentEvent(
                vpa="batch_customer@paytm",
                amount=50.0 + i * 10,
                timestamp=datetime(2024, 9, 15 + i, 10, 0, 0),
            )
            for i in range(5)
        ]
        
        db.ingest_payments_batch(events)
        
        # Should only have 1 customer with 5 visits
        visit_counts = db.get_visit_counts()
        
        assert len(visit_counts) == 1
        assert list(visit_counts.values())[0] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
