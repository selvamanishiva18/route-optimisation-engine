"""
Shared test fixtures and helpers.
Read docs/testing-guide.md before modifying.
"""

import json
import os
import pytest
from pathlib import Path
from schemas.request import EngineRequest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(relative_path: str) -> dict:
    """
    Load a JSON fixture file.
    Strips all keys prefixed with "_" (test metadata) before returning.
    """
    full_path = FIXTURES_DIR / relative_path
    with open(full_path, "r") as f:
        data = json.load(f)

    # Separate metadata from engine input
    metadata = {k: v for k, v in data.items() if k.startswith("_")}
    payload = {k: v for k, v in data.items() if not k.startswith("_")}

    return {"metadata": metadata, "payload": payload}


def parse_request(payload: dict) -> EngineRequest:
    """Parse raw dict into EngineRequest."""
    return EngineRequest(**payload)
