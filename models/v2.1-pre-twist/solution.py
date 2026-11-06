"""Standalone tree-ensemble challenger for customer repeat and value."""

import json
import math
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from features import FEATURE_NAMES, matrix

_MODEL = None
_CAP = 2000.0


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    model = json.loads((_ROOT / "starter_model.json").read_text(encoding="utf-8"))
    names = model["feature_names"]
    if names != list(FEATURE_NAMES[:len(names)]) or len(names) not in (9, len(FEATURE_NAMES)):
        raise ValueError("Tree model feature order does not match feature generation")
    for head in ("probability", "value"):
        trees = model[head]
        if not isinstance(trees, list) or not trees:
            raise ValueError("Tree model has an empty head")
        for tree in trees:
            for key in ("left", "right", "feature"):
                tree[key] = np.asarray(tree[key], dtype=np.int64)
            for key in ("threshold", "value"):
                tree[key] = np.asarray(tree[key], dtype=np.float64)
    _MODEL = model
    return model


def _predict_forest(features, trees):
    # sklearn tree inference casts input values to float32 before comparisons.
    features = np.asarray(features, dtype=np.float32)
    count = len(features)
    predictions = np.zeros(count, dtype=np.float64)
    for tree in trees:
        node = np.zeros(count, dtype=np.int64)
        active = tree["left"][node] >= 0
        while np.any(active):
            rows = np.flatnonzero(active)
            current = node[rows]
            feature = tree["feature"][current]
            go_left = features[rows, feature] <= tree["threshold"][current]
            node[rows] = np.where(go_left, tree["left"][current], tree["right"][current])
            active = tree["left"][node] >= 0
        predictions += tree["value"][node]
    return predictions / len(trees)


def decide(observation, state):
    del state
    customers = observation["customers"]
    if not isinstance(customers, list) or any(not isinstance(c, str) for c in customers):
        raise ValueError("customers must be a list of string IDs")
    if len(set(customers)) != len(customers):
        raise ValueError("customers must contain unique IDs")
    budget = observation["budget"]
    if isinstance(budget, bool) or not isinstance(budget, int) or not 1 <= budget <= len(customers):
        raise ValueError("budget must be a positive integer no greater than the roster size")
    cap = observation["value_cap"]
    if isinstance(cap, bool) or not isinstance(cap, (float, int)) or not math.isfinite(cap) or cap != _CAP:
        raise ValueError("value_cap does not match the trained model")
    model = _load_model()
    features = matrix(observation)[:, :len(model["feature_names"])]
    if not np.isfinite(features).all():
        raise ValueError("Non-finite feature values")
    probabilities = np.clip(_predict_forest(features, model["probability"]), 0, 1)
    values = np.clip(_predict_forest(features, model["value"]), 0, 1) * _CAP
    if not np.isfinite(probabilities).all() or not np.isfinite(values).all():
        raise ValueError("Non-finite model outputs")
    predictions = {c: {"probability": float(p), "value": float(v)}
                   for c, p, v in zip(customers, probabilities, values)}
    selected = sorted(customers, key=lambda c: (-predictions[c]["value"], c))[:budget]
    return {"action": {"predictions": predictions, "selected": selected}, "state": {}}
