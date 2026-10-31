"""
LoyalPay Configuration
Manages seed control for reproducible demo numbers and global settings.

Demo Numbers (with RANDOM_SEED=42):
- 312 regular customers
- 38 at-risk customers
- 21 customers return after campaign
- ₹3,200 recovered revenue
- ₹420 cashback spent
- 7.6x ROI
"""

import os
import random
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Global configuration for LoyalPay."""
    
    # Seed control for reproducibility
    RANDOM_SEED: int = 42
    
    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    MODELS_DIR: Path = PROJECT_ROOT / "models"
    
    # Database
    DATABASE_PATH: Path = DATA_DIR / "loyalpay.db"
    
    # Privacy - HMAC secret key for hashing VPAs
    HMAC_SECRET_KEY: str = "loyalpay_demo_secret_key_2024"
    
    # Merchant info (demo)
    MERCHANT_ID: str = "ramesh_kirana"
    MERCHANT_NAME: str = "Ramesh Kirana Store"
    
    # Segmentation thresholds
    CHAMPION_MIN_VISITS: int = 15
    CHAMPION_MAX_RECENCY_DAYS: int = 3
    LOYAL_MAX_RECENCY_DAYS: int = 7
    NEW_MAX_AGE_DAYS: int = 14
    AT_RISK_MIN_RECENCY_DAYS: int = 14
    AT_RISK_MAX_RECENCY_DAYS: int = 30
    LOST_MIN_RECENCY_DAYS: int = 30
    
    # Regular customer threshold
    MIN_VISITS_FOR_REGULAR: int = 2
    
    # Habit detection thresholds
    HABIT_DAY_THRESHOLD: float = 0.60  # 60% visits on same day
    HABIT_HOUR_THRESHOLD: float = 0.60  # 60% visits in same hour
    
    # Churn model
    CHURN_OBSERVATION_WINDOW_DAYS: int = 21
    
    # Campaign defaults
    DEFAULT_CASHBACK_PERCENT: float = 0.15  # 15% of avg basket
    DEFAULT_CAMPAIGN_BUDGET: float = 500.0  # ₹500
    EXPECTED_REDEMPTION_RATE: float = 0.60  # 60% conversion
    
    # API
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    
    def __post_init__(self):
        """Ensure directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()


def set_seed(seed: int = None) -> int:
    """
    Set random seed for reproducibility across all libraries.
    
    Args:
        seed: Seed value. If None, uses config.RANDOM_SEED.
        
    Returns:
        The seed value that was set.
    """
    if seed is None:
        seed = config.RANDOM_SEED
    
    random.seed(seed)
    np.random.seed(seed)
    
    # Note: LightGBM uses seed in training params, not global seed
    # It will be set when training the churn model in Phase 4
    
    return seed


def reset_seed() -> int:
    """Reset seed to default config value."""
    return set_seed(config.RANDOM_SEED)


# Initialize seed on module load
set_seed()


if __name__ == "__main__":
    # Quick verification
    print(f"Config loaded:")
    print(f"  RANDOM_SEED: {config.RANDOM_SEED}")
    print(f"  PROJECT_ROOT: {config.PROJECT_ROOT}")
    print(f"  DATA_DIR: {config.DATA_DIR}")
    print(f"  DATABASE_PATH: {config.DATABASE_PATH}")
    
    # Test seed reproducibility
    set_seed(42)
    nums1 = [random.randint(1, 100) for _ in range(5)]
    set_seed(42)
    nums2 = [random.randint(1, 100) for _ in range(5)]
    
    assert nums1 == nums2, "Seed not producing reproducible results!"
    print(f"\n✓ Seed reproducibility verified: {nums1}")
