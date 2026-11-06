"""Shared synthetic fixtures for the model tests."""

import copy
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "models" / "v2.1-pre-twist"
ADAPTED = ROOT / "models" / "v2.1-adapted"

COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
    "source_row",
]

ROWS = [
    ["INV-1", "SKU-1", "Widget", 2, "2020-01-10T10:00:00", 9.5, "A", "GB", "1"],
    ["INV-1", "SKU-2", "Gadget", 1, "2020-01-10T10:05:00", 20.0, "A", "GB", "2"],
    ["INV-2", "SKU-1", "Widget", 5, "2020-01-20T09:00:00", 9.5, "B", "GB", "3"],
    ["C-INV-3", "SKU-3", "Returned", -1, "2020-01-22T09:00:00", 9.5, "C", "GB", "4"],
    ["INV-4", "SKU-4", "Thing", 3, "2020-01-24T12:00:00", 15.0, "C", "GB", "5"],
]


def legacy_observation():
    return {
        "case_id": "synthetic-test",
        "task": "aiml",
        "snapshot": "2020-02-01T00:00:00",
        "history_start": "2020-01-01T00:00:00",
        "observed_until": "2020-01-25T00:00:00",
        "target_days": 30,
        "customers": ["A", "B", "C"],
        "budget": 1,
        "value_cap": 2000,
        "availability": {},
        "transactions": {"columns": COLUMNS, "rows": copy.deepcopy(ROWS)},
    }


def migrated_observation(source="store", quantity_factor=1, price_factor=1, offset=0):
    """Build a raw feed representing the same history as ``legacy_observation``."""
    observation = legacy_observation()
    observation["transactions"] = {"columns": COLUMNS, "rows": []}

    events = []
    for index, row in enumerate(ROWS):
        payload = list(row)
        payload[3] = payload[3] * quantity_factor
        payload[5] = payload[5] * price_factor
        if offset:
            from datetime import datetime, timedelta

            payload[4] = (
                datetime.fromisoformat(payload[4]) + timedelta(minutes=offset)
            ).isoformat()
        events.append([source, f"r{index}", 1, index + 1, payload])

    observation["raw_feed"] = {
        "columns": ["source", "record_id", "revision", "delivery_id", "payload"],
        "sources": {
            source: {
                "quantity_units_per_item": quantity_factor,
                "price_units_per_gbp": price_factor,
                "clock_offset_minutes": offset,
            }
        },
        "customer_sources": {customer: source for customer in observation["customers"]},
        "received_at": "2020-01-26T00:00:00",
        "events": events,
    }
    return observation


def load_solution(name, directory):
    """Load a model's ``solution.py`` with its own ``features`` module."""
    for module in ("features", "feed_adapter"):
        sys.modules.pop(module, None)
    sys.path.insert(0, str(directory))
    try:
        spec = importlib.util.spec_from_file_location(name, directory / "solution.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(directory))
