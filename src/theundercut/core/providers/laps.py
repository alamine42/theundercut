from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, Type

import httpx
import pandas as pd

from theundercut.config import get_settings

try:  # pragma: no cover - optional dependency
    import fastf1  # type: ignore
except Exception:  # pragma: no cover - e.g., during tests without fastf1
    fastf1 = None  # type: ignore


settings = get_settings()
DEFAULT_FASTF1_CACHE = settings.fastf1_cache_dir
OPENF1_API = "https://api.openf1.org/v1"


@dataclass(slots=True)
class ProviderResult:
    provider_name: str
    laps: pd.DataFrame


class LapDataProvider(abc.ABC):
    """Common interface for providers that return lap-level pandas frames."""

    name: str

    def __init__(self, season: int, round_number: int) -> None:
        self.season = season
        self.round_number = round_number

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...

    @abc.abstractmethod
    def load_laps(self, session_type: str = "Race") -> pd.DataFrame:
        ...


class FastF1LapProvider(LapDataProvider):
    name = "fastf1"

    def __init__(self, season: int, round_number: int, *, cache_dir: Path | None = None) -> None:
        super().__init__(season, round_number)
        self.cache_dir = cache_dir or DEFAULT_FASTF1_CACHE
        if fastf1 is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            fastf1.Cache.enable_cache(str(self.cache_dir))

    def is_available(self) -> bool:
        return fastf1 is not None

    def load_laps(self, session_type: str = "Race") -> pd.DataFrame:
        if fastf1 is None:
            raise RuntimeError("fastf1 package is not available")
        session = fastf1.get_session(self.season, self.round_number, session_type)
        session.load()
        return session.laps.copy()


class OpenF1LapProvider(LapDataProvider):
    name = "openf1"

    def is_available(self) -> bool:
        return True

    def _fetch(self, endpoint: str, params: dict[str, int | str]) -> list[dict]:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{OPENF1_API}/{endpoint}", params=params)
            resp.raise_for_status()
            return resp.json()

    def load_laps(self, session_type: str = "Race") -> pd.DataFrame:
        params = {
            "year": self.season,
            "round_number": self.round_number,
            "session_name": session_type,
        }
        data = self._fetch("laps", params)
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        renames = {
            "driver_number": "Driver",
            "lap_number": "LapNumber",
            "lap_time": "LapTime",
            "compound": "Compound",
            "stint_number": "Stint",
        }
        df = df.rename(columns={k: v for k, v in renames.items() if k in df.columns})
        if "LapTime" in df.columns:
            df["LapTime"] = pd.to_timedelta(df["LapTime"], errors="coerce")
        if "Stint" in df.columns:
            df["Stint"] = df["Stint"].astype("Int64")
        return df


def resolve_lap_provider(
    season: int,
    round_number: int,
    *,
    session_type: str = "Race",
    preferred_order: Sequence[Type[LapDataProvider]] | None = None,
) -> ProviderResult:
    """
    Attempt to load laps using providers in order. Returns the first successful.
    """

    provider_types: Iterable[Type[LapDataProvider]] = preferred_order or (
        FastF1LapProvider,
        OpenF1LapProvider,
    )
    last_error: Exception | None = None
    for provider_cls in provider_types:
        provider = provider_cls(season, round_number)
        if not provider.is_available():
            continue
        try:
            laps = provider.load_laps(session_type=session_type)
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
            continue
        if laps.empty:
            last_error = RuntimeError(f"{provider.name} returned no laps")
            continue
        return ProviderResult(provider_name=provider.name, laps=laps)

    if last_error:
        raise last_error
    raise RuntimeError("No lap providers available")
