"""Regression tests for JSON tool schemas and database method signatures."""

import inspect
import json
import unittest
from pathlib import Path

from run.utils import execute_tool
from tools.household.household_db import HouseholdDB
from tools.kitchen.kitchen_db import KitchenDB
from tools.restaurant.restaurant6_db import Restaurant6DB
from tools.restaurant.restaurant_db import RestaurantDB
from tools.retail.retail_db import RetailDB
from tools.warehouse.warehouse_db import WarehouseDB


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_CONTRACTS = (
    ("tools/retail/retail_tools.json", RetailDB),
    ("tools/kitchen/kitchen_tools.json", KitchenDB),
    ("tools/restaurant/restaurant_tools.json", RestaurantDB),
    ("tools/restaurant/restaurant6_tools.json", Restaurant6DB),
    ("tools/warehouse/warehouse_tools.json", WarehouseDB),
    ("tools/household/household_tools.json", HouseholdDB),
)


def _tool_definition(entry):
    return entry.get("function", entry)


class ToolSchemaContractTests(unittest.TestCase):
    def test_schema_parameters_match_database_signatures(self):
        for relative_schema_path, database_class in TOOL_CONTRACTS:
            schema_path = PROJECT_ROOT / relative_schema_path
            definitions = json.loads(schema_path.read_text(encoding="utf-8"))

            for entry in definitions:
                definition = _tool_definition(entry)
                tool_name = definition.get("tool_name") or definition.get("name")
                with self.subTest(schema=relative_schema_path, tool=tool_name):
                    self.assertTrue(tool_name, "Tool definition is missing its name")
                    self.assertTrue(
                        hasattr(database_class, tool_name),
                        f"{database_class.__name__}.{tool_name} is not implemented",
                    )

                    signature = inspect.signature(getattr(database_class, tool_name))
                    parameters = {
                        name: parameter
                        for name, parameter in signature.parameters.items()
                        if name != "self"
                    }
                    accepts_extra_keywords = any(
                        parameter.kind == inspect.Parameter.VAR_KEYWORD
                        for parameter in parameters.values()
                    )
                    schema = definition.get("parameters", {})
                    schema_parameters = set(schema.get("properties", {}))
                    schema_required = set(schema.get("required", []))

                    if not accepts_extra_keywords:
                        self.assertEqual(
                            set(),
                            schema_parameters - set(parameters),
                            "Schema exposes keyword arguments rejected by the implementation",
                        )

                    implementation_required = {
                        name
                        for name, parameter in parameters.items()
                        if parameter.default is inspect.Parameter.empty
                        and parameter.kind
                        in (
                            inspect.Parameter.POSITIONAL_ONLY,
                            inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            inspect.Parameter.KEYWORD_ONLY,
                        )
                    }
                    self.assertEqual(
                        set(),
                        implementation_required - schema_required,
                        "Implementation requires arguments that the schema marks optional",
                    )

    def test_retail_catalog_tools_accept_schema_keywords(self):
        database = RetailDB()
        add_result = execute_tool(
            database,
            {
                "tool_name": "add_product",
                "parameters": {
                    "product_name": "contract test product",
                    "category": "test",
                    "price": 1.0,
                    "tax_rate": 0.0,
                    "discount": 1.0,
                    "nutritional_characteristics": [],
                    "taste": [],
                    "country_of_origin": "test",
                    "nutrition": {"basis": "PER_SERVING"},
                },
            },
        )
        self.assertEqual("success", json.loads(add_result[0]["content"])["status"])

        delete_result = execute_tool(
            database,
            {
                "tool_name": "delete_product",
                "parameters": {"product_name": "contract test product"},
            },
        )
        self.assertEqual("success", json.loads(delete_result[0]["content"])["status"])

    def test_restaurant_catalog_tools_accept_schema_keywords(self):
        database = RestaurantDB()
        self._exercise_restaurant_catalog(database, restaurant_name=None)

    def test_restaurant6_catalog_tools_accept_schema_keywords(self):
        database = Restaurant6DB()
        self._exercise_restaurant_catalog(database, restaurant_name="contract test restaurant")

    def _exercise_restaurant_catalog(self, database, restaurant_name):
        common_parameters = {
            "dish_name": "contract test dish",
            "category": "Pizza",
            "price": 1.0,
            "tax_rate": 0.0,
            "discount": 1.0,
            "nutritional_characteristics": [],
            "taste": [],
            "allergens": [],
            "nutrition": {"basis": "PER_SERVING"},
        }
        if restaurant_name is not None:
            common_parameters["restaurant_name"] = restaurant_name

        add_result = execute_tool(
            database,
            {"tool_name": "add_dish_to_catalog", "parameters": common_parameters},
        )
        self.assertEqual("success", json.loads(add_result[0]["content"])["status"])

        identity = {"dish_name": "contract test dish"}
        if restaurant_name is not None:
            identity["restaurant_name"] = restaurant_name

        for tool_name, extra_parameters in (
            ("update_dish_price", {"new_price": 2.0}),
            ("update_dish_discount", {"new_discount": 0.5}),
            ("remove_dish_from_catalog", {}),
        ):
            result = execute_tool(
                database,
                {
                    "tool_name": tool_name,
                    "parameters": {**identity, **extra_parameters},
                },
            )
            self.assertEqual("success", json.loads(result[0]["content"])["status"])


if __name__ == "__main__":
    unittest.main()
