import argparse
import json
import os
import tempfile
import unittest

from analysis_scripts.evaluate_interaction import (
    evaluate_interaction_success,
    get_init_db,
    parse_result_filename,
)


class EvaluateNewScenariosTest(unittest.TestCase):
    def test_restaurant6_is_classified_as_restaurant_variant_6(self):
        self.assertEqual(
            ("restaurant", 6, "easy"),
            parse_result_filename("restaurant6_easy.json"),
        )
        self.assertIsNone(parse_result_filename("restaurant7_easy.json"))

    def test_household_result_filename_is_supported(self):
        self.assertEqual(
            ("household", 18, "static"),
            parse_result_filename("household18_static.json"),
        )
        self.assertIsNone(parse_result_filename("household19_static.json"))

    def _evaluate(self, scenario, scenario_number, ground_truth, interactions):
        with tempfile.TemporaryDirectory() as temp_dir:
            ground_truth_path = os.path.join(temp_dir, "ground_truth.json")
            interaction_path = os.path.join(temp_dir, "interaction.json")
            with open(ground_truth_path, "w", encoding="utf-8") as stream:
                json.dump(ground_truth, stream)
            with open(interaction_path, "w", encoding="utf-8") as stream:
                json.dump(interactions, stream)

            return evaluate_interaction_success(
                ground_truth_path,
                interaction_path,
                scenario=scenario,
                args=argparse.Namespace(scenario_number=scenario_number),
                silent=True,
            )

    def test_warehouse_mutation_and_final_state_are_evaluated(self):
        database = get_init_db("warehouse", 1)
        equipment = next(iter(database.equipment))
        call = {
            "tool_name": "add_to_equipment_action_list",
            "parameters": {
                "user_id": "warehouse_user_01",
                "equipment": equipment,
                "required_action": "replace",
                "due_date": "2026-08-20",
            },
        }
        result = self._evaluate(
            "warehouse",
            1,
            [{"scenario_id": 1, "ground_truth": [call]}],
            [{
                "scenario_id": 1,
                "tool_calls": [{"turn": 0, "calls": [call], "results": []}],
            }],
        )

        self.assertTrue(result["is_complete"])
        self.assertEqual(result["joint_success"]["success_rate"], 1.0)

    def test_household_mutation_and_final_state_are_evaluated(self):
        database = get_init_db("household", 1)
        item_name = next(iter(database.items))
        call = {
            "tool_name": "add_to_household_action_list",
            "parameters": {
                "user_id": "household_user_01",
                "name": item_name,
                "required_action": "repair",
                "due_date": "2026-08-20",
            },
        }
        result = self._evaluate(
            "household",
            1,
            [{"scenario_id": 1, "ground_truth": [call]}],
            [{
                "scenario_id": 1,
                "tool_calls": [{"turn": 0, "calls": [call], "results": []}],
            }],
        )

        self.assertTrue(result["is_complete"])
        self.assertEqual(result["joint_success"]["success_rate"], 1.0)

    def test_missing_scenario_id_marks_file_incomplete(self):
        database = get_init_db("warehouse", 1)
        equipment = next(iter(database.equipment))
        call = {
            "tool_name": "get_equipment_category",
            "parameters": {"equipment": equipment},
        }
        result = self._evaluate(
            "warehouse",
            1,
            [
                {"scenario_id": 1, "ground_truth": [call]},
                {"scenario_id": 2, "ground_truth": [call]},
            ],
            [{
                "scenario_id": 1,
                "tool_calls": [{"turn": 0, "calls": [call], "results": []}],
            }],
        )

        self.assertFalse(result["is_complete"])
        self.assertEqual(result["valid_scenarios"], 1)
        self.assertEqual(result["total_scenarios"], 2)

    def test_order_is_not_a_supported_database_scenario(self):
        with self.assertRaisesRegex(ValueError, "unsupported scenario"):
            get_init_db("order", 1)

    def test_only_four_original_simulated_user_averages_are_kept(self):
        database = get_init_db("warehouse", 1)
        equipment = next(iter(database.equipment))
        call = {
            "tool_name": "get_equipment_category",
            "parameters": {"equipment": equipment},
        }
        ground_truth = [
            {"scenario_id": 1, "ground_truth": [call]},
            {"scenario_id": 2, "ground_truth": [call]},
        ]
        interactions = [
            {
                "scenario_id": 1,
                "tool_calls": [{"turn": 0, "calls": [call], "results": []}],
                "user_performance": {
                    "original_role_consistency_avg": 1.0,
                    "original_instruction_following_avg": 0.8,
                    "original_resilience_avg": 0.6,
                    "original_contextual_robustness_avg": 0.4,
                    "final_role_consistency_avg": 99.0,
                },
            },
            {
                "scenario_id": 2,
                "tool_calls": [{"turn": 0, "calls": [call], "results": []}],
                "user_performance": {
                    "original_role_consistency_avg": 0.5,
                },
            },
        ]

        result = self._evaluate(
            "warehouse", 1, ground_truth, interactions
        )
        performance = result["performance_metrics"]

        self.assertEqual(
            set(performance["avg_user_performance"]),
            {
                "role_consistency",
                "instruction_following",
                "resilience",
                "contextual_robustness",
            },
        )
        self.assertAlmostEqual(
            performance["avg_user_performance"]["role_consistency"], 0.75
        )
        self.assertEqual(
            performance["user_performance_sample_counts"]["role_consistency"],
            2,
        )
        self.assertEqual(
            performance["user_performance_sample_counts"]["instruction_following"],
            1,
        )
        self.assertNotIn("scenario_stats", result)
        self.assertNotIn("filtered_user_issue", result)


if __name__ == "__main__":
    unittest.main()
