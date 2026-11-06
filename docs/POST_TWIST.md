# The post-twist feed

## What changed

The initial observations supplied a populated `transactions.rows` table with
nine columns:

```text
InvoiceNo, StockCode, Description, Quantity, InvoiceDate,
UnitPrice, CustomerID, Country, source_row
```

After the twist, that table is empty. The history arrives as a migrated event
feed:

```json
{
  "raw_feed": {
    "columns": ["source", "record_id", "revision", "delivery_id", "payload"],
    "sources": {
      "store": {
        "quantity_units_per_item": 1,
        "price_units_per_gbp": 100,
        "clock_offset_minutes": 60
      }
    },
    "customer_sources": {"12345": "store"},
    "events": [
      ["store", "row-1", 2, 7, ["INV", "SKU", "Item", 2, "2011-01-01T10:00:00", 500, "12345", "GB", "1"]]
    ]
  }
}
```

The feed models transport effects, not new business outcomes. Targets and the
action contract are unchanged.

## Adapter rules

`feed_adapter.py` reconstructs the original transaction view before feature
generation:

1. **Resolve revisions.** Each `(source, record_id)` is one logical source row.
   The highest revision is the full replacement. Retries of the same revision
   must carry the same payload; conflicting retries raise an error.
2. **Normalise units.** Divide `Quantity` by `quantity_units_per_item` and
   `UnitPrice` by `price_units_per_gbp` for the event's source.
3. **Restore the business clock.** Subtract `clock_offset_minutes` from
   `InvoiceDate`. Drop rows that fall outside
   `[history_start, snapshot)`.
4. **Deduplicate.** Remove exact duplicates on the first eight original fields.
   `source_row`, `record_id`, and `delivery_id` are provenance, not spend
   features.
5. **Preserve unknowns.** Null source fields stay null. Missing coverage is
   never filled with zero-purchase days.

`delivery_id` identifies a transport delivery, not a purchase. Event order is
not revision order. A retry does not add a second purchase.

## Coverage

`raw_feed.customer_sources` routes each customer to a source.
`availability.sources[source].complete_intervals` gives half-open intervals
`[start, end)` that are known to be complete.

Store histories in the released excerpts were complete for 178 of 180 days.
Partner histories varied: 110, 131, and 110 complete days, leaving 70, 49, and
70 unknown days respectively. Gaps outside those intervals are **unknown**, not
evidence that a customer was inactive.

`feed_adapter.coverage_summary()` reports complete days, unknown days, and the
latest complete boundary. The V2.1 feature code does **not** use those coverage
flags. It applies the same 26 features to the normalised rows, so a gappy
source can look like a quiet customer. That is a known limitation, not a
solved problem.

## What was checked

The adapter was checked against an independent reference implementation on all
eight released operating excerpts:

- normalised rows matched the reference exactly;
- revisions, retries, duplicates, units, clocks, and the cutoff were applied;
- rows at or after the snapshot and unknown-customer rows were excluded;
- the input observation was not mutated;
- empty feeds produced a valid action;
- the packaged model returned one prediction per customer and exactly the
  requested budget.

The excerpts have no targets. They are not runnable evaluator cases, and no
post-twist accuracy is claimed.

## Why the model was not retrained

There was no labelled post-twist replay to train on. Retraining on the
unlabelled excerpts would have been guesswork, and inventing labels was not an
option. The adapted variant therefore keeps the V2.1 weights and changes only
the input normalisation. This preserves the pre-twist model's behaviour on
legacy data and makes the post-twist change auditable.

## Edge cases

The adapter rejects:

- non-list or empty event tables where a list is required;
- unknown sources or malformed source metadata;
- conflicting payloads for the same revision;
- non-scalar record IDs or negative revisions;
- payloads missing required transaction fields;
- timezone-aware timestamps (the business clock is naive retail time).

Those failures are deliberate. A silent fallback would hide broken feeds and
produce confident but meaningless predictions.
