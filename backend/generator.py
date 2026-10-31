"""
LoyalPay Synthetic Payment Generator

Generates realistic UPI payment events with planted patterns for demo purposes:
- #B07: Visits every Sunday at 8 AM (habit pattern)
- 38 customers who stop coming after ~45 days (churn pattern)
- Various customer segments (Champions, Loyal, New, At-Risk, Lost)

Target demo numbers (with seed=42):
- ~312 regular customers (2+ visits)
- ~38 at-risk customers (14-30 days since last visit)
- Various habit patterns detectable
"""

import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Generator
import numpy as np

from backend.config import config, set_seed


@dataclass
class PaymentEvent:
    """A single UPI payment transaction."""
    vpa: str  # Virtual Payment Address (e.g., rahul123@paytm)
    amount: float  # Transaction amount in INR
    timestamp: datetime  # When the payment occurred
    merchant_id: str = config.MERCHANT_ID
    
    def to_dict(self) -> dict:
        return {
            "vpa": self.vpa,
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat(),
            "merchant_id": self.merchant_id,
        }


@dataclass
class CustomerProfile:
    """
    Profile defining a synthetic customer's behavior patterns.
    Used to generate realistic payment sequences.
    """
    vpa: str
    
    # Visit frequency
    avg_visits_per_week: float = 1.0
    visit_variance: float = 0.3  # How much visit frequency varies
    
    # Spending patterns
    avg_amount: float = 50.0
    amount_std: float = 15.0
    
    # Time preferences (for habit patterns)
    preferred_day: Optional[int] = None  # 0=Monday, 6=Sunday
    preferred_hour: Optional[int] = None  # 0-23
    day_consistency: float = 0.3  # Probability of visiting on preferred day
    hour_consistency: float = 0.3  # Probability of visiting at preferred hour
    
    # Churn behavior
    will_churn: bool = False
    churn_after_days: Optional[int] = None  # Days after start when customer churns
    
    # Lifecycle
    first_visit_day: int = 0  # Day offset from simulation start
    
    def __post_init__(self):
        # Ensure reasonable bounds
        self.avg_amount = max(10, self.avg_amount)
        self.amount_std = max(5, self.amount_std)
        self.avg_visits_per_week = max(0.1, min(14, self.avg_visits_per_week))


@dataclass 
class GeneratorConfig:
    """Configuration for the payment generator."""
    
    # Simulation period
    start_date: datetime = field(default_factory=lambda: datetime(2024, 9, 1, 6, 0, 0))
    num_days: int = 60
    
    # Customer counts by type - tuned for target: ~312 regulars, ~38 at-risk
    num_champions: int = 28      # High frequency, still active
    num_loyal: int = 95          # Regular visitors, still active
    num_casual: int = 130        # Occasional visitors (many become regulars)
    num_new: int = 40            # Started in last 2 weeks
    num_churners: int = 40       # Will stop coming - slightly more to account for variance
    num_one_timers: int = 90     # Single visit only (not counted as regulars)
    
    # Special planted patterns
    num_sunday_habituals: int = 10  # Visit specifically on Sundays
    num_morning_habituals: int = 15  # Visit specifically in morning (7-9 AM)
    
    # Store operating hours
    open_hour: int = 6
    close_hour: int = 22
    
    # Peak hours (higher probability of visits)
    morning_peak: tuple = (7, 10)   # 7 AM - 10 AM
    evening_peak: tuple = (17, 20)  # 5 PM - 8 PM
    
    @property
    def end_date(self) -> datetime:
        return self.start_date + timedelta(days=self.num_days)
    
    @property
    def total_potential_regulars(self) -> int:
        """Total customers who could become regulars (2+ visits)."""
        return (self.num_champions + self.num_loyal + self.num_casual + 
                self.num_new + self.num_churners)


