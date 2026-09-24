#!/usr/bin/env python3
"""Self-contained smoke tests for published household scenarios and tools."""

import json
import re
import unittest
from datetime import date
from pathlib import Path

try:
    from .household_db import HOUSEHOLD_ACTIONS, HouseholdDB
    from . import household_init
except ImportError:
    from household_db import HOUSEHOLD_ACTIONS, HouseholdDB
    import household_init


SCENARIOS = {
    number: getattr(household_init, f"household_init_data{number}")
    for number in range(1, 19)
}


class HouseholdScenarioTests(unittest.TestCase):
    def test_all_scenarios_load(self):
        self.assertEqual(18, len(SCENARIOS))
        for number, data in SCENARIOS.items():
            db = HouseholdDB()
            db.init_from_json(data)
            self.assertEqual(len(data["items"]), len(db.get_all_item_names()), number)
            self.assertEqual(
                {False, True},
                {item["appears_in_video"] for item in data["items"]},
                number,
            )

    def test_names_are_unique(self):
        for number, data in SCENARIOS.items():
            names = [item["name"] for item in data["items"]]
            self.assertEqual(len(names), len(set(names)), number)

    def test_dates_and_action_values_are_valid(self):
        cutoff = date(2026, 8, 1)
        for number, data in SCENARIOS.items():
            item_names = {item["name"] for item in data["items"]}
            for item in data["items"]:
                self.assertLessEqual(date.fromisoformat(item["purchase_date"]), cutoff)
                for record in item["maintenance_history"]:
                    self.assertLessEqual(date.fromisoformat(record["date"]), cutoff)
            for action_list in data["household_action_lists"]:
                for action in action_list["actions"]:
                    self.assertIn(action["name"], item_names, number)
                    self.assertIn(action["required_action"], HOUSEHOLD_ACTIONS, number)

    def test_queries_and_action_mutations(self):
        db = HouseholdDB()
        db.init_from_json(SCENARIOS[1])
        name = db.get_all_item_names()[0]
        category = db.get_item_category(name)
        location = db.get_item_ideal_storage_location(name)
        self.assertIn(name, db.find_items_by_category(category))
        self.assertIn(name, db.find_items_by_ideal_storage_location(location))
        db.add_to_household_action_list("test_user", name, "clean", "2026-08-16")
        self.assertEqual("clean", db.get_household_action_list("test_user")[0]["required_action"])
        db.remove_from_household_action_list("test_user", name, "clean", "2026-08-16")
        self.assertEqual([], db.get_household_action_list("test_user"))

    def test_tool_schema(self):
        tools = json.loads(Path(__file__).with_name("household_tools.json").read_text())
        functions = {entry["function"]["tool_name"]: entry["function"] for entry in tools}
        self.assertEqual(16, len(functions))
        required_action = functions["add_to_household_action_list"]["parameters"]["properties"]["required_action"]
        due_date = functions["add_to_household_action_list"]["parameters"]["properties"]["due_date"]
        self.assertEqual(HOUSEHOLD_ACTIONS, set(required_action["enum"]))
        self.assertRegex(due_date["description"], re.compile("YYYY-MM-DD", re.I))


if __name__ == "__main__":
    unittest.main(verbosity=2)
