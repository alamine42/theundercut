"""
Shared utilities bridging The Undercut ingestion stack and Drive Grade engine.

This package initially hosts provider abstractions (FastF1/OpenF1) that can be
imported by both repos. Over time we can expand it with schema constants or
calibration helpers as the integration deepens.
"""

from . import providers as providers  # re-export for convenience

__all__ = ["providers"]
