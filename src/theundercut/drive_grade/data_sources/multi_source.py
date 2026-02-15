"""Orchestrates fetching race data using multiple providers with fallbacks."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List, Sequence

from .base import RaceDataProvider, RaceDescriptor


logger = logging.getLogger(__name__)


class MultiSourceFetcher:
    """Try providers in priority order for schedules and race detail."""

    def __init__(self, providers: Sequence[RaceDataProvider]):
        self.providers = list(providers)

    def available_providers(self) -> List[RaceDataProvider]:
        return [provider for provider in self.providers if provider.is_available()]

    def fetch_schedule(self, season: int) -> List[RaceDescriptor]:
        last_error: Exception | None = None
        for provider in self.available_providers():
            try:
                schedule = provider.fetch_schedule(season)
                if schedule:
                    logger.info("Using schedule from %s", provider.name)
                    return schedule
            except Exception as exc:  # pragma: no cover - log + fallback
                logger.warning("Provider %s schedule failed: %s", provider.name, exc)
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("No providers available to fetch schedule")

    def fetch_race(self, season: int, round_number: int) -> dict:
        last_error: Exception | None = None
        for provider in self.available_providers():
            try:
                return provider.fetch_weekend(season, round_number)
            except Exception as exc:
                logger.warning(
                    "Provider %s failed for season=%s round=%s: %s",
                    provider.name,
                    season,
                    round_number,
                    exc,
                )
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("No providers available to fetch race data")


__all__ = ["MultiSourceFetcher"]
