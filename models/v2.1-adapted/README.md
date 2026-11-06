# V2.1 — adapted for the post-twist feed

## Summary

This variant keeps the **same fitted V2.1 weights** as the pre-twist model and
adds a normalisation layer for the migrated `raw_feed`. It was not retrained on
post-twist data, because no labelled post-twist data was released.

On legacy observations it produces exactly the same predictions as the
pre-twist model. On migrated observations it reconstructs the original
transaction view from revisions, retries, source units, and clock offsets
before running the same 26 features.

## What changed

| | Pre-twist | Adapted |
| --- | --- | --- |
| Input | `transactions.rows` | `raw_feed` events |
| Revisions | Not applicable | Highest revision per record |
| Units | Original | Divided by per-source factors |
| Clocks | Business time | Offset removed per source |
| Duplicates | First 8 fields | Same, after normalisation |
| Coverage gaps | Not modelled | Not modelled; never filled |
| Model weights | `starter_model.json` | Byte-identical |

The only inference change is:

```python
adapted = adapt_observation(observation)
features = matrix(adapted)
```

## Files

| File | Purpose |
| --- | --- |
| `solution.py` | Entry point; calls the adapter before features |
| `feed_adapter.py` | Revision, unit, clock, cutoff, and dedupe logic |
| `features.py` | Same 26-feature generator as pre-twist |
| `starter_model.json` | Same fitted forest as pre-twist |

All four files must sit at the top level of a flat submission ZIP.

## Results

| Check | Result |
| --- | --- |
| Legacy predictions match pre-twist | Identical |
| Released operating records parsed | 8 / 8 |
| Normalised rows match independent reference | Yes |
| Input mutated by adapter | No |
| Valid action on synthetic budget | Yes |
| Labelled post-twist accuracy | Not available |

The released excerpts are partial and unlabelled. Passing the checks proves
that the adapter handles the feed contract; it does not prove better ranking
after the twist.

## Usage

```sh
python -c "import sys; sys.path.insert(0, 'models/v2.1-adapted'); from solution import decide; print(decide(observation, None))"
```

Or run the synthetic demo:

```sh
python scripts/demo.py
```

## Limitations

- **No retraining.** The weights are from the pre-twist world. Post-twist
  customer behaviour may differ.
- **Coverage gaps are invisible to the model.** The adapter reports gaps but
  the 26 features do not consume coverage flags. A gappy source can resemble
  an inactive customer.
- **Partial excerpts.** The eight operating records are not complete evaluator
  cases, so they cannot produce a score.
- **No accuracy claim.** Compatibility is not accuracy.

See [../../docs/POST_TWIST.md](../../docs/POST_TWIST.md) for the adapter rules
and edge cases.

## Verification

```sh
python -m unittest discover -s tests -v
python scripts/package.py --model adapted --output-dir dist --force
```

The tests compare adapted output on a raw feed with pre-twist output on the
equivalent cleaned table, check revision and duplicate handling, verify the
cutoff and clock/unit normalisation, and confirm the adapter does not mutate
its input.
