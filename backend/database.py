"""
LoyalPay Database Module

Handles:
- SQLite schema (Customers, Payments, Campaigns, CampaignTargets)
- HMAC-SHA256 hashing of VPA → token → label (#A12)
- Event ingestion with privacy preservation

Privacy Design:
- VPA is hashed using HMAC-SHA256 with a secret key
- Hash is deterministic (same VPA → same hash)
- Hash is irreversible (cannot recover VPA from hash)
- Customer label (#A12) is derived from hash for display
"""

import hashlib
import hmac
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager

from backend.config import config
from backend.generator import PaymentEvent


@dataclass
class Customer:
    """Customer record with anonymized identity."""
    id: int
    token: str  # HMAC-SHA256 hash of VPA
    label: str  # Human-readable label like #A12
    opt_in: bool  # Whether customer has opted into promotions
    created_at: datetime
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "token": self.token,
            "label": self.label,
            "opt_in": self.opt_in,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class Payment:
    """Payment/visit record."""
    id: int
    customer_id: int
    amount: float
    timestamp: datetime
    merchant_id: str
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "merchant_id": self.merchant_id,
        }


@dataclass
class Campaign:
    """Marketing campaign record."""
    id: int
    name: str
    cashback_amount: float
    budget: float
    spent: float
    status: str  # 'active', 'completed', 'cancelled'
    created_at: datetime
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "cashback_amount": self.cashback_amount,
            "budget": self.budget,
            "spent": self.spent,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class CampaignTarget:
    """Campaign target/recipient record."""
    id: int
    campaign_id: int
    customer_id: int
    sent_at: datetime
    redeemed: bool
    redeemed_at: Optional[datetime]
    redemption_amount: Optional[float]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "customer_id": self.customer_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "redeemed": self.redeemed,
            "redeemed_at": self.redeemed_at.isoformat() if self.redeemed_at else None,
            "redemption_amount": self.redemption_amount,
        }