class SyntheticPaymentGenerator:
    """
    Generates synthetic UPI payment events with planted patterns.
    
    Patterns planted for demo:
    1. Champion customers: 15+ visits, active within 3 days
    2. Loyal customers: Regular weekly visits
    3. Habit patterns: Specific day/hour preferences
    4. Churn pattern: 38 customers stop coming after ~45 days
    5. New customers: First visit within last 14 days
    """
    
    def __init__(self, gen_config: GeneratorConfig = None, seed: int = None):
        self.gen_config = gen_config or GeneratorConfig()
        self.seed = seed or config.RANDOM_SEED
        self.customers: List[CustomerProfile] = []
        self.events: List[PaymentEvent] = []
        
        # Initialize
        set_seed(self.seed)
        self._create_customer_profiles()
    
    def _generate_vpa(self, index: int, prefix: str = "") -> str:
        """Generate a realistic-looking VPA."""
        names = [
            "rahul", "priya", "amit", "neha", "vijay", "anita", "suresh", "kavita",
            "rajesh", "sunita", "mohan", "deepa", "anil", "meera", "sanjay", "pooja",
            "ravi", "nisha", "ashok", "rekha", "manoj", "geeta", "vinod", "shanti",
            "kumar", "lakshmi", "prakash", "usha", "dinesh", "kamla", "ramesh", "saroj"
        ]
        suffixes = ["", "123", "456", "789", "99", "2024", "01", "007", "_upi", ".paytm"]
        providers = ["@paytm", "@ybl", "@oksbi", "@okaxis", "@okicici"]
        
        name = random.choice(names)
        suffix = random.choice(suffixes)
        provider = random.choice(providers)
        
        return f"{prefix}{name}{suffix}{index}{provider}"
    
    def _create_customer_profiles(self):
        """Create all customer profiles with their behavior patterns."""
        self.customers = []
        customer_idx = 0
        
        # 1. Champions - High frequency, still very active
        for i in range(self.gen_config.num_champions):
            self.customers.append(CustomerProfile(
                vpa=self._generate_vpa(customer_idx, "champ_"),
                avg_visits_per_week=random.uniform(3, 5),  # 3-5 visits/week
                avg_amount=random.uniform(30, 80),
                amount_std=random.uniform(10, 25),
                first_visit_day=random.randint(0, 10),  # Started early
                day_consistency=random.uniform(0.2, 0.4),
                hour_consistency=random.uniform(0.2, 0.4),
            ))
            customer_idx += 1
        
        # 2. Loyal customers - Regular weekly visitors
        for i in range(self.gen_config.num_loyal):
            self.customers.append(CustomerProfile(
                vpa=self._generate_vpa(customer_idx, "loyal_"),
                avg_visits_per_week=random.uniform(1.5, 3),  # 1.5-3 visits/week
                avg_amount=random.uniform(40, 120),
                amount_std=random.uniform(15, 35),
                first_visit_day=random.randint(0, 20),
                day_consistency=random.uniform(0.3, 0.5),
                hour_consistency=random.uniform(0.3, 0.5),
            ))
            customer_idx += 1
        
        # 3. Casual visitors - Occasional
        for i in range(self.gen_config.num_casual):
            self.customers.append(CustomerProfile(
                vpa=self._generate_vpa(customer_idx, "casual_"),
                avg_visits_per_week=random.uniform(0.3, 1),  # Every 1-3 weeks
                avg_amount=random.uniform(30, 100),
                amount_std=random.uniform(10, 30),
                first_visit_day=random.randint(0, 30),
                day_consistency=random.uniform(0.1, 0.3),
                hour_consistency=random.uniform(0.1, 0.3),
            ))
            customer_idx += 1
        
        # 4. New customers - Started in last 14 days
        for i in range(self.gen_config.num_new):
            # Start between day 46 and day 58 (last 14 days of 60-day period)
            start_day = self.gen_config.num_days - random.randint(2, 14)
            self.customers.append(CustomerProfile(
                vpa=self._generate_vpa(customer_idx, "new_"),
                avg_visits_per_week=random.uniform(1, 3),
                avg_amount=random.uniform(30, 80),
                amount_std=random.uniform(10, 25),
                first_visit_day=start_day,
                day_consistency=random.uniform(0.1, 0.3),
                hour_consistency=random.uniform(0.1, 0.3),
            ))
            customer_idx += 1
        
        # 5. CHURNERS - Critical for demo! These 38 customers will stop coming
        for i in range(self.gen_config.num_churners):
            # Churn between day 30 and day 44 (so they're 16-30 days inactive at day 60)
            # Tighter range to ensure most fall in at-risk category
            churn_day = random.randint(32, 44)
            self.customers.append(CustomerProfile(
                vpa=self._generate_vpa(customer_idx, "churn_"),
                avg_visits_per_week=random.uniform(1, 2.5),  # Were regular visitors
                avg_amount=random.uniform(50, 150),  # Higher avg spend (good customers lost)
                amount_std=random.uniform(15, 40),
                first_visit_day=random.randint(0, 15),  # Started early
                will_churn=True,
                churn_after_days=churn_day,
                day_consistency=random.uniform(0.2, 0.4),
                hour_consistency=random.uniform(0.2, 0.4),
            ))
            customer_idx += 1
        
        # 6. One-time visitors (will not count as regulars)
        for i in range(self.gen_config.num_one_timers):
            self.customers.append(CustomerProfile(
                vpa=self._generate_vpa(customer_idx, "once_"),
                avg_visits_per_week=0.05,  # Very rare - effectively once
                avg_amount=random.uniform(20, 60),
                amount_std=random.uniform(5, 15),
                first_visit_day=random.randint(0, self.gen_config.num_days - 1),
            ))
            customer_idx += 1
        
        # 7. PLANTED HABIT PATTERNS
        # Sunday habituals (like #B07 in the demo)
        sunday_customers = random.sample(
            [c for c in self.customers if not c.will_churn and c.avg_visits_per_week >= 0.5],
            min(self.gen_config.num_sunday_habituals, len(self.customers))
        )
        for c in sunday_customers:
            c.preferred_day = 6  # Sunday
            c.day_consistency = 0.70  # 70% visits on Sunday
            c.preferred_hour = 8  # 8 AM
            c.hour_consistency = 0.65
        
        # Morning habituals
        morning_candidates = [c for c in self.customers 
                            if c not in sunday_customers and not c.will_churn 
                            and c.avg_visits_per_week >= 0.5]
        morning_customers = random.sample(
            morning_candidates,
            min(self.gen_config.num_morning_habituals, len(morning_candidates))
        )
        for c in morning_customers:
            c.preferred_hour = random.choice([7, 8, 9])  # 7-9 AM
            c.hour_consistency = 0.65
    
    def _generate_visit_time(self, customer: CustomerProfile, day_offset: int) -> datetime:
        """Generate a specific visit timestamp for a customer on a given day."""
        base_date = self.gen_config.start_date + timedelta(days=day_offset)
        
        # Determine hour
        if customer.preferred_hour and random.random() < customer.hour_consistency:
            # Use preferred hour with some variance
            hour = customer.preferred_hour + random.choice([-1, 0, 0, 0, 1])
            hour = max(self.gen_config.open_hour, min(self.gen_config.close_hour - 1, hour))
        else:
            # Random hour weighted towards peak times
            if random.random() < 0.4:  # 40% chance of peak hours
                if random.random() < 0.5:
                    hour = random.randint(*self.gen_config.morning_peak)
                else:
                    hour = random.randint(*self.gen_config.evening_peak)
            else:
                hour = random.randint(self.gen_config.open_hour, self.gen_config.close_hour - 1)
        
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        
        return base_date.replace(hour=hour, minute=minute, second=second)
    
    def _should_visit_on_day(self, customer: CustomerProfile, day_offset: int) -> bool:
        """Determine if a customer should visit on a given day."""
        # Check if customer has started visiting
        if day_offset < customer.first_visit_day:
            return False
        
        # Check if customer has churned
        if customer.will_churn and customer.churn_after_days:
            if day_offset > customer.churn_after_days:
                return False
        
        # Get day of week
        visit_date = self.gen_config.start_date + timedelta(days=day_offset)
        day_of_week = visit_date.weekday()
        
        # Calculate base probability
        # avg_visits_per_week / 7 = daily probability
        base_prob = customer.avg_visits_per_week / 7.0
        
        # Adjust for preferred day
        if customer.preferred_day is not None:
            if day_of_week == customer.preferred_day:
                # Much higher probability on preferred day
                base_prob = min(0.95, base_prob * (1 + customer.day_consistency * 3))
            else:
                # Lower probability on other days
                base_prob = base_prob * (1 - customer.day_consistency * 0.5)
        
        # Add some variance
        prob = base_prob * random.uniform(1 - customer.visit_variance, 1 + customer.visit_variance)
        
        return random.random() < prob
    
    def _generate_amount(self, customer: CustomerProfile) -> float:
        """Generate a transaction amount for a customer."""
        amount = random.gauss(customer.avg_amount, customer.amount_std)
        # Round to nearest 5 or 10 (realistic for Indian transactions)
        amount = max(10, round(amount / 5) * 5)
        return float(amount)
    
    def generate_all_events(self) -> List[PaymentEvent]:
        """
        Generate all payment events for the simulation period.
        
        Returns:
            List of PaymentEvent objects sorted by timestamp.
        """
        set_seed(self.seed)  # Reset seed for reproducibility
        self.events = []
        
        # Generate events for each day
        for day_offset in range(self.gen_config.num_days):
            for customer in self.customers:
                if self._should_visit_on_day(customer, day_offset):
                    event = PaymentEvent(
                        vpa=customer.vpa,
                        amount=self._generate_amount(customer),
                        timestamp=self._generate_visit_time(customer, day_offset),
                        merchant_id=config.MERCHANT_ID,
                    )
                    self.events.append(event)
        
        # Sort by timestamp
        self.events.sort(key=lambda e: e.timestamp)
        
        return self.events
    
    def generate_events_stream(self) -> Generator[PaymentEvent, None, None]:
        """
        Generate events one at a time (for streaming simulation).
        
        Yields:
            PaymentEvent objects in chronological order.
        """
        if not self.events:
            self.generate_all_events()
        
        for event in self.events:
            yield event
    
    def get_statistics(self) -> dict:
        """
        Get statistics about generated events.
        Useful for verifying demo numbers.
        """
        if not self.events:
            self.generate_all_events()
        
        # Count visits per customer
        visits_per_customer = {}
        for event in self.events:
            visits_per_customer[event.vpa] = visits_per_customer.get(event.vpa, 0) + 1
        
        # Count regulars (2+ visits)
        regulars = {vpa: count for vpa, count in visits_per_customer.items() if count >= 2}
        
        # Analyze churners
        churner_vpas = {c.vpa for c in self.customers if c.will_churn}
        churner_visits = {vpa: visits_per_customer.get(vpa, 0) for vpa in churner_vpas}
        
        # Find last visit dates for each customer
        last_visits = {}
        for event in self.events:
            last_visits[event.vpa] = event.timestamp
        
        # Calculate days since last visit (from simulation end)
        end_date = self.gen_config.end_date
        recency = {}
        for vpa, last_visit in last_visits.items():
            recency[vpa] = (end_date - last_visit).days
        
        # Count at-risk (14-30 days since last visit, was a regular)
        at_risk = [vpa for vpa, days in recency.items() 
                   if 14 <= days <= 30 and visits_per_customer.get(vpa, 0) >= 2]
        
        # Analyze habits
        sunday_visitors = self._analyze_day_habits(6)  # Sunday
        morning_visitors = self._analyze_hour_habits([7, 8, 9])
        
        return {
            "total_events": len(self.events),
            "unique_customers": len(visits_per_customer),
            "regular_customers": len(regulars),  # Target: ~312
            "at_risk_customers": len(at_risk),   # Target: ~38
            "churner_customers": len(churner_vpas),
            "sunday_habituals": len(sunday_visitors),
            "morning_habituals": len(morning_visitors),
            "avg_visits_per_regular": np.mean(list(regulars.values())) if regulars else 0,
            "total_revenue": sum(e.amount for e in self.events),
            "avg_transaction": np.mean([e.amount for e in self.events]) if self.events else 0,
            "simulation_days": self.gen_config.num_days,
            "start_date": self.gen_config.start_date.isoformat(),
            "end_date": self.gen_config.end_date.isoformat(),
        }
    
    def _analyze_day_habits(self, target_day: int, threshold: float = 0.6) -> List[str]:
        """Find customers who visit on a specific day >= threshold of the time."""
        visits_by_customer_day = {}
        for event in self.events:
            vpa = event.vpa
            day = event.timestamp.weekday()
            if vpa not in visits_by_customer_day:
                visits_by_customer_day[vpa] = {}
            visits_by_customer_day[vpa][day] = visits_by_customer_day[vpa].get(day, 0) + 1
        
        habitual = []
        for vpa, day_counts in visits_by_customer_day.items():
            total = sum(day_counts.values())
            if total >= 3:  # Need at least 3 visits to detect habit
                target_count = day_counts.get(target_day, 0)
                if target_count / total >= threshold:
                    habitual.append(vpa)
        
        return habitual
    
    def _analyze_hour_habits(self, target_hours: List[int], threshold: float = 0.6) -> List[str]:
        """Find customers who visit during specific hours >= threshold of the time."""
        visits_by_customer = {}
        for event in self.events:
            vpa = event.vpa
            hour = event.timestamp.hour
            if vpa not in visits_by_customer:
                visits_by_customer[vpa] = {"target": 0, "total": 0}
            visits_by_customer[vpa]["total"] += 1
            if hour in target_hours:
                visits_by_customer[vpa]["target"] += 1
        
        habitual = []
        for vpa, counts in visits_by_customer.items():
            if counts["total"] >= 3:
                if counts["target"] / counts["total"] >= threshold:
                    habitual.append(vpa)
        
        return habitual
    
    def print_summary(self):
        """Print a human-readable summary of the generated data."""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("LoyalPay Synthetic Data Generator Summary")
        print("="*60)
        print(f"\nSimulation Period: {stats['start_date'][:10]} to {stats['end_date'][:10]}")
        print(f"                   ({stats['simulation_days']} days)")
        print(f"\nTransaction Statistics:")
        print(f"  Total Transactions: {stats['total_events']:,}")
        print(f"  Total Revenue:      ₹{stats['total_revenue']:,.0f}")
        print(f"  Avg Transaction:    ₹{stats['avg_transaction']:.0f}")
        print(f"\nCustomer Statistics:")
        print(f"  Unique Customers:   {stats['unique_customers']}")
        print(f"  Regular Customers:  {stats['regular_customers']} (2+ visits)")
        print(f"  At-Risk Customers:  {stats['at_risk_customers']} (14-30 days inactive)")
        print(f"  Avg Visits/Regular: {stats['avg_visits_per_regular']:.1f}")
        print(f"\nDetected Habits:")
        print(f"  Sunday Regulars:    {stats['sunday_habituals']}")
        print(f"  Morning Regulars:   {stats['morning_habituals']}")
        print("="*60)


