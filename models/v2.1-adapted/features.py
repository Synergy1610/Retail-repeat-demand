"""Causal transaction features used by the inference model."""

from datetime import datetime
import math

import numpy as np


FEATURE_NAMES = (
    "recency",
    "invoice_frequency",
    "recent_value",
    "older_value",
    "basket_value",
    "return_ratio",
    "cadence",
    "tenure",
    "observed_gap",
)

_ROW_FIELDS = 8
_FEATURE_COUNT = len(FEATURE_NAMES)
_DEFAULT_RECENCY = 180.0
_DEFAULT_CADENCE = 90.0


def _parse_datetime(value):
    """Parse an ISO timestamp, returning None for missing or invalid values."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _finite_number(value):
    """Return a finite float for numeric source values, otherwise None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    return number


def matrix(observation):
    """Build the frozen nine-column feature matrix in roster order.

    Only exact duplicate transaction rows (the first eight source fields) are
    removed. Rows must have a customer in the supplied roster and a valid date
    in the available history interval to affect any feature.
    """
    customers = observation["customers"]
    snapshot = datetime.fromisoformat(observation["snapshot"])
    history_start = datetime.fromisoformat(observation["history_start"])
    observed_until = datetime.fromisoformat(observation["observed_until"])

    grouped = {customer_id: [] for customer_id in customers}
    seen_rows = set()

    for row in observation["transactions"]["rows"]:
        if not isinstance(row, (list, tuple)) or len(row) < _ROW_FIELDS + 1:
            continue

        # source_row is intentionally excluded from duplicate identity.
        original_fields = tuple(row[:_ROW_FIELDS])
        try:
            if original_fields in seen_rows:
                continue
            seen_rows.add(original_fields)
        except TypeError:
            # Source fields are scalar by contract. Ignore malformed rows
            # rather than letting an unhashable value disrupt the whole batch.
            continue

        customer_id = row[6]
        if customer_id not in grouped:
            continue

        transaction_date = _parse_datetime(row[4])
        if transaction_date is None:
            continue
        try:
            if not history_start <= transaction_date < observed_until:
                continue
        except TypeError:
            # The source contract uses local-naive timestamps. Incompatible
            # or timezone-aware malformed dates cannot safely pass the filter.
            continue

        grouped[customer_id].append((row, transaction_date))

    rows_by_customer = []
    observed_gap = (snapshot - observed_until).total_seconds() / 86400.0
    for customer_id in customers:
        invoice_values = {}
        invoice_ages = {}
        recent_value = 0.0
        older_value = 0.0
        return_value = 0.0

        for row, transaction_date in grouped[customer_id]:
            invoice_no = row[0]
            quantity = _finite_number(row[3])
            unit_price = _finite_number(row[5])
            if quantity is None or unit_price is None:
                continue

            amount = quantity * unit_price
            if not math.isfinite(amount):
                continue

            is_cancellation = str(invoice_no).upper().startswith("C")
            if quantity < 0 or is_cancellation:
                return_value += abs(amount)
                continue

            # Positive purchases require a present invoice and positive
            # quantity and unit price. Returns never reduce purchase totals.
            if not isinstance(invoice_no, str) or quantity <= 0 or unit_price <= 0:
                continue

            age = (snapshot - transaction_date).total_seconds() / 86400.0
            invoice_values[invoice_no] = invoice_values.get(invoice_no, 0.0) + amount
            # The smallest age is the latest positive line date for an invoice.
            invoice_ages[invoice_no] = min(age, invoice_ages.get(invoice_no, math.inf))
            if age <= 30.0:
                recent_value += amount
            else:
                older_value += amount

        total_value = sum(invoice_values.values())
        ages = sorted(invoice_ages.values())
        gaps = [later - earlier for earlier, later in zip(ages, ages[1:])]
        cadence = sum(gaps) / len(gaps) if gaps else _DEFAULT_CADENCE

        rows_by_customer.append(
            [
                min(ages) if ages else _DEFAULT_RECENCY,
                len(invoice_values),
                recent_value,
                older_value,
                total_value / max(1, len(invoice_values)),
                return_value / max(1.0, total_value),
                cadence,
                max(ages) if ages else _DEFAULT_RECENCY,
                observed_gap,
            ]
        )

    if not rows_by_customer:
        return np.empty((0, _FEATURE_COUNT), dtype=np.float64)

    result = np.asarray(rows_by_customer, dtype=np.float64).reshape(
        len(customers), _FEATURE_COUNT
    )
    if not np.isfinite(result).all():
        raise ValueError("Invalid causal features")
    return result


