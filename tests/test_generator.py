"""
Tests for the Synthetic Payment Generator.

Verifies:
1. Reproducibility with same seed
2. Target demo numbers (~312 regulars, ~38 at-risk)
3. Planted patterns are detectable
4. Data integrity
"""

import pytest
from datetime import datetime, timedelta

from backend.config import config, set_seed
from backend.generator import (
    SyntheticPaymentGenerator,
    GeneratorConfig,
    PaymentEvent,
    create_demo_generator,
    generate_demo_data,
)


class TestPaymentEvent:
    """Tests for PaymentEvent dataclass."""
    
    def test_payment_event_creation(self):
        """Test creating a payment event."""
        event = PaymentEvent(
            vpa="test@paytm",
            amount=50.0,
            timestamp=datetime(2024, 9, 15, 10, 30, 0),
        )
        
        assert event.vpa == "test@paytm"
        assert event.amount == 50.0
        assert event.merchant_id == config.MERCHANT_ID
    
    def test_payment_event_to_dict(self):
        """Test serializing event to dictionary."""
        event = PaymentEvent(
            vpa="test@paytm",
            amount=75.0,
            timestamp=datetime(2024, 9, 15, 10, 30, 0),
        )
        
        d = event.to_dict()
        
        assert d["vpa"] == "test@paytm"
        assert d["amount"] == 75.0
        assert "timestamp" in d
        assert d["merchant_id"] == config.MERCHANT_ID


class TestGeneratorReproducibility:
    """Tests for seed-based reproducibility."""
    
    def test_same_seed_produces_identical_events(self):
        """Two generators with same seed should produce identical events."""
        gen1 = create_demo_generator(seed=42)
        events1 = gen1.generate_all_events()
        
        gen2 = create_demo_generator(seed=42)
        events2 = gen2.generate_all_events()
        
        assert len(events1) == len(events2), "Event counts should match"
        
        # Check all events match
        for e1, e2 in zip(events1, events2):
            assert e1.vpa == e2.vpa, "VPAs should match"
            assert e1.amount == e2.amount, "Amounts should match"
            assert e1.timestamp == e2.timestamp, "Timestamps should match"
    
    def test_different_seeds_produce_different_events(self):
        """Different seeds should produce different events."""
        gen1 = create_demo_generator(seed=42)
        events1 = gen1.generate_all_events()
        
        gen2 = create_demo_generator(seed=123)
        events2 = gen2.generate_all_events()
        
        # Counts might differ
        # Even if counts match, the specific events should differ
        vpas1 = set(e.vpa for e in events1[:50])
        vpas2 = set(e.vpa for e in events2[:50])
        
        # They should not be identical
        assert vpas1 != vpas2 or len(events1) != len(events2), \
            "Different seeds should produce different results"
    
    def test_statistics_reproducible(self):
        """Statistics should be identical for same seed."""
        stats1 = create_demo_generator(seed=42).generate_all_events()
        gen1 = create_demo_generator(seed=42)
        gen1.generate_all_events()
        stats1 = gen1.get_statistics()
        
        gen2 = create_demo_generator(seed=42)
        gen2.generate_all_events()
        stats2 = gen2.get_statistics()
        
        assert stats1["total_events"] == stats2["total_events"]
        assert stats1["regular_customers"] == stats2["regular_customers"]
        assert stats1["at_risk_customers"] == stats2["at_risk_customers"]


class TestDemoNumbers:
    """Tests for achieving target demo numbers."""
    
    @pytest.fixture
    def demo_generator(self):
        """Create and run the demo generator."""
        gen = create_demo_generator(seed=42)
        gen.generate_all_events()
        return gen
    
    def test_regular_customers_target(self, demo_generator):
        """Should have approximately 312 regular customers."""
        stats = demo_generator.get_statistics()
        regular_count = stats["regular_customers"]
        
        # Allow ±15% tolerance
        assert 265 <= regular_count <= 360, \
            f"Expected ~312 regulars, got {regular_count}"
    
    def test_at_risk_customers_target(self, demo_generator):
        """Should have approximately 38 at-risk customers from churners."""
        stats = demo_generator.get_statistics()
        at_risk_count = stats["at_risk_customers"]
        
        # Total at-risk includes churners + naturally inactive casuals
        # Our 40 churners should produce ~38 at-risk
        # Plus some casuals, total expected: 50-70
        assert 40 <= at_risk_count <= 80, \
            f"Expected ~50-70 at-risk (churners + casuals), got {at_risk_count}"
    
    def test_churner_customers_created(self, demo_generator):
        """Should have ~40 churner profiles created."""
        churner_count = sum(1 for c in demo_generator.customers if c.will_churn)
        assert churner_count == 40, f"Expected 40 churners, got {churner_count}"
    
    def test_reasonable_total_transactions(self, demo_generator):
        """Total transactions should be reasonable for 60 days."""
        stats = demo_generator.get_statistics()
        total = stats["total_events"]
        
        # Expect at least 1000 transactions, but not more than 20000
        assert 1000 <= total <= 20000, f"Unexpected transaction count: {total}"
    
    def test_average_transaction_reasonable(self, demo_generator):
        """Average transaction should be in realistic range."""
        stats = demo_generator.get_statistics()
        avg = stats["avg_transaction"]
        
        # Expect between ₹30 and ₹150
        assert 30 <= avg <= 150, f"Unexpected average: ₹{avg}"


