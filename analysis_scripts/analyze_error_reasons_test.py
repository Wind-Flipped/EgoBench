import unittest

from analysis_scripts.analyze_error_reasons import (
    check_hallucination_error,
    check_multimodal_error,
)


class AnalyzeErrorReasonsTest(unittest.TestCase):
    def test_multimodal_check_accepts_list_parameter(self):
        gt_entry = {
            "key": "equipment",
            "value": ["Fuel Can", "Handcart", "Mechanic Stool"],
        }
        interaction_calls = [
            {
                "tool_name": "get_equipment_maintenance_and_usage_instructions",
                "parameters": {
                    "equipment": ["Fuel Can", "Handcart", "Mechanic Stool"]
                },
            }
        ]

        has_error, description = check_multimodal_error(
            gt_entry,
            interaction_calls,
            {"get_equipment_maintenance_and_usage_instructions"},
        )

        self.assertFalse(has_error, description)

    def test_multimodal_check_reports_value_missing_from_list(self):
        gt_entry = {
            "key": "equipment",
            "value": ["Fuel Can", "Handcart"],
        }
        interaction_calls = [
            {
                "tool_name": "get_equipment_maintenance_and_usage_instructions",
                "parameters": {"equipment": ["Fuel Can"]},
            }
        ]

        has_error, description = check_multimodal_error(
            gt_entry,
            interaction_calls,
            {"get_equipment_maintenance_and_usage_instructions"},
        )

        self.assertTrue(has_error)
        self.assertIn("Handcart", description)

    def test_household_name_annotation_matches_item_name_query_parameter(self):
        gt_entry = {
            "key": "name",
            "value": ["Building Blocks"],
        }
        interaction_calls = [
            {
                "tool_name": "get_item_usage_history",
                "parameters": {"item_name": "Building Blocks"},
            }
        ]

        has_error, description = check_multimodal_error(
            gt_entry,
            interaction_calls,
            {"get_item_usage_history"},
            scenario_type="household",
        )

        self.assertFalse(has_error, description)

    def test_hallucination_check_reads_user_id_from_ground_truth(self):
        gt_entry = {
            "Instruction": "Your user ID is not parsed from this text.",
            "ground_truth": [
                {
                    "tool_name": "add_to_equipment_action_list",
                    "parameters": {"user_id": "warehouse_user_01"},
                }
            ],
        }

        correct, _ = check_hallucination_error(
            gt_entry,
            [{"parameters": {"user_id": "warehouse_user_01"}}],
        )
        incorrect, description = check_hallucination_error(
            gt_entry,
            [{"parameters": {"user_id": "USER_ID_PLACEHOLDER"}}],
        )

        self.assertFalse(correct)
        self.assertTrue(incorrect)
        self.assertIn("warehouse_user_01", description)
        self.assertIn("USER_ID_PLACEHOLDER", description)


if __name__ == "__main__":
    unittest.main()
