# Repeat Demand & Customer Value

**Predict who will buy again, how much they will spend, and who to prioritise.**

[![tests](https://github.com/Synergy1610/hackmatrix-team99/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Synergy1610/hackmatrix-team99/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Built in six hours for the Applied ML track of a KSIT hackathon in November
2026. The team's submission was **not shortlisted for final evaluation**. This
repository preserves the two model variants that came out of the work:

- **V2.1 pre-twist** — the team's primary pre-twist candidate;
- **V2.1 adapted** — the same fitted weights, with an input adapter for the
  post-twist event feed.

The interesting part is not a leaderboard score. It is a compact, auditable
model, a leakage-aware validation setup, and an honest account of what could
and could not be measured after the operating conditions changed.

---

## The problem

A small online retailer can prioritise only a fraction of its customers. Using
a messy transaction history, estimate for each eligible customer:

1. the probability of a qualifying purchase in the next 30 days;
2. the expected purchase value, capped at £2,000.

Then select exactly `max(1, floor(n / 5))` customers — 20% of the roster,
rounded down. The data comes from the UCI Online Retail II workbook and
includes duplicates, cancellations, returns, missing descriptions, and
nonpositive prices.

This is offline predictive ranking, not causal uplift. Selecting a customer
does not cause a purchase.

Read [docs/PROBLEM.md](docs/PROBLEM.md) for the full task, target definitions,
and scoring formulas.

## The models

| | V2.1 pre-twist | V2.1 adapted |
| --- | --- | --- |
| Input | Legacy `transactions.rows` | Migrated `raw_feed` |
| Fitted weights | Forest V2.1 | **Byte-identical** to pre-twist |
| Extra code | — | `feed_adapter.py` |
| Understands revisions/retries | No | Yes |
| Understands source units/clocks | No | Yes |
| Post-twist score | Not measured | Not measured |

Both models use 26 causal customer-history features and two 64-tree random
forests. The adapted variant does not retrain: it reconstructs the original
transaction view from the new feed, then runs the same features and weights.
That keeps the change auditable and avoids inventing labels that were never
released.

- [Pre-twist model card](models/v2.1-pre-twist/README.md)
- [Adapted model card](models/v2.1-adapted/README.md)

## Results

All numbers below use the **initial-stage** 100-point formula. They are
historical development and practice measurements, not private final-test
results.

| Evaluation | V2.1 pre-twist | V2.1 adapted |
| --- | ---: | ---: |
| Grouped development (5 folds, 2,191 customers) | 82.553 | 82.553 |
| November 2010 holdout (713 customers) | 76.274 | 76.274 |
| Public practice (51 cases, 1,940 customers) | **80.908** | **80.908** |
| Released twist records parsed | — | 8 / 8 |
| Labelled post-twist score | — | — |

The pre-twist model ignores `raw_feed`. The adapted model parses it and returns
a valid action, but the released excerpts have no targets. Compatibility is not
accuracy. See [docs/EVALUATION.md](docs/EVALUATION.md) for component scores,
baselines, and caveats.

## How it works

```text
raw observation
      │
      ├── pre-twist ──────────────► transactions.rows
      │                                   │
      └── adapted ──► feed_adapter ──► normalised rows
                          │
                          ▼
              26 causal history features
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
      repeat-probability        capped-value
           forest                  forest
              │                       │
              └───────────┬───────────┘
                          ▼
             rank by value, take budget
```

Key choices:

- **No customer-ID feature.** IDs are join keys, not signals.
- **Customer-disjoint validation.** Entire snapshot/customer shards are held
  out; a random row split would leak repeat customers.
- **Explicit observation gap.** The seven days between `observed_until` and
  `snapshot` are unknown demand, not zero purchases.
- **Portable JSON trees.** No pickle, no scikit-learn at inference time; only
  NumPy.
- **No gap imputation.** The adapter reports unknown coverage but never fills
  it with fake transactions.
- **Same weights after the twist.** The adaptation changes plumbing, not the
  learned model.

The 26 features cover recency, frequency, spend windows, invoice-size
distribution, return ratio, cadence, tenure, product breadth, and the
observation gap. See [docs/METHOD.md](docs/METHOD.md) for the full table and
training protocol.

## Repository layout

```text
.
├── models/
│   ├── v2.1-pre-twist/       # solution.py, features.py, starter_model.json
│   └── v2.1-adapted/         # adds feed_adapter.py; same model weights
├── docs/
│   ├── PROBLEM.md            # task, targets, scoring, constraints
│   ├── METHOD.md             # features, forests, validation
│   ├── EVALUATION.md         # results and honest caveats
│   ├── POST_TWIST.md         # migrated feed and adapter rules
│   └── DATA.md               # dataset, licence, schema
├── scripts/
│   ├── package.py            # build flat submission ZIPs
│   └── demo.py               # run both models on synthetic data
├── tests/                    # no dataset required
├── dist/                     # prebuilt ZIPs + SHA-256 checksums
├── requirements.txt
├── LICENSE
└── NOTICE
```

## Quick start

Python 3.11 or newer is enough. Only NumPy is required.

```bash
git clone https://github.com/Synergy1610/hackmatrix-team99.git
cd hackmatrix-team99

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

python -m unittest discover -s tests -v
python scripts/demo.py
python scripts/package.py --output-dir dist --force
```

The demo builds a synthetic customer history, runs both models, and prints the
predictions and shortlist. It does not download or need the source dataset.

To use a model directly:

```python
import sys
sys.path.insert(0, "models/v2.1-adapted")
from solution import decide

result = decide(observation, None)
predictions = result["action"]["predictions"]
selected = result["action"]["selected"]
```

`observation` must follow the schema in [docs/DATA.md](docs/DATA.md).

## The twist

Halfway through the event, the transaction feed changed. The original
`transactions.rows` table became empty and history arrived as an event feed
with revisions, retries, per-source unit factors, clock offsets, and partial
coverage.

The adapted model resolves the latest revision per logical row, normalises
units and clocks, drops rows outside the history window, and deduplicates on
the original eight fields. It deliberately does not impute missing coverage.
The pre-twist features were designed for complete histories, so a gappy source
can still mislead the model.

Read [docs/POST_TWIST.md](docs/POST_TWIST.md) for the contract, edge cases, and
the eight released records.

## What this project demonstrates

- Temporal, customer-disjoint validation instead of a leaky random split.
- A compact model artifact that can be inspected without Python pickles.
- A clean separation between model weights and input normalisation.
- An adapter that fails loudly on malformed feeds instead of guessing.
- Evaluation writing that distinguishes a compatibility check from a score.

## Limitations

- **No untouched holdout.** The November group and the practice set were both
  inspected during development.
- **No labelled post-twist data.** Post-twist ranking quality is unmeasured.
- **Coverage gaps are not modelled.** The adapter never invents rows, but the
  26 features have no explicit coverage flags.
- **Small sample.** 75 training cases and 51 practice cases support a
  hackathon result, not a production claim.
- **Offline ranking.** No uplift or causal effect is estimated.
- **Not shortlisted.** The hackathon submission did not reach final evaluation.

## Attribution and licence

The models were trained on data derived from the UCI Machine Learning
Repository's [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)
dataset by Daqing Chen, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

The dataset and the organiser's processed packet are **not** included in this
repository. See [NOTICE](NOTICE) and [docs/DATA.md](docs/DATA.md).

The source code and fitted model parameters are released under the
[MIT licence](LICENSE).
