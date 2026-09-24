#!/usr/bin/env python3
"""Self-contained smoke tests for published warehouse scenarios and tools."""

import json
import re
import unittest
from datetime import date
from pathlib import Path

try:
    from .warehouse_db import EQUIPMENT_ACTIONS, WarehouseDB
    from . import warehouse_init
except ImportError:
    from warehouse_db import EQUIPMENT_ACTIONS, WarehouseDB
    import warehouse_init


SCENARIOS = {
    number: getattr(warehouse_init, f"warehouse_init_data{number}")
    for number in range(1, 26)
}


class WarehouseScenarioTests(unittest.TestCase):
    def test_all_scenarios_load(self):
        self.assertEqual(25, len(SCENARIOS))
        for number, data in SCENARIOS.items():
            db = WarehouseDB()
            db.init_from_json(data)
            self.assertEqual(len(data["equipment"]), len(db.get_all_equipment()), number)
            self.assertEqual(
                {False, True},
                {item["appears_in_video"] for item in data["equipment"]},
                number,
            )

    def test_names_are_unique(self):
        for number, data in SCENARIOS.items():
            names = [item["equipment"] for item in data["equipment"]]
            self.assertEqual(len(names), len(set(names)), number)

    def test_dates_and_action_values_are_valid(self):
        cutoff = date(2026, 8, 1)
        for number, data in SCENARIOS.items():
            equipment_names = {item["equipment"] for item in data["equipment"]}
            for item in data["equipment"]:
                self.assertLessEqual(date.fromisoformat(item["purchase_date"]), cutoff)
                for record in item["maintenance_history"]:
                    self.assertLessEqual(date.fromisoformat(record["date"]), cutoff)
            for action_list in data["equipment_action_lists"]:
                for action in action_list["actions"]:
                    self.assertIn(action["equipment"], equipment_names, number)
                    self.assertIn(action["required_action"], EQUIPMENT_ACTIONS, number)

    def test_queries_and_action_mutations(self):
        db = WarehouseDB()
        db.init_from_json(SCENARIOS[1])
        name = db.get_all_equipment()[0]
        category = db.get_equipment_category(name)
        location = db.get_equipment_ideal_storage_location(name)
        self.assertIn(name, db.find_equipment_by_category(category))
        self.assertIn(name, db.find_equipment_by_ideal_storage_location(location))
        db.add_to_equipment_action_list("test_user", name, "replace", "2026-08-16")
        self.assertEqual("replace", db.get_equipment_action_list("test_user")[0]["required_action"])
        db.remove_from_equipment_action_list("test_user", name, "replace", "2026-08-16")
        self.assertEqual([], db.get_equipment_action_list("test_user"))

    def test_tool_schema(self):
        tools = json.loads(Path(__file__).with_name("warehouse_tools.json").read_text())
        functions = {entry["function"]["tool_name"]: entry["function"] for entry in tools}
        self.assertEqual(17, len(functions))
        required_action = functions["add_to_equipment_action_list"]["parameters"]["properties"]["required_action"]
        due_date = functions["add_to_equipment_action_list"]["parameters"]["properties"]["due_date"]
        self.assertEqual(EQUIPMENT_ACTIONS, set(required_action["enum"]))
        self.assertRegex(due_date["description"], re.compile("YYYY-MM-DD", re.I))


if __name__ == "__main__":
    unittest.main(verbosity=2)
