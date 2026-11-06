"""Run both model variants on a synthetic customer history.

No dataset is required. The script demonstrates the action contract, shows that
the adapted model matches the pre-twist model on legacy input, and shows that
the feed adapter reconstructs the same history from a migrated raw feed.
"""

import copy
import importlib.util
import json
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
        "case_id": "synthetic-demo",
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


def migrated_observation():
    observation = legacy_observation()
    observation["transactions"] = {"columns": COLUMNS, "rows": []}
    events = [
        ["store", "r0", 2, 9, ROWS[0]],
        ["store", "r0", 2, 10, ROWS[0]],  # retry: must not add a purchase
        ["store", "r0", 1, 11, ["INV-OLD", "SKU-1", "Widget", 99, "2020-01-10T10:00:00", 9.5, "A", "GB", "1"]],
        ["store", "r1", 1, 12, ROWS[1]],
        ["store", "r2", 1, 13, ROWS[2]],
        ["store", "r3", 1, 14, ROWS[3]],
        ["store", "r4", 1, 15, ROWS[4]],
    ]
    observation["raw_feed"] = {
        "columns": ["source", "record_id", "revision", "delivery_id", "payload"],
        "sources": {
            "store": {
                "quantity_units_per_item": 1,
                "price_units_per_gbp": 1,
                "clock_offset_minutes": 0,
            }
        },
        "customer_sources": {"A": "store", "B": "store", "C": "store"},
        "received_at": "2020-01-26T00:00:00",
        "events": events,
    }
    return observation


def load(name, directory):
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


def main():
    pre = load("demo_pre", PRE)
    adapted = load("demo_adapted", ADAPTED)

    legacy = legacy_observation()
    migrated = migrated_observation()

    pre_legacy = pre.decide(legacy, None)
    adapted_legacy = adapted.decide(copy.deepcopy(legacy), None)
    adapted_feed = adapted.decide(migrated, None)

    checks = {
        "legacy_parity": pre_legacy == adapted_legacy,
        "raw_feed_parity": pre_legacy == adapted_feed,
        "input_not_mutated": migrated["transactions"]["rows"] == [],
    }
    if not all(checks.values()):
        raise SystemExit(f"Demo checks failed: {checks}")

    print(
        json.dumps(
            {
                "customers": legacy["customers"],
                "budget": legacy["budget"],
                "pre_twist_legacy": pre_legacy["action"],
                "adapted_raw_feed": adapted_feed["action"],
                "checks": checks,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
