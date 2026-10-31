"""
Tests for configuration and seed control.
"""

import random
import numpy as np
import pytest


def test_seed_reproducibility():
    """Verify that setting the same seed produces identical random sequences."""
    from backend.config import set_seed
    
    # First sequence
    set_seed(42)
    random_nums_1 = [random.randint(1, 1000) for _ in range(10)]
    numpy_nums_1 = np.random.randint(1, 1000, size=10).tolist()
    
    # Second sequence with same seed
    set_seed(42)
    random_nums_2 = [random.randint(1, 1000) for _ in range(10)]
    numpy_nums_2 = np.random.randint(1, 1000, size=10).tolist()
    
    assert random_nums_1 == random_nums_2, "random module not reproducible"
    assert numpy_nums_1 == numpy_nums_2, "numpy not reproducible"


def test_different_seeds_produce_different_results():
    """Verify that different seeds produce different sequences."""
    from backend.config import set_seed
    
    set_seed(42)
    nums_42 = [random.randint(1, 1000) for _ in range(10)]
    
    set_seed(123)
    nums_123 = [random.randint(1, 1000) for _ in range(10)]
    
    assert nums_42 != nums_123, "Different seeds should produce different results"


def test_config_defaults():
    """Verify configuration defaults are set correctly."""
    from backend.config import config
    
    assert config.RANDOM_SEED == 42
    assert config.MIN_VISITS_FOR_REGULAR == 2
    assert config.CHAMPION_MIN_VISITS == 15
    assert config.AT_RISK_MIN_RECENCY_DAYS == 14
    assert config.AT_RISK_MAX_RECENCY_DAYS == 30
    assert config.LOST_MIN_RECENCY_DAYS == 30
    assert config.DEFAULT_CASHBACK_PERCENT == 0.15
    assert config.DEFAULT_CAMPAIGN_BUDGET == 500.0


def test_directories_exist():
    """Verify that required directories are created."""
    from backend.config import config
    
    assert config.DATA_DIR.exists(), "Data directory should exist"
    assert config.MODELS_DIR.exists(), "Models directory should exist"


def test_reset_seed():
    """Verify reset_seed returns to default seed."""
    from backend.config import set_seed, reset_seed, config
    
    # Change seed
    set_seed(999)
    _ = [random.randint(1, 100) for _ in range(5)]
    
    # Reset and verify
    returned_seed = reset_seed()
    assert returned_seed == config.RANDOM_SEED
    
    # Verify it's actually reset by comparing sequences
    reset_seed()
    nums1 = [random.randint(1, 100) for _ in range(5)]
    reset_seed()
    nums2 = [random.randint(1, 100) for _ in range(5)]
    
    assert nums1 == nums2
