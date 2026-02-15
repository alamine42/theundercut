"""Common abstractions for race data providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(slots=True)
class RaceDescriptor:
    season: int
    round: int
    race_name: str
    circuit: str
    slug: str


class RaceDataProvider(ABC):
    """Simple interface for season schedule + race fetchers."""

    name: str

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def fetch_schedule(self, season: int) -> List[RaceDescriptor]:
        ...

    @abstractmethod
    def fetch_weekend(self, season: int, round_number: int) -> dict:
        ...


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider cannot serve a request."""


__all__ = ["RaceDescriptor", "RaceDataProvider", "ProviderUnavailableError"]