class PrivacyHasher:
    """
    HMAC-SHA256 based privacy hasher for VPAs.
    
    Properties:
    - Deterministic: Same VPA always produces same hash
    - Irreversible: Cannot recover VPA from hash
    - Secure: Uses HMAC with secret key
    """
    
    def __init__(self, secret_key: str = None):
        self.secret_key = (secret_key or config.HMAC_SECRET_KEY).encode('utf-8')
        self._label_counter = 0
        self._token_to_label: Dict[str, str] = {}
    
    def hash_vpa(self, vpa: str) -> str:
        """
        Hash a VPA using HMAC-SHA256.
        
        Args:
            vpa: Virtual Payment Address (e.g., rahul123@paytm)
            
        Returns:
            Hex-encoded hash string
        """
        message = vpa.encode('utf-8')
        return hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()
    
    def generate_label(self, token: str) -> str:
        """
        Generate a human-readable label for a token.
        
        Format: #<letter><number> (e.g., #A12, #B07, #F08)
        
        Args:
            token: The hashed token
            
        Returns:
            Human-readable label
        """
        if token in self._token_to_label:
            return self._token_to_label[token]
        
        # Generate new label
        self._label_counter += 1
        
        # Convert counter to letter + number format
        # A01-A99, B01-B99, etc.
        letter_idx = (self._label_counter - 1) // 99
        number = ((self._label_counter - 1) % 99) + 1
        
        if letter_idx < 26:
            letter = chr(ord('A') + letter_idx)
        else:
            # For > 2574 customers, use AA, AB, etc.
            letter = chr(ord('A') + letter_idx // 26) + chr(ord('A') + letter_idx % 26)
        
        label = f"#{letter}{number:02d}"
        self._token_to_label[token] = label
        
        return label
    
    def reset_labels(self):
        """Reset label counter (for testing/demo reset)."""
        self._label_counter = 0
        self._token_to_label.clear()


class Database:
    """
    SQLite database manager for LoyalPay.
    
    Tables:
    - customers: Hashed customer identities
    - payments: Transaction records
    - campaigns: Marketing campaigns
    - campaign_targets: Campaign recipients and redemptions
    - redemptions: Completed redemption records with payment details
    """
    
    SCHEMA = """
    -- Customers table: stores anonymized customer identities
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,           -- HMAC-SHA256 hash of VPA
        label TEXT UNIQUE NOT NULL,           -- Human-readable label (#A12)
        opt_in INTEGER DEFAULT 1,             -- 1=opted in, 0=opted out
        created_at TEXT NOT NULL              -- ISO timestamp
    );
    
    -- Payments table: transaction records
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        timestamp TEXT NOT NULL,              -- ISO timestamp
        merchant_id TEXT NOT NULL,
        is_redemption INTEGER DEFAULT 0,      -- 1 if this payment was a redemption
        campaign_id INTEGER,                  -- Associated campaign if redemption
        discount_amount REAL DEFAULT 0,       -- Discount applied
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
    );
    
    -- Campaigns table: marketing campaigns
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cashback_amount REAL NOT NULL,        -- Cashback percentage
        budget REAL NOT NULL,                 -- Total budget
        spent REAL DEFAULT 0,                 -- Amount spent so far
        status TEXT DEFAULT 'active',         -- active, completed, cancelled
        created_at TEXT NOT NULL
    );
    
    -- Campaign targets: who received offers and redemption status
    CREATE TABLE IF NOT EXISTS campaign_targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        sent_at TEXT NOT NULL,
        redeemed INTEGER DEFAULT 0,           -- 1=redeemed, 0=not redeemed
        redeemed_at TEXT,                     -- When redeemed (if applicable)
        redemption_amount REAL,               -- Original transaction amount at redemption
        discount_amount REAL,                 -- Discount given (cashback)
        final_amount REAL,                    -- Final amount after discount
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    
    -- Customer coupon history: tracks when each customer last received a coupon
    -- Used to enforce the 7-payment rule for spam prevention
    CREATE TABLE IF NOT EXISTS customer_coupon_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        last_coupon_sent_at TEXT NOT NULL,    -- When last coupon was sent
        payments_since_coupon INTEGER DEFAULT 0,  -- Payments since last coupon
        last_payment_at TEXT,                 -- Last payment timestamp
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        UNIQUE(customer_id)
    );
    
    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);
    CREATE INDEX IF NOT EXISTS idx_payments_timestamp ON payments(timestamp);
    CREATE INDEX IF NOT EXISTS idx_campaign_targets_campaign ON campaign_targets(campaign_id);
    CREATE INDEX IF NOT EXISTS idx_campaign_targets_customer ON campaign_targets(customer_id);
    CREATE INDEX IF NOT EXISTS idx_coupon_history_customer ON customer_coupon_history(customer_id);
    """
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.hasher = PrivacyHasher()
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.executescript(self.SCHEMA)
    
    @contextmanager
    def _connect(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def reset(self):
        """Reset database (delete all data, keep schema)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM campaign_targets")
            conn.execute("DELETE FROM campaigns")
            conn.execute("DELETE FROM payments")
            conn.execute("DELETE FROM customers")
            # Reset auto-increment counters
            conn.execute("DELETE FROM sqlite_sequence")
        self.hasher.reset_labels()
    
    def drop_all(self):
        """Drop all tables (for complete reset)."""
        with self._connect() as conn:
            conn.execute("DROP TABLE IF EXISTS campaign_targets")
            conn.execute("DROP TABLE IF EXISTS campaigns")
            conn.execute("DROP TABLE IF EXISTS payments")
            conn.execute("DROP TABLE IF EXISTS customers")
        self.hasher.reset_labels()
        self._ensure_schema()
    
    # ==================== Customer Operations ====================
    
    def get_or_create_customer(self, vpa: str) -> Customer:
        """
        Get existing customer or create new one from VPA.
        
        The VPA is hashed - we never store the raw VPA.
        
        Args:
            vpa: Virtual Payment Address
            
        Returns:
            Customer object
        """
        token = self.hasher.hash_vpa(vpa)
        
        with self._connect() as conn:
            # Try to find existing customer
            row = conn.execute(
                "SELECT * FROM customers WHERE token = ?",
                (token,)
            ).fetchone()
            
            if row:
                return Customer(
                    id=row['id'],
                    token=row['token'],
                    label=row['label'],
                    opt_in=bool(row['opt_in']),
                    created_at=datetime.fromisoformat(row['created_at']),
                )
            
            # Create new customer
            label = self.hasher.generate_label(token)
            now = datetime.now().isoformat()
            
            cursor = conn.execute(
                "INSERT INTO customers (token, label, opt_in, created_at) VALUES (?, ?, 1, ?)",
                (token, label, now)
            )
            
            return Customer(
                id=cursor.lastrowid,
                token=token,
                label=label,
                opt_in=True,
                created_at=datetime.fromisoformat(now),
            )
    
    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """Get customer by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE id = ?",
                (customer_id,)
            ).fetchone()
            
            if row:
                return Customer(
                    id=row['id'],
                    token=row['token'],
                    label=row['label'],
                    opt_in=bool(row['opt_in']),
                    created_at=datetime.fromisoformat(row['created_at']),
                )
            return None
    
    def get_customer_by_label(self, label: str) -> Optional[Customer]:
        """Get customer by label (e.g., #A12)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE label = ?",
                (label,)
            ).fetchone()
            
            if row:
                return Customer(
                    id=row['id'],
                    token=row['token'],
                    label=row['label'],
                    opt_in=bool(row['opt_in']),
                    created_at=datetime.fromisoformat(row['created_at']),
                )
            return None
    
    def get_all_customers(self) -> List[Customer]:
        """Get all customers."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM customers ORDER BY id").fetchall()
            return [
                Customer(
                    id=row['id'],
                    token=row['token'],
                    label=row['label'],
                    opt_in=bool(row['opt_in']),
                    created_at=datetime.fromisoformat(row['created_at']),
                )
                for row in rows
            ]
    
    def update_customer_opt_in(self, customer_id: int, opt_in: bool):
        """Update customer opt-in status."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE customers SET opt_in = ? WHERE id = ?",
                (1 if opt_in else 0, customer_id)
            )
    
    # ==================== Payment Operations ====================
    
    def ingest_payment(self, event: PaymentEvent) -> tuple[Customer, Payment]:
        """
        Ingest a payment event.
        
        This is the main entry point for processing transactions.
        The VPA is hashed and stored anonymously.
        
        Args:
            event: PaymentEvent from the generator
            
        Returns:
            Tuple of (Customer, Payment) objects
        """
        # Get or create customer (handles hashing)
        customer = self.get_or_create_customer(event.vpa)
        
        # Record the payment
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO payments (customer_id, amount, timestamp, merchant_id)
                   VALUES (?, ?, ?, ?)""",
                (customer.id, event.amount, event.timestamp.isoformat(), event.merchant_id)
            )
            
            payment = Payment(
                id=cursor.lastrowid,
                customer_id=customer.id,
                amount=event.amount,
                timestamp=event.timestamp,
                merchant_id=event.merchant_id,
            )
        
        return customer, payment
    
    def ingest_payments_batch(self, events: List[PaymentEvent]) -> int:
        """
        Batch ingest multiple payment events.
        
        More efficient than ingesting one at a time.
        
        Args:
            events: List of PaymentEvents
            
        Returns:
            Number of payments ingested
        """
        count = 0
        for event in events:
            self.ingest_payment(event)
            count += 1
        return count
    
    def get_customer_payments(self, customer_id: int) -> List[Payment]:
        """Get all payments for a customer."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM payments WHERE customer_id = ? ORDER BY timestamp",
                (customer_id,)
            ).fetchall()
            
            return [
                Payment(
                    id=row['id'],
                    customer_id=row['customer_id'],
                    amount=row['amount'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    merchant_id=row['merchant_id'],
                )
                for row in rows
            ]
    
    def get_visit_counts(self) -> Dict[int, int]:
        """
        Get visit counts per customer.
        
        Returns:
            Dict mapping customer_id to visit count
        """
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT customer_id, COUNT(*) as visit_count
                   FROM payments
                   GROUP BY customer_id"""
            ).fetchall()
            
            return {row['customer_id']: row['visit_count'] for row in rows}
    
    def get_customer_stats(self) -> List[Dict[str, Any]]:
        """
        Get comprehensive stats for each customer.
        
        Returns:
            List of dicts with customer stats including:
            - label, visit_count, total_spent, avg_spent, first_visit, last_visit
        """
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT 
                       c.id,
                       c.label,
                       c.opt_in,
                       COUNT(p.id) as visit_count,
                       COALESCE(SUM(p.amount), 0) as total_spent,
                       COALESCE(AVG(p.amount), 0) as avg_spent,
                       MIN(p.timestamp) as first_visit,
                       MAX(p.timestamp) as last_visit
                   FROM customers c
                   LEFT JOIN payments p ON c.id = p.customer_id
                   GROUP BY c.id
                   ORDER BY visit_count DESC"""
            ).fetchall()
            
            return [
                {
                    "customer_id": row['id'],
                    "label": row['label'],
                    "opt_in": bool(row['opt_in']),
                    "visit_count": row['visit_count'],
                    "total_spent": row['total_spent'],
                    "avg_spent": row['avg_spent'],
                    "first_visit": row['first_visit'],
                    "last_visit": row['last_visit'],
                }
                for row in rows
            ]
    
    # ==================== Campaign Operations ====================
    
    def create_campaign(
        self,
        name: str,
        cashback_amount: float,
        budget: float,
        target_customer_ids: List[int]
    ) -> Campaign:
        """
        Create a new campaign and assign targets.
        
        Args:
            name: Campaign name
            cashback_amount: Cashback per redemption
            budget: Total budget
            target_customer_ids: List of customer IDs to target
            
        Returns:
            Created Campaign object
        """
        now = datetime.now().isoformat()
        
        with self._connect() as conn:
            # Create campaign
            cursor = conn.execute(
                """INSERT INTO campaigns (name, cashback_amount, budget, status, created_at)
                   VALUES (?, ?, ?, 'active', ?)""",
                (name, cashback_amount, budget, now)
            )
            campaign_id = cursor.lastrowid
            
            # Add targets and update coupon history
            for customer_id in target_customer_ids:
                conn.execute(
                    """INSERT INTO campaign_targets (campaign_id, customer_id, sent_at)
                       VALUES (?, ?, ?)""",
                    (campaign_id, customer_id, now)
                )
                
                # Update coupon history for this customer
                conn.execute(
                    """INSERT INTO customer_coupon_history (customer_id, last_coupon_sent_at, payments_since_coupon)
                       VALUES (?, ?, 0)
                       ON CONFLICT(customer_id) DO UPDATE SET 
                           last_coupon_sent_at = excluded.last_coupon_sent_at,
                           payments_since_coupon = 0""",
                    (customer_id, now)
                )
            
            return Campaign(
                id=campaign_id,
                name=name,
                cashback_amount=cashback_amount,
                budget=budget,
                spent=0,
                status='active',
                created_at=datetime.fromisoformat(now),
            )
    
    def check_customer_coupon_eligibility(self, customer_id: int, min_payments: int = 7) -> Dict[str, Any]:
        """
        Check if a customer is eligible to receive a new coupon.
        
        Rule: Customer must have made at least min_payments (default 7) since their last coupon.
        
        Args:
            customer_id: Customer to check
            min_payments: Minimum payments required since last coupon
            
        Returns:
            Dict with 'eligible' bool and 'reason' string
        """
        with self._connect() as conn:
            history = conn.execute(
                "SELECT * FROM customer_coupon_history WHERE customer_id = ?",
                (customer_id,)
            ).fetchone()
            
            if not history:
                # Never received a coupon, eligible
                return {"eligible": True, "reason": "No previous coupon sent", "payments_since": None}
            
            payments_since = history['payments_since_coupon']
            
            if payments_since >= min_payments:
                return {
                    "eligible": True, 
                    "reason": f"Made {payments_since} payments since last coupon",
                    "payments_since": payments_since
                }
            else:
                return {
                    "eligible": False,
                    "reason": f"Only {payments_since}/{min_payments} payments since last coupon",
                    "payments_since": payments_since,
                    "payments_needed": min_payments - payments_since
                }
    
    def get_eligible_customers_for_coupon(self, customer_ids: List[int], min_payments: int = 7) -> List[Dict[str, Any]]:
        """
        Filter a list of customers to only those eligible for coupons.
        
        Args:
            customer_ids: List of customer IDs to check
            min_payments: Minimum payments required
            
        Returns:
            List of dicts with customer_id, eligible, and reason
        """
        results = []
        for cid in customer_ids:
            eligibility = self.check_customer_coupon_eligibility(cid, min_payments)
            results.append({
                "customer_id": cid,
                **eligibility
            })
        return results
    
    def redeem_campaign_offer(
        self,
        campaign_id: int,
        customer_id: int,
        redemption_amount: float
    ) -> Dict[str, Any]:
        """
        Record a campaign redemption with payment details.
        
        Args:
            campaign_id: Campaign ID
            customer_id: Customer who redeemed
            redemption_amount: Original transaction amount
            
        Returns:
            Dict with success status and redemption details
        """
        now = datetime.now().isoformat()
        
        with self._connect() as conn:
            # Find the target
            target = conn.execute(
                """SELECT * FROM campaign_targets
                   WHERE campaign_id = ? AND customer_id = ? AND redeemed = 0""",
                (campaign_id, customer_id)
            ).fetchone()
            
            if not target:
                # Check if already redeemed
                already_redeemed = conn.execute(
                    """SELECT * FROM campaign_targets
                       WHERE campaign_id = ? AND customer_id = ? AND redeemed = 1""",
                    (campaign_id, customer_id)
                ).fetchone()
                
                if already_redeemed:
                    return {"success": False, "error": "already_redeemed", "message": "This offer has already been redeemed"}
                return {"success": False, "error": "not_found", "message": "Offer not found"}
            
            # Get campaign for cashback amount
            campaign = conn.execute(
                "SELECT * FROM campaigns WHERE id = ?",
                (campaign_id,)
            ).fetchone()
            
            if not campaign or campaign['status'] != 'active':
                return {"success": False, "error": "campaign_inactive", "message": "Campaign is not active"}
            
            # Calculate discount
            cashback_percent = campaign['cashback_amount']  # This is stored as percentage
            discount_amount = round(redemption_amount * (cashback_percent / 100), 2)
            final_amount = round(redemption_amount - discount_amount, 2)
            
            # Check budget
            new_spent = campaign['spent'] + discount_amount
            if new_spent > campaign['budget']:
                return {"success": False, "error": "budget_exceeded", "message": "Campaign budget exceeded"}
            
            # Record redemption with all details
            conn.execute(
                """UPDATE campaign_targets
                   SET redeemed = 1, redeemed_at = ?, redemption_amount = ?, 
                       discount_amount = ?, final_amount = ?
                   WHERE id = ?""",
                (now, redemption_amount, discount_amount, final_amount, target['id'])
            )
            
            # Update campaign spent
            conn.execute(
                "UPDATE campaigns SET spent = ? WHERE id = ?",
                (new_spent, campaign_id)
            )
            
            # Record this as a payment (redemption payment)
            cursor = conn.execute(
                """INSERT INTO payments (customer_id, amount, timestamp, merchant_id, is_redemption, campaign_id, discount_amount)
                   VALUES (?, ?, ?, 'ramesh_kirana', 1, ?, ?)""",
                (customer_id, final_amount, now, campaign_id, discount_amount)
            )
            
            # Update customer coupon history - increment payments since coupon
            # (This payment counts towards next coupon eligibility)
            conn.execute(
                """UPDATE customer_coupon_history 
                   SET payments_since_coupon = payments_since_coupon + 1,
                       last_payment_at = ?
                   WHERE customer_id = ?""",
                (now, customer_id)
            )
            
            # Get customer label for response
            customer = conn.execute("SELECT label FROM customers WHERE id = ?", (customer_id,)).fetchone()
            
            return {
                "success": True,
                "redemption": {
                    "customer_id": customer_id,
                    "customer_label": customer['label'] if customer else f"#{customer_id}",
                    "campaign_id": campaign_id,
                    "original_amount": redemption_amount,
                    "discount_percent": cashback_percent,
                    "discount_amount": discount_amount,
                    "final_amount": final_amount,
                    "redeemed_at": now,
                    "payment_id": cursor.lastrowid
                }
            }
    
    def get_campaign(self, campaign_id: int) -> Optional[Campaign]:
        """Get campaign by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM campaigns WHERE id = ?",
                (campaign_id,)
            ).fetchone()
            
            if row:
                return Campaign(
                    id=row['id'],
                    name=row['name'],
                    cashback_amount=row['cashback_amount'],
                    budget=row['budget'],
                    spent=row['spent'],
                    status=row['status'],
                    created_at=datetime.fromisoformat(row['created_at']),
                )
            return None
    
    def get_active_campaigns(self) -> List[Campaign]:
        """Get all active campaigns."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM campaigns WHERE status = 'active'"
            ).fetchall()
            
            return [
                Campaign(
                    id=row['id'],
                    name=row['name'],
                    cashback_amount=row['cashback_amount'],
                    budget=row['budget'],
                    spent=row['spent'],
                    status=row['status'],
                    created_at=datetime.fromisoformat(row['created_at']),
                )
                for row in rows
            ]
    
    def get_campaign_roi(self, campaign_id: int) -> Dict[str, Any]:
        """
        Calculate ROI metrics for a campaign.
        
        Returns:
            Dict with targets_count, redemptions_count, cashback_spent,
            revenue_recovered, roi_multiple
        """
        with self._connect() as conn:
            campaign = conn.execute(
                "SELECT * FROM campaigns WHERE id = ?",
                (campaign_id,)
            ).fetchone()
            
            if not campaign:
                return {}
            
            targets = conn.execute(
                """SELECT 
                       COUNT(*) as total_targets,
                       SUM(redeemed) as redemptions,
                       COALESCE(SUM(redemption_amount), 0) as revenue
                   FROM campaign_targets
                   WHERE campaign_id = ?""",
                (campaign_id,)
            ).fetchone()
            
            cashback_spent = campaign['spent']
            revenue = targets['revenue'] or 0
            
            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign['name'],
                "targets_count": targets['total_targets'],
                "redemptions_count": targets['redemptions'] or 0,
                "cashback_spent": cashback_spent,
                "revenue_recovered": revenue,
                "roi_multiple": round(revenue / cashback_spent, 1) if cashback_spent > 0 else 0,
            }
    
    def get_customer_active_offers(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get active (unredeemed) offers for a customer."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT ct.*, c.name as campaign_name, c.cashback_amount
                   FROM campaign_targets ct
                   JOIN campaigns c ON ct.campaign_id = c.id
                   WHERE ct.customer_id = ? AND ct.redeemed = 0 AND c.status = 'active'""",
                (customer_id,)
            ).fetchall()
            
            return [
                {
                    "campaign_id": row['campaign_id'],
                    "campaign_name": row['campaign_name'],
                    "cashback_amount": row['cashback_amount'],
                    "sent_at": row['sent_at'],
                }
                for row in rows
            ]
    
    def get_recent_redemptions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent redemptions for merchant dashboard."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT ct.*, c.label as customer_label, camp.name as campaign_name, camp.cashback_amount as percent
                   FROM campaign_targets ct
                   JOIN customers c ON ct.customer_id = c.id
                   JOIN campaigns camp ON ct.campaign_id = camp.id
                   WHERE ct.redeemed = 1
                   ORDER BY ct.redeemed_at DESC
                   LIMIT ?""",
                (limit,)
            ).fetchall()
            
            return [
                {
                    "customer_id": row['customer_id'],
                    "customer_label": row['customer_label'],
                    "campaign_id": row['campaign_id'],
                    "campaign_name": row['campaign_name'],
                    "original_amount": row['redemption_amount'],
                    "discount_percent": row['percent'],
                    "discount_amount": row['discount_amount'],
                    "final_amount": row['final_amount'],
                    "redeemed_at": row['redeemed_at'],
                }
                for row in rows
            ]
    
    def record_regular_payment(self, customer_id: int, amount: float):
        """
        Record a regular payment (non-redemption) and update coupon history.
        
        This increments the payments_since_coupon counter.
        """
        now = datetime.now().isoformat()
        
        with self._connect() as conn:
            # Record the payment
            conn.execute(
                """INSERT INTO payments (customer_id, amount, timestamp, merchant_id, is_redemption)
                   VALUES (?, ?, ?, 'ramesh_kirana', 0)""",
                (customer_id, amount, now)
            )
            
            # Update or create coupon history
            existing = conn.execute(
                "SELECT * FROM customer_coupon_history WHERE customer_id = ?",
                (customer_id,)
            ).fetchone()
            
            if existing:
                conn.execute(
                    """UPDATE customer_coupon_history 
                       SET payments_since_coupon = payments_since_coupon + 1,
                           last_payment_at = ?
                       WHERE customer_id = ?""",
                    (now, customer_id)
                )
            else:
                # First payment, no coupon history yet
                conn.execute(
                    """INSERT INTO customer_coupon_history (customer_id, last_coupon_sent_at, payments_since_coupon, last_payment_at)
                       VALUES (?, ?, 1, ?)""",
                    (customer_id, now, now)
                )
    
    def get_campaign_stats_for_merchant(self) -> Dict[str, Any]:
        """Get campaign statistics for merchant dashboard."""
        with self._connect() as conn:
            # Total campaigns
            total = conn.execute("SELECT COUNT(*) as count FROM campaigns").fetchone()['count']
            
            # Active campaigns
            active = conn.execute(
                "SELECT COUNT(*) as count FROM campaigns WHERE status = 'active'"
            ).fetchone()['count']
            
            # Total redemptions
            redemptions = conn.execute(
                "SELECT COUNT(*) as count, SUM(discount_amount) as total_discount, SUM(final_amount) as total_revenue FROM campaign_targets WHERE redeemed = 1"
            ).fetchone()
            
            # Offers sent vs redeemed
            targets = conn.execute(
                "SELECT COUNT(*) as sent, SUM(redeemed) as redeemed FROM campaign_targets"
            ).fetchone()
            
            return {
                "total_campaigns": total,
                "active_campaigns": active,
                "total_offers_sent": targets['sent'] or 0,
                "total_redemptions": redemptions['count'] or 0,
                "redemption_rate": round((targets['redeemed'] or 0) / (targets['sent'] or 1) * 100, 1),
                "total_discount_given": round(redemptions['total_discount'] or 0, 2),
                "total_revenue_from_redemptions": round(redemptions['total_revenue'] or 0, 2),
            }


# Convenience function
def create_database(db_path: Path = None) -> Database:
    """Create and return a Database instance."""
    return Database(db_path)


if __name__ == "__main__":
    # Quick verification
    from backend.generator import create_demo_generator
    
    print("Testing Database Module...")
    print("=" * 60)
    
    # Create fresh database
    db = Database()
    db.drop_all()
    
    # Test hashing
    hasher = PrivacyHasher()
    vpa1 = "rahul123@paytm"
    hash1 = hasher.hash_vpa(vpa1)
    hash2 = hasher.hash_vpa(vpa1)
    
    print(f"\nPrivacy Hashing Test:")
    print(f"  VPA: {vpa1}")
    print(f"  Hash: {hash1[:16]}...{hash1[-8:]}")
    print(f"  Same hash twice: {hash1 == hash2} ✓")
    print(f"  Label: {hasher.generate_label(hash1)}")
    
    # Test ingestion
    print(f"\nIngesting sample events...")
    generator = create_demo_generator(seed=42)
    events = generator.generate_all_events()
    
    # Ingest first 100 events
    for event in events[:100]:
        db.ingest_payment(event)
    
    # Check visit counts
    visit_counts = db.get_visit_counts()
    customer_stats = db.get_customer_stats()
    
    print(f"\nDatabase Stats:")
    print(f"  Unique customers: {len(visit_counts)}")
    print(f"  Total payments: {sum(visit_counts.values())}")
    
    print(f"\nTop 5 Customers by Visits:")
    for stat in customer_stats[:5]:
        print(f"  {stat['label']}: {stat['visit_count']} visits, ₹{stat['avg_spent']:.0f} avg")
    
    # Test same VPA → same customer
    print(f"\nDeterministic Test:")
    c1 = db.get_or_create_customer("test_vpa@paytm")
    c2 = db.get_or_create_customer("test_vpa@paytm")
    print(f"  Same VPA → Same customer ID: {c1.id == c2.id} ✓")
    print(f"  Same VPA → Same label: {c1.label == c2.label} ✓")
    
    print("\n" + "=" * 60)
    print("Database module tests passed! ✓")
