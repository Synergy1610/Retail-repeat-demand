# V2.1 — pre-twist

## Summary

V2.1 is the strongest locally validated pre-twist candidate from Team 99. It
uses two shallow random forests over 26 causal customer-history features to
predict 30-day repeat probability and capped purchase value. The fitted model
is stored as plain JSON and requires only NumPy at inference time.

This is the model that reads the original `transactions.rows` table. It does
not understand the migrated `raw_feed`; use
[`../v2.1-adapted/`](../v2.1-adapted/) for that.

## At a glance

| | |
| --- | --- |
| Task | 30-day repeat probability and capped value ranking |
| Features | 26 causal history features |
| Model | 64-tree random forest per head, depth 5, leaf 40 |
| Target | `repeat` and capped value / 2000 |
| Output | One probability and value per customer, plus a shortlist |
| Inference | Python 3.11+, NumPy |
| Training data | 75 public cases from the hackathon packet |
| Practice score | **80.908** (initial formula) |
| Post-twist score | Not measured |
| Licence | MIT (code); dataset CC BY 4.0 |

## Files

| File | Purpose |
| --- | --- |
| `solution.py` | `decide(observation, state)` entry point |
| `features.py` | Cleaning and 26-feature generation |
| `starter_model.json` | Fitted forest parameters |

All three files must sit at the top level of a flat submission ZIP.

## Contract

`decide()` returns:

```python
{
    "action": {
        "predictions": {
            "12345": {"probability": 0.35, "value": 125.20},
        },
        "selected": ["12345"],
    },
    "state": {},
}
```

Predictions are finite, probability is in `[0, 1]`, value is in `[0, 2000]`,
and `selected` contains exactly `budget` unique eligible IDs. The selector
sorts by predicted value descending and breaks ties by customer ID.

## Method

Features cover recency, invoice frequency, spend windows, invoice-size
distribution, return ratio, cadence, tenure, product breadth, and the explicit
seven-day observation gap. Customer ID is a join key only.

The probability forest is fit on repeat labels. The value forest is fit
directly on capped value divided by 2000, so it estimates unconditional
expected value. The model was selected by grouped, customer-disjoint
development folds and checked on a later snapshot; the exported artifact is a
refit on all 75 training cases.

See [../../docs/METHOD.md](../../docs/METHOD.md) for the full feature list and
validation protocol.

## Results

| Partition | Score | Brier | Value MSE | Capture |
| --- | ---: | ---: | ---: | ---: |
| Grouped development | 82.553 | 0.15627 | 84,163.28 | 0.64784 |
| November 2010 holdout | 76.274 | 0.21932 | 117,619.81 | 0.53096 |
| Public practice | 80.908 | 0.16088 | 70,367.29 | 0.59568 |

Practice was already inspected during development and is not an untouched
holdout. See [../../docs/EVALUATION.md](../../docs/EVALUATION.md) for caveats.

## Usage

From the repository root:

```sh
python -c "import sys; sys.path.insert(0, 'models/v2.1-pre-twist'); from solution import decide; print(decide(observation, None))"
```

Or run the synthetic demo:

```sh
python scripts/demo.py
```

## Limitations

- The model expects the legacy transaction table; `raw_feed` is ignored.
- No labelled post-twist accuracy is available.
- The 26 features assume a reasonably complete history. Coverage gaps are not
  modelled explicitly.
- The practice set was reused, so the score is a development measurement.
- This is predictive ranking, not causal uplift.

## Verification

```sh
python -m unittest discover -s tests -v
python scripts/package.py --model pre-twist --output-dir dist --force
```

The tests build a synthetic observation, check the action contract, verify
prediction bounds and exact budget, and confirm deterministic output.
