# Evaluation

## What was measured

Two different questions were measured separately:

1. **Initial-stage accuracy** on public labelled data, using the initial
   100-point formula.
2. **Post-twist compatibility** on eight released operating excerpts, which
   have no targets and cannot produce an accuracy score.

Mixing the two would be misleading. The initial numbers below say nothing
about post-twist accuracy, and the feed checks say nothing about ranking
quality.

## Initial-stage scoring

For batch mean Brier error `B`, mean squared capped-value error `E` in GBP²,
and realised shortlist value `R`:

| Component | Maximum | Formula |
| --- | ---: | --- |
| Probability | 40 | `40 * (1 - B)` |
| Value | 30 | `30 * (1 - E / 4,000,000)` |
| Selection | 30 | `30 * R / O` (or `30` if `O = 0`) |

`O` is the realised value of the best possible budget-sized set. Scores are
computed per batch and averaged with customer-count weights.

## Validation protocol

- 75 public training cases in six snapshot groups.
- Five groups used for leave-one-group-out development.
- November 2010 used as a separate holdout **after** selection.
- Practice: 51 different cases, 1,940 customers, used once for comparison
  after the model was selected.

The exported model is a refit on all 75 training cases. The development and
November numbers therefore come from out-of-fold fits, while the practice
number comes from the fully fitted artifact.

## Results

### V2.1, initial formula

| Partition | Score | Brier | Value MSE | Capture | Customers |
| --- | ---: | ---: | ---: | ---: | ---: |
| Grouped development (5 folds) | **82.553** | 0.15627 | 84,163.28 | 0.64784 | 2,191 |
| November 2010 holdout | **76.274** | 0.21932 | 117,619.81 | 0.53096 | 713 |
| Public practice | **80.908** | 0.16088 | 70,367.29 | 0.59568 | 1,940 |

### Practice comparison

| Model | Practice score | Notes |
| --- | ---: | --- |
| Starter linear baseline | 80.210 | Supplied baseline |
| V1 | 80.502 | Earlier nine-feature linear model |
| V2 | 80.582 | Two-part expected-value model |
| **V2.1** | **80.908** | 26-feature forest, this repository |

The gap is small. A difference of roughly 0.3 points on 51 public cases is not
evidence of a robust private-test advantage, and the practice set had already
been inspected repeatedly across model versions.

### Adapted V2.1

The adapted model reuses the **same fitted weights** as pre-twist V2.1. On
legacy observations its predictions are identical. On the eight released
post-twist records it normalises the migrated feed and returns a valid action
for a synthetic budget.

| Check | Result |
| --- | --- |
| Legacy predictions match pre-twist | Identical |
| Released records parsed | 8 / 8 |
| Normalised rows match independent reference | Yes |
| Input observation mutated | No |
| Labelled post-twist accuracy | Not available |

The excerpts are partial and unlabelled. Parsing them correctly proves the
adapter works; it does not prove the model ranks post-twist customers well.

## Honest caveats

- **No untouched holdout.** November was inspected after earlier experiments,
  and practice was reused across model versions. Both are development data.
- **No post-twist labels.** No complete labelled post-twist replay was
  released, so post-twist accuracy is unmeasured.
- **Coverage gaps are unknown, not zero.** The V2.1 features were designed for
  a complete 180-day history. The adapter never pads gaps, but the model has
  no explicit coverage flags, so predictions on a gappy source can be biased.
- **Small sample.** 51 practice cases and 75 training cases are enough for a
  hackathon, not for a strong generalisation claim.
- **Offline ranking.** This is not uplift modelling. Selecting a customer does
  not cause a purchase.
- **Hackathon outcome.** The submission was not shortlisted for final
  evaluation. No official score or rank is claimed here.

## Post-twist scoring, for reference

The revised stage changed the value component to:

| Component | Formula |
| --- | --- |
| Probability | `40 * (1 - B)` |
| Value | `30 * exp(-E / 129614.14440376188)` |
| Selection | `30 * min(1, R / O)` |

The exponential value scale is the population MSE of the constant-mean
predictor on the 2,904 public training labels. It was fixed before post-twist
outcomes, so it cannot be used to infer a hidden score.
