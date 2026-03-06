"""Enhanced Strategy Score module.

Provides comprehensive strategy evaluation for F1 races, analyzing:
- Pit timing (undercuts, overcuts, pit window optimization)
- Tire compound selection
- Safety car response
- Weather strategy
"""

from .types import (
    StrategyDecisionType,
    StrategyFactor,
    StrategyDecisionRecord,
    FactorScore,
    StrategyScoreResult,
)
from .position_delta import PositionDeltaAnalyzer
from .pit_timing import PitTimingScorer
from .tire_selection import TireSelectionScorer
from .safety_car import SafetyCarScorer
from .weather import WeatherScorer
from .engine import StrategyScoreEngine, StrategyEngineConfig
from .pit_timing import PitTimingConfig
from .tire_selection import TireSelectionConfig
from .safety_car import SafetyCarConfig
from .weather import WeatherConfig
from .peer_comparison import PeerComparison, PeerComparisonConfig
from .hindsight_simulation import HindsightSimulator, SimulationConfig

__all__ = [
    # Types
    "StrategyDecisionType",
    "StrategyFactor",
    "StrategyDecisionRecord",
    "FactorScore",
    "StrategyScoreResult",
    # Analyzers
    "PositionDeltaAnalyzer",
    "PeerComparison",
    "PeerComparisonConfig",
    "HindsightSimulator",
    "SimulationConfig",
    # Scorers
    "PitTimingScorer",
    "PitTimingConfig",
    "TireSelectionScorer",
    "TireSelectionConfig",
    "SafetyCarScorer",
    "SafetyCarConfig",
    "WeatherScorer",
    "WeatherConfig",
    # Engine
    "StrategyScoreEngine",
    "StrategyEngineConfig",
]
