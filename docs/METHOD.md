# Method

## Overview

V2.1 is a pair of shallow random forests over 26 causal, pre-cutoff customer
features. One forest predicts repeat probability; the other predicts capped
30-day value. The shortlist is ranked by predicted value.

The fitted model is exported as plain JSON and evaluated with NumPy only, so
there is no pickle dependency and no scikit-learn requirement at inference
time.

## Cleaning rules

The feature code applies the same rules used to define the targets:

- Only rows with a customer in the supplied roster are joined.
- A row must have a valid timestamp in
  `[history_start, observed_until)`.
- Exact duplicate rows are removed on the first eight source fields;
  `source_row` is excluded from the identity.
- Returns and cancellations (`InvoiceNo` starting with `C`, negative
  quantity, or nonpositive price) are counted as return evidence but never as
  purchases.
- Different rows with the same invoice number remain separate; they are
  aggregated only when computing invoice-level features.
- The gap between `observed_until` and `snapshot` is represented explicitly by
  the `observed_gap` feature. It is never filled with synthetic zero-purchase
  days.

## Features

The model uses 26 features per customer. No customer ID is used as a
predictive input.

### Base history features (9)

| Feature | Meaning |
| --- | --- |
| `recency` | Days since the most recent positive purchase |
| `invoice_frequency` | Number of distinct positive-purchase invoices |
| `recent_value` | Positive spend in the last 30 days |
| `older_value` | Positive spend older than 30 days |
| `basket_value` | Mean invoice value |
| `return_ratio` | Return value divided by positive purchase value |
| `cadence` | Mean gap between invoice dates |
| `tenure` | Days since the first purchase |
| `observed_gap` | Days between `observed_until` and `snapshot` |

### Extended history features (17)

| Group | Features |
| --- | --- |
| Invoice counts in windows | `invoices_30`, `invoices_60`, `invoices_90`, `invoices_180` |
| Spend in windows | `value_60`, `value_90`, `value_180` |
| Invoice distribution | `latest_invoice_value`, `largest_invoice_value`, `median_invoice_value`, `invoice_value_std` |
| Activity | `active_purchase_days`, `positive_line_count`, `total_units` |
| Recency concentration | `recent_share_90`, `recent_share_180` |
| Product breadth | `unique_products` |

All features are computed strictly from the supplied history. Defaults are
used when a customer has no positive purchases, so the model always returns a
finite vector.

## Model

- **Probability head:** `RandomForestRegressor` with 64 trees, maximum depth 5,
  minimum samples per leaf 40, and `max_features=1.0`.
- **Value head:** the same forest configuration, fit directly on capped value
  divided by 2000.
- **Selection:** sort by predicted value descending, breaking ties by customer
  ID, and take the first `budget` customers.
- **Inference:** portable JSON trees traversed with NumPy. Inputs are cast to
  `float32` before comparisons to match scikit-learn's tree inference.

The value head is unconditional: it estimates expected capped value directly.
It is not a probability multiplied by a conditional amount. This differs from
the earlier two-part V2 model.

## Training

- 75 public training cases, grouped into six snapshot groups.
- Five groups were used for leave-one-group-out development; the latest group
  (November 2010) was held out for a separate check.
- Eight configurations were compared: random forest vs extra trees, 9 vs 26
  features, and leaf sizes 20 vs 40.
- The configuration was selected by the customer-weighted composite
  development score.
- The selected model was then refit on all 75 training cases for the exported
  artifact.

Practice cases were used for comparison after selection, not for fitting or
hyperparameter choice. They had already been inspected during development, so
they are not an untouched holdout either.

## Why this validation matters

The data contains repeated customers across snapshots and source shards. A
random row split would leak the same customer into training and validation.
The grouped split keeps an entire customer/snapshot shard out of each fold.
The training code also asserts that no customer crosses snapshot groups.

## Reproducibility

The fitted model is included, so inference and packaging can be reproduced
without the source dataset:

```sh
python -m unittest discover -s tests -v
python scripts/package.py --output-dir dist --force
```

Training code is not included because it depends on the organiser's processed
packet, which is not redistributed. The hyperparameters and validation
protocol above are sufficient to describe the fit; the original experiment
sources were retained locally outside this repository.
