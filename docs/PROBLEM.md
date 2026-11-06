# The problem

## Context

This project was built in six hours for the Applied ML track of a KSIT
hackathon in November 2026. The event had two stages:

1. **Initial stage** — a conventional historical replay.
2. **Post-twist stage** — the operating feed changed, and teams had to decide
   whether their initial submission could still consume the new data.

The team's submission was not shortlisted for final evaluation. This
repository is a cleaned-up record of the work, not a claim of a winning
result.

## Task

A small online retailer has a fixed budget for prioritising customers. Given a
roster of eligible customers and their messy transaction history, predict for
each customer:

- `probability` — the chance of a qualifying purchase in the next 30 days,
  in `[0, 1]`;
- `value` — the expected capped purchase value in GBP, in `[0, 2000]`.

Then select exactly `budget = max(1, floor(number_of_customers / 5))` distinct
customer IDs. This is an offline predictive ranking task. It does **not**
estimate whether contacting a customer causes a purchase.

## Data

The source is the UCI Online Retail II workbook covering 2009–2011: online
retail line items with duplicates, cancellations, returns, nonpositive prices,
missing descriptions, and unknown customer IDs. Each observation contains up
to 180 days of history for the supplied customers.

A line counts as a **qualifying purchase** only when:

- `CustomerID` and `InvoiceNo` are present;
- `InvoiceNo` does not start with `C` or `c`;
- `Quantity > 0` and `UnitPrice > 0`.

Exact duplicate lines count once when all eight original fields match:
`InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`,
`UnitPrice`, `CustomerID`, and `Country`. `source_row` is provenance only and
is ignored for duplicate detection.

For each customer in `[snapshot, snapshot + 30 days)`:

- `repeat = 1` if any qualifying line exists;
- value is the sum of positive qualifying `Quantity * UnitPrice`, capped at
  £2,000 and rounded once to pennies with half-up rounding.

Returns and cancellations are useful historical evidence but do not subtract
from the positive-purchase target.

## Action contract

The evaluator calls `decide(observation, state)` once per batch. The response
must contain exactly:

```json
{
  "action": {
    "predictions": {
      "12345": {"probability": 0.35, "value": 125.20}
    },
    "selected": ["12345"]
  },
  "state": {}
}
```

Every supplied customer needs exactly one prediction, and `selected` must
contain exactly `budget` unique eligible IDs. State resets between cases.

## Scoring — initial stage

For batch mean Brier error `B`, mean squared capped-value error `E`, and
realised value `R` from the selected shortlist:

| Component | Points |
| --- | ---: |
| Probability | `40 * (1 - B)` |
| Value | `30 * (1 - E / 2000²)` |
| Selection | `30 * R / O`, or `30` when the oracle `O = 0` |

`O` is the realised value of the best budget-sized customer set. The final
score is the customer-count-weighted average of batch scores. Losses and
capture are computed within each batch before averaging. An invalid or partial
action scores zero for the whole batch.

## Scoring — post-twist stage

The revised stage kept the probability and selection components, but changed
the value score to a relative exponential form:

| Component | Points |
| --- | ---: |
| Probability | `40 * (1 - B)` |
| Value | `30 * exp(-E / 129614.14440376188)` |
| Selection | `30 * min(1, R / O)`, or `30` when `O = 0` |

The value scale is the population MSE of the constant-mean predictor over the
2,904 labels in the 75 public training cases. No post-twist outcomes were used
to choose it.

## Constraints

- Inference runs offline in an isolated Python 3.12 environment.
- The submission is a flat ZIP of source and JSON; no nested paths, pickles,
  or external data.
- Only the supplied observation may be used at prediction time.
- Customer ID is a join key; memorising it cannot generalise to disjoint
  customer cohorts.
- History must be strictly before `observed_until`. The seven-day gap before
  `snapshot` is unknown demand, not evidence of zero purchases.

## Post-twist change

The original transaction table was replaced by a migrated event feed. It adds
revisions, retries, per-source units, clock offsets, and partial source
coverage. See [POST_TWIST.md](POST_TWIST.md) for the adapter and its limits.

## Outcome

The team's submission was not shortlisted for final evaluation. The local
numbers in this repository are development and practice measurements, not
private final-test results.
