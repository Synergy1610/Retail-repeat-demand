"""Restore migrated-feed rows to causal business-clock transaction fields."""

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import math


TRANSACTION_COLUMNS = (
    "InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
    "UnitPrice", "CustomerID", "Country", "source_row",
)
EVENT_COLUMNS = ("source", "record_id", "revision", "delivery_id", "payload")


def _business_datetime(value, name):
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}") from exc
    if parsed.tzinfo is not None:
        raise ValueError(f"{name} must be naive business-clock time")
    return parsed


def _decimal(value, name, positive=False):
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not number.is_finite() or (positive and number <= 0):
        raise ValueError(f"{name} must be {'positive and ' if positive else ''}finite")
    return number


def _row_payload(payload):
    if isinstance(payload, (tuple, list)) and len(payload) == len(TRANSACTION_COLUMNS):
        return list(payload)
    if isinstance(payload, dict) and all(name in payload for name in TRANSACTION_COLUMNS):
        return [payload[name] for name in TRANSACTION_COLUMNS]
    raise ValueError("Payload must provide all nine transaction fields")


def reconstruct_transactions(events, columns, source_metadata, history_start, snapshot):
    """Resolve revisions, normalize units/time and deduplicate original fields.

    ``events`` is a sequence of table rows in ``columns`` order. The caller
    supplies ``source_metadata`` as an internal mapping, not a claimed wire
    format. Coverage gaps are not filled or treated as zero purchases. The
    caller must separately handle source routing and coverage metadata.
    """
    if not isinstance(columns, (tuple, list)) or len(columns) != len(set(columns)):
        raise ValueError("Event columns must be a unique sequence")
    if not set(EVENT_COLUMNS).issubset(columns):
        raise ValueError("Event columns are missing required fields")
    positions = {name: columns.index(name) for name in EVENT_COLUMNS}
    start = _business_datetime(history_start, "history_start")
    end = _business_datetime(snapshot, "snapshot")
    if start >= end:
        raise ValueError("history_start must precede snapshot")
    if not isinstance(source_metadata, dict):
        raise ValueError("source_metadata must be a normalized internal mapping")

    latest = {}
    for event in events:
        if not isinstance(event, (list, tuple)) or len(event) != len(columns):
            raise ValueError("Each event must match the event table columns")
        source = event[positions["source"]]
        record_id = event[positions["record_id"]]
        revision = event[positions["revision"]]
        if not isinstance(source, str) or source not in source_metadata:
            raise ValueError("Event source is missing or has no metadata")
        if record_id is None or isinstance(record_id, (dict, list, bool)):
            raise ValueError("Record ID must be a non-null scalar")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ValueError("Revision must be a nonnegative integer")
        payload = _row_payload(event[positions["payload"]])
        key = (source, record_id)
        prior = latest.get(key)
        if prior is None or revision > prior[0]:
            latest[key] = (revision, payload)
        elif revision == prior[0] and payload != prior[1]:
            raise ValueError("Retries of the same revision contain conflicting payloads")

    records = []
    seen = set()
    for (source, _record_id), (_revision, payload) in latest.items():
        settings = source_metadata[source]
        if not isinstance(settings, dict):
            raise ValueError("Source metadata must contain numeric transport settings")
        quantity_factor = _decimal(settings.get("quantity_units_per_item"), "quantity factor", positive=True)
        price_factor = _decimal(settings.get("price_units_per_gbp"), "price factor", positive=True)
        offset = _decimal(settings.get("clock_offset_minutes"), "clock offset")
        row = payload.copy()
        for index, factor, name in ((3, quantity_factor, "quantity"), (5, price_factor, "unit price")):
            if row[index] is not None:
                converted = _decimal(row[index], name) / factor
                row[index] = float(converted)
                if not math.isfinite(row[index]):
                    raise ValueError(f"Normalized {name} is not finite")
        if row[4] is not None:
            transported = _business_datetime(row[4], "InvoiceDate")
            business_time = transported - timedelta(minutes=float(offset))
            if not start <= business_time < end:
                continue
            row[4] = business_time.isoformat()
        key = tuple(row[:8])
        try:
            if key in seen:
                continue
            seen.add(key)
        except TypeError as exc:
            raise ValueError("Transaction fields must be scalar") from exc
        records.append(row)
    return records


def coverage_summary(intervals, history_start, snapshot):
    """Summarize union coverage without inventing transactions in unknown gaps."""
    start = _business_datetime(history_start, "history_start")
    end = _business_datetime(snapshot, "snapshot")
    if start >= end:
        raise ValueError("history_start must precede snapshot")
    clean = []
    for interval in intervals:
        if isinstance(interval, dict) and "start" in interval and "end" in interval:
            interval_start, interval_end = interval["start"], interval["end"]
        elif isinstance(interval, (list, tuple)) and len(interval) == 2:
            interval_start, interval_end = interval
        else:
            raise ValueError("Each complete interval needs start and end")
        a = _business_datetime(interval_start, "interval start")
        b = _business_datetime(interval_end, "interval end")
        if a >= b:
            raise ValueError("Complete intervals must be nonempty")
        a, b = max(start, a), min(end, b)
        if a < b:
            clean.append((a, b))
    clean.sort()
    merged = []
    for a, b in clean:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    seconds = sum((b - a).total_seconds() for a, b in merged)
    span = (end - start).total_seconds()
    latest_complete_end = merged[-1][1] if merged else None
    return {
        "complete_days": seconds / 86400.0,
        "unknown_days": (span - seconds) / 86400.0,
        "latest_complete_end": latest_complete_end.isoformat() if latest_complete_end else None,
    }


def adapt_observation(observation):
    """Convert a migrated raw feed; leave ordinary historical inputs unchanged.

    The feed layout is consistent with the first two partial operating
    excerpts. Missing coverage is never padded with synthetic transactions.
    Existing V2.1 model features are retained and may be sensitive to gaps.
    """
    if "raw_feed" not in observation:
        return observation
    feed = observation["raw_feed"]
    if not isinstance(feed, dict):
        raise ValueError("raw_feed must be an object")
    events = feed.get("events")
    if not isinstance(events, list):
        raise ValueError("raw_feed.events must be an event table")
    columns = feed.get("columns")
    sources = feed.get("sources")
    rows = reconstruct_transactions(
        events, columns, sources, observation["history_start"], observation["snapshot"]
    )
    adapted = observation.copy()
    adapted["transactions"] = {"columns": list(TRANSACTION_COLUMNS), "rows": rows}
    return adapted
