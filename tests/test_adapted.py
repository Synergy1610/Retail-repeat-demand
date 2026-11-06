"""Feed-adapter and parity tests for the adapted model."""

import copy
import importlib.util
import unittest

import support


def load_adapter(directory):
    spec = importlib.util.spec_from_file_location(
        "test_feed_adapter", directory / "feed_adapter.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdaptedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pre = support.load_solution("pre_for_parity", support.PRE)
        cls.adapted = support.load_solution("adapted_solution", support.ADAPTED)
        cls.adapter = load_adapter(support.ADAPTED)

    def test_legacy_predictions_match_pre_twist(self):
        legacy = support.legacy_observation()
        self.assertEqual(
            self.pre.decide(support.legacy_observation(), None),
            self.adapted.decide(legacy, None),
        )

    def test_raw_feed_matches_equivalent_legacy_input(self):
        migrated = support.migrated_observation()
        legacy = support.legacy_observation()
        self.assertEqual(
            self.adapted.decide(migrated, None),
            self.adapted.decide(legacy, None),
        )

    def test_units_and_clock_offsets_are_normalised(self):
        migrated = support.migrated_observation(
            source="partner", quantity_factor=1000, price_factor=100, offset=60
        )
        legacy = support.legacy_observation()
        self.assertEqual(
            self.adapted.decide(migrated, None),
            self.adapted.decide(legacy, None),
        )

    def test_adapter_does_not_mutate_input(self):
        migrated = support.migrated_observation()
        before = copy.deepcopy(migrated)
        self.adapted.decide(migrated, None)
        self.assertEqual(migrated, before)

    def test_retry_does_not_add_a_purchase(self):
        migrated = support.migrated_observation()
        baseline = self.adapted.decide(support.migrated_observation(), None)
        migrated["raw_feed"]["events"].append(list(migrated["raw_feed"]["events"][0]))
        self.assertEqual(self.adapted.decide(migrated, None), baseline)

    def test_highest_revision_wins_regardless_of_event_order(self):
        migrated = support.migrated_observation()
        payload = list(migrated["raw_feed"]["events"][0][4])
        payload[3] = 12
        migrated["raw_feed"]["events"].append(["store", "r0", 2, 99, payload])
        stale = list(migrated["raw_feed"]["events"][0][4])
        stale[3] = 999
        migrated["raw_feed"]["events"].append(["store", "r0", 1, 100, stale])

        adapted = self.adapter.adapt_observation(migrated)
        matching = [
            row
            for row in adapted["transactions"]["rows"]
            if row[0] == "INV-1" and row[1] == "SKU-1"
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0][3], 12)

    def test_conflicting_retry_is_rejected(self):
        migrated = support.migrated_observation()
        payload = list(migrated["raw_feed"]["events"][0][4])
        payload[3] = 7
        migrated["raw_feed"]["events"].append(["store", "r0", 1, 99, payload])
        with self.assertRaises(ValueError):
            self.adapter.adapt_observation(migrated)

    def test_cutoff_and_unknown_customer_do_not_change_output(self):
        migrated = support.migrated_observation()
        baseline = self.adapted.decide(support.migrated_observation(), None)
        future = list(support.ROWS[0])
        future[4] = "2020-02-01T00:00:00"
        unknown = list(support.ROWS[0])
        unknown[6] = "Z"
        migrated["raw_feed"]["events"].extend(
            [
                ["store", "future", 1, 98, future],
                ["store", "unknown", 1, 99, unknown],
            ]
        )
        self.assertEqual(self.adapted.decide(migrated, None), baseline)

    def test_empty_feed_still_returns_a_valid_action(self):
        migrated = support.migrated_observation()
        migrated["raw_feed"]["events"] = []
        action = self.adapted.decide(migrated, None)["action"]
        self.assertEqual(len(action["selected"]), migrated["budget"])
        self.assertEqual(set(action["predictions"]), set(migrated["customers"]))

    def test_invalid_feed_inputs_are_rejected(self):
        migrated = support.migrated_observation()
        migrated["raw_feed"] = []
        with self.assertRaises(ValueError):
            self.adapted.decide(migrated, None)

        migrated = support.migrated_observation()
        del migrated["raw_feed"]["events"]
        with self.assertRaises(ValueError):
            self.adapted.decide(migrated, None)

        migrated = support.migrated_observation()
        migrated["budget"] = 0
        with self.assertRaises(ValueError):
            self.adapted.decide(migrated, None)

    def test_coverage_summary_reports_unknown_days(self):
        summary = self.adapter.coverage_summary(
            [
                {
                    "start": "2020-01-01T00:00:00",
                    "end": "2020-01-11T00:00:00",
                }
            ],
            "2020-01-01T00:00:00",
            "2020-01-21T00:00:00",
        )
        self.assertEqual(summary["complete_days"], 10.0)
        self.assertEqual(summary["unknown_days"], 10.0)
        self.assertEqual(summary["latest_complete_end"], "2020-01-11T00:00:00")


if __name__ == "__main__":
    unittest.main()
