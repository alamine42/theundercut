"""Provider interfaces shareable between ingestion + grading layers."""

from .laps import (
    LapDataProvider,
    FastF1LapProvider,
    OpenF1LapProvider,
    resolve_lap_provider,
    ProviderResult,
)

__all__ = [
    "LapDataProvider",
    "FastF1LapProvider",
    "OpenF1LapProvider",
    "resolve_lap_provider",
    "ProviderResult",
]
