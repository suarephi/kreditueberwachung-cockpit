#!/usr/bin/env python3
"""Build the base SQLite dataset + per-table CSVs."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kreditueberwachung_mock import pipeline


if __name__ == "__main__":
    pipeline.run()