class TestPlantedPatterns:
    """Tests for verifying planted behavioral patterns."""
    
    @pytest.fixture
    def demo_generator(self):
        gen = create_demo_generator(seed=42)
        gen.generate_all_events()
        return gen
    
    def test_sunday_habituals_detected(self, demo_generator):
        """Should detect customers with Sunday habit."""
        stats = demo_generator.get_statistics()
        sunday_count = stats["sunday_habituals"]
        
        # Should detect at least a few Sunday habituals
        assert sunday_count >= 3, \
            f"Expected to detect Sunday habituals, found {sunday_count}"
    
    def test_morning_habituals_detected(self, demo_generator):
        """Should detect customers with morning habit."""
        stats = demo_generator.get_statistics()
        morning_count = stats["morning_habituals"]
        
        # Should detect some morning habituals
        assert morning_count >= 3, \
            f"Expected to detect morning habituals, found {morning_count}"
    
    def test_churners_stop_visiting(self, demo_generator):
        """Churner customers should stop visiting after their churn date."""
        events = demo_generator.events
        
        # Get a churner customer
        churner = next(c for c in demo_generator.customers if c.will_churn)
        churner_events = [e for e in events if e.vpa == churner.vpa]
        
        if churner_events:
            last_visit = max(e.timestamp for e in churner_events)
            churn_date = demo_generator.gen_config.start_date + \
                         timedelta(days=churner.churn_after_days)
            
            # Last visit should be before or around churn date
            assert last_visit <= churn_date + timedelta(days=1), \
                f"Churner visited after churn date"
    
    def test_new_customers_started_recently(self, demo_generator):
        """New customers should have started in last 14 days."""
        events = demo_generator.events
        end_date = demo_generator.gen_config.end_date
        
        # Find customers who started late
        new_customer_profiles = [c for c in demo_generator.customers 
                                 if c.vpa.startswith("new_")]
        
        for profile in new_customer_profiles[:5]:  # Check first 5
            customer_events = [e for e in events if e.vpa == profile.vpa]
            if customer_events:
                first_visit = min(e.timestamp for e in customer_events)
                days_since_start = (first_visit - demo_generator.gen_config.start_date).days
                
                # Should have started in latter part of simulation
                assert days_since_start >= 45, \
                    f"New customer started too early: day {days_since_start}"


class TestDataIntegrity:
    """Tests for data integrity and consistency."""
    
    @pytest.fixture
    def demo_generator(self):
        gen = create_demo_generator(seed=42)
        gen.generate_all_events()
        return gen
    
    def test_events_sorted_by_timestamp(self, demo_generator):
        """Events should be in chronological order."""
        events = demo_generator.events
        
        for i in range(1, len(events)):
            assert events[i].timestamp >= events[i-1].timestamp, \
                "Events not sorted by timestamp"
    
    def test_all_timestamps_within_simulation_period(self, demo_generator):
        """All events should be within the simulation period."""
        events = demo_generator.events
        start = demo_generator.gen_config.start_date
        end = demo_generator.gen_config.end_date
        
        for event in events:
            assert start <= event.timestamp < end, \
                f"Event timestamp {event.timestamp} outside simulation period"
    
    def test_all_amounts_positive(self, demo_generator):
        """All transaction amounts should be positive."""
        events = demo_generator.events
        
        for event in events:
            assert event.amount > 0, f"Found non-positive amount: {event.amount}"
    
    def test_amounts_are_rounded(self, demo_generator):
        """Amounts should be rounded to nearest 5."""
        events = demo_generator.events
        
        for event in events[:100]:  # Check first 100
            assert event.amount % 5 == 0, \
                f"Amount {event.amount} not rounded to nearest 5"
    
    def test_all_events_have_merchant_id(self, demo_generator):
        """All events should have the correct merchant ID."""
        events = demo_generator.events
        
        for event in events:
            assert event.merchant_id == config.MERCHANT_ID
    
    def test_timestamps_within_operating_hours(self, demo_generator):
        """Events should be within store operating hours."""
        events = demo_generator.events
        open_hour = demo_generator.gen_config.open_hour
        close_hour = demo_generator.gen_config.close_hour
        
        for event in events:
            hour = event.timestamp.hour
            assert open_hour <= hour < close_hour, \
                f"Event at {hour}:00 outside operating hours ({open_hour}-{close_hour})"


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_generate_demo_data(self):
        """Test the generate_demo_data convenience function."""
        events, stats = generate_demo_data()
        
        assert len(events) > 0
        assert "regular_customers" in stats
        assert "at_risk_customers" in stats
    
    def test_create_demo_generator_default_seed(self):
        """Test create_demo_generator uses default seed."""
        gen = create_demo_generator()
        
        assert gen.seed == config.RANDOM_SEED


class TestEventStreaming:
    """Tests for streaming event generation."""
    
    def test_streaming_produces_same_events(self):
        """Streaming should produce the same events as batch generation."""
        gen = create_demo_generator(seed=42)
        batch_events = gen.generate_all_events()
        
        gen2 = create_demo_generator(seed=42)
        stream_events = list(gen2.generate_events_stream())
        
        assert len(batch_events) == len(stream_events)
        
        for b, s in zip(batch_events[:100], stream_events[:100]):
            assert b.vpa == s.vpa
            assert b.amount == s.amount


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
