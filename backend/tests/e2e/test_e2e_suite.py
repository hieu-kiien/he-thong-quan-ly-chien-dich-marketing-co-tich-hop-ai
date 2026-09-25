"""MarketFlow AI — Master E2E Test Suite (Tiers 1-4).
Consolidates all 4 Tiers of the Opaque-Box E2E Testing Track:
- Tier 1: Feature Coverage (R1-R6, >=5 test cases per feature)
- Tier 2: Boundary & Corner Cases (R1-R6, >=5 test cases per feature)
- Tier 3: Cross-Feature Combinations (Integration Matrix)
- Tier 4: Real-World Scenarios (Full Agency User Journeys)

Run directly with:
    pytest backend/tests/e2e/test_e2e_suite.py -v --tb=short
"""

from tests.e2e.test_tier1_feature_coverage import (
    TestTier1FeatureCoverageR1,
    TestTier1FeatureCoverageR2,
    TestTier1FeatureCoverageR3,
    TestTier1FeatureCoverageR4,
    TestTier1FeatureCoverageR5,
    TestTier1FeatureCoverageR6,
)
from tests.e2e.test_tier2_boundary_corner import (
    TestTier2BoundaryCornerR1,
    TestTier2BoundaryCornerR2,
    TestTier2BoundaryCornerR3,
    TestTier2BoundaryCornerR4,
    TestTier2BoundaryCornerR5,
    TestTier2BoundaryCornerR6,
)
from tests.e2e.test_tier3_cross_feature import TestTier3CrossFeatureCombinations
from tests.e2e.test_tier4_real_scenarios import TestTier4RealWorldScenarios

__all__ = [
    "TestTier1FeatureCoverageR1",
    "TestTier1FeatureCoverageR2",
    "TestTier1FeatureCoverageR3",
    "TestTier1FeatureCoverageR4",
    "TestTier1FeatureCoverageR5",
    "TestTier1FeatureCoverageR6",
    "TestTier2BoundaryCornerR1",
    "TestTier2BoundaryCornerR2",
    "TestTier2BoundaryCornerR3",
    "TestTier2BoundaryCornerR4",
    "TestTier2BoundaryCornerR5",
    "TestTier2BoundaryCornerR6",
    "TestTier3CrossFeatureCombinations",
    "TestTier4RealWorldScenarios",
]
