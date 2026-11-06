"""Action-contract and robustness tests for the pre-twist model."""

import copy
import unittest

import support


class PreTwistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solution = support.load_solution("pre_solution", support.PRE)

    def test_action_contract_and_bounds(self):
        observation = support.legacy_observation()
        result = self.solution.decide(observation, {"ignored": True})

        self.assertEqual(set(result), {"action", "state"})
        self.assertEqual(result["state"], {})
        action = result["action"]
        self.assertEqual(set(action), {"predictions", "selected"})
        self.assertEqual(set(action["predictions"]), set(observation["customers"]))
        self.assertEqual(len(action["selected"]), observation["budget"])
        self.assertEqual(len(set(action["selected"])), observation["budget"])
        self.assertTrue(set(action["selected"]) <= set(observation["customers"]))

        for prediction in action["predictions"].values():
            self.assertEqual(set(prediction), {"probability", "value"})
            self.assertTrue(0 <= prediction["probability"] <= 1)
            self.assertTrue(0 <= prediction["value"] <= 2000)

    def test_selected_is_highest_predicted_value(self):
        observation = support.legacy_observation()
        action = self.solution.decide(observation, None)["action"]
        expected = sorted(
            observation["customers"],
            key=lambda customer: (-action["predictions"][customer]["value"], customer),
        )[: observation["budget"]]
        self.assertEqual(action["selected"], expected)

    def test_deterministic_and_non_mutating(self):
        observation = support.legacy_observation()
        before = copy.deepcopy(observation)
        first = self.solution.decide(observation, None)
        second = self.solution.decide(observation, None)
        self.assertEqual(first, second)
        self.assertEqual(observation, before)

    def test_identical_customers_get_identical_predictions(self):
        observation = support.legacy_observation()
        observation["customers"] = ["A", "B"]
        observation["budget"] = 1
        a_rows = [list(row) for row in support.ROWS if row[6] == "A"]
        b_rows = []
        for row in a_rows:
            copied = list(row)
            copied[6] = "B"
            b_rows.append(copied)
        observation["transactions"]["rows"] = a_rows + b_rows

        predictions = self.solution.decide(observation, None)["action"]["predictions"]
        self.assertAlmostEqual(
            predictions["A"]["probability"], predictions["B"]["probability"], places=12
        )
        self.assertAlmostEqual(
            predictions["A"]["value"], predictions["B"]["value"], places=9
        )

    def test_empty_history_still_returns_a_valid_action(self):
        observation = support.legacy_observation()
        observation["transactions"]["rows"] = []
        action = self.solution.decide(observation, None)["action"]
        self.assertEqual(len(action["selected"]), observation["budget"])
        for prediction in action["predictions"].values():
            self.assertTrue(0 <= prediction["probability"] <= 1)
            self.assertTrue(0 <= prediction["value"] <= 2000)

    def test_invalid_inputs_are_rejected(self):
        base = support.legacy_observation()
        cases = [
            ("budget", 0),
            ("budget", True),
            ("budget", 4),
            ("value_cap", 1000),
        ]
        for key, value in cases:
            observation = copy.deepcopy(base)
            observation[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    self.solution.decide(observation, None)

        duplicate = copy.deepcopy(base)
        duplicate["customers"] = ["A", "A", "C"]
        with self.assertRaises(ValueError):
            self.solution.decide(duplicate, None)


if __name__ == "__main__":
    unittest.main()