_base_matrix = matrix
EXTRA_FEATURE_NAMES = (
    "invoices_30", "invoices_60", "invoices_90", "invoices_180",
    "value_60", "value_90", "value_180", "latest_invoice_value",
    "largest_invoice_value", "median_invoice_value", "invoice_value_std",
    "active_purchase_days", "positive_line_count", "total_units",
    "recent_share_90", "recent_share_180", "unique_products",
)
FEATURE_NAMES = FEATURE_NAMES + EXTRA_FEATURE_NAMES


def matrix(observation):
    """Append richer, strictly pre-cutoff purchase-history features."""
    base = _base_matrix(observation)
    customers = observation["customers"]
    snapshot = datetime.fromisoformat(observation["snapshot"])
    start = datetime.fromisoformat(observation["history_start"])
    cutoff = datetime.fromisoformat(observation["observed_until"])
    groups = {customer: {} for customer in customers}
    seen = set()
    for row in observation["transactions"]["rows"]:
        if not isinstance(row, (list, tuple)) or len(row) < 9:
            continue
        try:
            key = tuple(row[:8])
            if key in seen:
                continue
            seen.add(key)
        except TypeError:
            continue
        customer = row[6]
        if customer not in groups:
            continue
        date = _parse_datetime(row[4])
        if date is None:
            continue
        try:
            if not start <= date < cutoff:
                continue
        except TypeError:
            continue
        invoice, quantity, price = row[0], _finite_number(row[3]), _finite_number(row[5])
        if not isinstance(invoice, str) or not invoice or invoice.upper().startswith("C"):
            continue
        if quantity is None or price is None or quantity <= 0 or price <= 0:
            continue
        amount = quantity * price
        if not math.isfinite(amount):
            continue
        invoices = groups[customer]
        if invoice not in invoices:
            invoices[invoice] = {"amount": 0.0, "latest": date, "lines": 0, "units": 0.0, "products": set(), "days": set(), "windows": [0.0, 0.0, 0.0]}
        item = invoices[invoice]
        item["amount"] += amount
        item["latest"] = max(item["latest"], date)
        item["lines"] += 1
        item["units"] += quantity
        item["days"].add(date.date())
        if isinstance(row[1], str) and row[1]:
            item["products"].add(row[1])
        age = (snapshot - date).total_seconds() / 86400.0
        for i, days in enumerate((30, 60, 90)):
            if age <= days:
                item["windows"][i] += amount

    extras = []
    for customer in customers:
        invoices = list(groups[customer].values())
        ages = [(snapshot - item["latest"]).total_seconds() / 86400.0 for item in invoices]
        amounts = np.asarray([item["amount"] for item in invoices], dtype=np.float64)
        counts = [sum(age <= days for age in ages) for days in (30, 60, 90, 180)]
        recent = [sum(item["windows"][i] for item in invoices) for i in range(3)]
        total = float(amounts.sum()) if len(amounts) else 0.0
        latest = min(range(len(ages)), key=ages.__getitem__) if ages else None
        products = set().union(*(item["products"] for item in invoices)) if invoices else set()
        days = set().union(*(item["days"] for item in invoices)) if invoices else set()
        extras.append(counts + [
            recent[1], recent[2], total,
            invoices[latest]["amount"] if latest is not None else 0.0,
            float(amounts.max()) if len(amounts) else 0.0,
            float(np.median(amounts)) if len(amounts) else 0.0,
            float(amounts.std()) if len(amounts) else 0.0,
            len(days), sum(item["lines"] for item in invoices),
            sum(item["units"] for item in invoices),
            recent[0] / max(1.0, recent[2]), recent[0] / max(1.0, total), len(products),
        ])
    if not customers:
        return np.empty((0, len(FEATURE_NAMES)), dtype=np.float64)
    result = np.concatenate([base, np.asarray(extras, dtype=np.float64)], axis=1)
    if result.shape != (len(customers), len(FEATURE_NAMES)) or not np.isfinite(result).all():
        raise ValueError("Invalid extended causal features")
    return result
