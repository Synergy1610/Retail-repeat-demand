# Data

## Source

The models were trained on a processed form of the UCI Machine Learning
Repository's **Online Retail II** dataset.

| | |
| --- | --- |
| Creator | Daqing Chen |
| Period | 2009–2011 |
| Source | <https://archive.ics.uci.edu/dataset/502/online+retail+ii> |
| Licence | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

Online Retail II contains line items from a UK-based online retailer: invoice
numbers, stock codes, descriptions, quantities, timestamps, unit prices,
customer IDs, and countries. It includes duplicates, cancellations, returns,
nonpositive prices, and missing customer IDs.

If you use the dataset, follow the citation guidance on the UCI page. No
endorsement by the creator, UCI, or the hackathon organisers is implied.

## Processed packet

The hackathon supplied a processed packet, not the raw workbook:

- **75 training cases** across six snapshot groups;
- **51 practice cases** with different customers;
- a small smoke subset;
- a local checker and public scoring constants.

Each case contains one observation and, for labelled partitions, a target map:

```text
CustomerID -> [repeat, capped_value]
```

The packet is not redistributed here. Its terms belong to the organisers, and
the dataset remains available from UCI under CC BY 4.0.

## Observation schema

An observation contains:

| Field | Meaning |
| --- | --- |
| `case_id` | Opaque case identifier |
| `snapshot` | Start of the 30-day target window |
| `history_start` | Earliest supplied history boundary |
| `observed_until` | End of known-complete history |
| `target_days` | Always 30 |
| `customers` | Eligible customer ID strings |
| `budget` | Exact shortlist size, `max(1, floor(n / 5))` |
| `value_cap` | Always 2000 |
| `availability` | Source coverage metadata |
| `transactions` | Historical line items |

The transaction columns are:

```text
InvoiceNo, StockCode, Description, Quantity, InvoiceDate,
UnitPrice, CustomerID, Country, source_row
```

`source_row` is a global provenance identifier. It is never a spend feature
and is ignored when detecting duplicates.

## Target definition

A line qualifies as a purchase only when `CustomerID` and `InvoiceNo` are
present, the invoice does not start with `C` or `c`, and both quantity and
price are positive.

- `repeat = 1` if any qualifying line occurs in
  `[snapshot, snapshot + 30 days)`.
- Value is the sum of positive qualifying `Quantity * UnitPrice`, capped at
  £2,000 per customer and rounded once to pennies with half-up rounding.
- Returns and cancellations do not subtract from the target, but may be used
  as historical features.

Exact duplicate rows are counted once when all eight original fields match.

## Why the data is not in this repository

- The processed packet is organiser material and is not ours to republish.
- The raw dataset is several megabytes and is already available from UCI.
- The fitted model and inference code are sufficient to use the model; the
  training data is not needed at prediction time.
- Keeping customer-level data out of the repository avoids an unnecessary
  redistribution of retail records.

The `.gitignore` excludes `data/`, `*.json.gz`, and common tabular formats so a
local copy cannot be committed accidentally.

## Reproducing a local evaluation

If you have the public packet, place it outside version control, for example:

```text
data/
  training.json.gz
  practice.json.gz
  smoke.json.gz
  scoring.json
  local_check.py
```

Then run the checker against a model directory:

```sh
python data/local_check.py \
  --solution models/v2.1-pre-twist/solution.py \
  --data data/practice.json.gz \
  --scoring data/scoring.json
```

The published practice score for V2.1 is **80.908** under the initial formula.
See [EVALUATION.md](EVALUATION.md) for the full breakdown and caveats.