def create_demo_generator(seed: int = None) -> SyntheticPaymentGenerator:
    """
    Create a generator configured for the demo scenario.
    
    Args:
        seed: Random seed (default: 42 for reproducibility)
    
    Returns:
        Configured SyntheticPaymentGenerator
    """
    return SyntheticPaymentGenerator(
        gen_config=GeneratorConfig(),
        seed=seed or config.RANDOM_SEED
    )


# Convenience function for quick testing
def generate_demo_data() -> tuple[List[PaymentEvent], dict]:
    """
    Generate demo data and return events with statistics.
    
    Returns:
        Tuple of (events list, statistics dict)
    """
    generator = create_demo_generator()
    events = generator.generate_all_events()
    stats = generator.get_statistics()
    return events, stats


if __name__ == "__main__":
    # Quick verification
    print("Generating demo data with seed=42...")
    
    generator = create_demo_generator(seed=42)
    events = generator.generate_all_events()
    generator.print_summary()
    
    # Verify reproducibility
    print("\n\nVerifying reproducibility...")
    generator2 = create_demo_generator(seed=42)
    events2 = generator2.generate_all_events()
    
    assert len(events) == len(events2), "Event counts don't match!"
    for e1, e2 in zip(events[:100], events2[:100]):
        assert e1.vpa == e2.vpa, "VPAs don't match!"
        assert e1.amount == e2.amount, "Amounts don't match!"
        assert e1.timestamp == e2.timestamp, "Timestamps don't match!"
    
    print("✓ Reproducibility verified - same seed produces identical events")
    
    # Show sample events
    print("\n\nSample Events (first 10):")
    print("-" * 80)
    for event in events[:10]:
        print(f"  {event.timestamp.strftime('%Y-%m-%d %H:%M')} | {event.vpa[:25]:<25} | ₹{event.amount:>6.0f}")
    
    # Show a Sunday habitual example
    print("\n\nSample Sunday Habitual Customer Events:")
    print("-" * 80)
    sunday_vpas = generator._analyze_day_habits(6)
    if sunday_vpas:
        sample_vpa = sunday_vpas[0]
        sunday_events = [e for e in events if e.vpa == sample_vpa]
        for event in sunday_events[:8]:
            day_name = event.timestamp.strftime('%A')
            print(f"  {event.timestamp.strftime('%Y-%m-%d %H:%M')} ({day_name}) | ₹{event.amount:>6.0f}")
