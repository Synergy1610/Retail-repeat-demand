# Prebuilt submission archives

These ZIPs are generated from [`models/`](../models) by
[`scripts/package.py`](../scripts/package.py).

| Archive | Model | Contents |
| --- | --- | --- |
| `Team-99_v2.1_pre-twist.zip` | V2.1 pre-twist | `solution.py`, `features.py`, `starter_model.json` |
| `Team-99_v2.1_adapted.zip` | V2.1 adapted | `solution.py`, `features.py`, `feed_adapter.py`, `starter_model.json` |

Each archive is flat, deterministic, and contains no datasets, notebooks, or
pickles. `SHA256SUMS` records the digests.

Rebuild them with:

```sh
python scripts/package.py --output-dir dist --force
```

The hackathon runner accepts this flat layout. The original submission archives
were built from the same source directories; these regenerated artifacts use
fixed ZIP timestamps so repeated builds are reproducible.
