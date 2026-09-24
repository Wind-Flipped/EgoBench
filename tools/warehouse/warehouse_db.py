"""In-memory database and tool implementations for the equipment warehouse."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, datetime
import re
from typing import Any, Dict, List


EQUIPMENT_CATEGORIES = {
    "manual_equipment", "power_equipment", "measuring_and_testing_equipment",
    "lifting_and_moving_equipment", "access_equipment", "safety_equipment",
    "cleaning_equipment", "storage_equipment", "consumable", "other",
}
STORAGE_LOCATIONS = {
    "dry_equipment_cabinet", "locked_equipment_cabinet", "wall_rack", "pegboard",
    "drawer_unit", "parts_bin", "shelving_unit", "floor_storage_area",
    "charging_station", "safety_equipment_cabinet", "chemical_storage_cabinet",
    "outdoor_storage_shed",
}
MAINTENANCE_ACTIONS = {"clean", "inspect", "lubricate", "calibrate", "sharpen", "condition"}
LIFECYCLE_ACTIONS = {"replace", "repair", "relocate", "dispose"}
EQUIPMENT_ACTIONS = MAINTENANCE_ACTIONS | LIFECYCLE_ACTIONS
DATA_START = date(2016, 8, 20)
DATA_CUTOFF = date(2026, 8, 1)


def _parse_date(value: str, field_name: str):
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a YYYY-MM-DD string")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format") from exc


@dataclass(frozen=True)
class MaintenanceRecord:
    date: str
    action: str


@dataclass(frozen=True)
class Equipment:
    equipment: str
    appears_in_video: bool
    category: str
    brand: str
    country_of_origin: str
    purchase_date: str
    ideal_storage_location: str
    usage_history: List[str]
    maintenance_and_usage_instructions: str
    maintenance_history: List[MaintenanceRecord]


@dataclass(frozen=True)
class EquipmentAction:
    equipment: str
    required_action: str
    due_date: str


class WarehouseDB:
    """Store equipment profiles and per-user equipment action lists."""

    def __init__(self) -> None:
        self.equipment: Dict[str, Equipment] = {}
        self.user_action_lists: Dict[str, List[EquipmentAction]] = {}

    def init_from_json(self, data: Dict[str, Any]) -> None:
        new_equipment: Dict[str, Equipment] = {}
        for raw in data.get("equipment", []):
            item = self._make_equipment(raw)
            if item.equipment in new_equipment:
                raise ValueError(f"duplicate equipment name: {item.equipment}")
            new_equipment[item.equipment] = item
        self._validate_equipment_groups(new_equipment)
        new_lists: Dict[str, List[EquipmentAction]] = {}
        raw_action_lists = data.get("equipment_action_lists", [])
        if not isinstance(raw_action_lists, list) or not 3 <= len(raw_action_lists) <= 5:
            raise ValueError("equipment_action_lists must contain 3 to 5 users")
        for raw_list in raw_action_lists:
            if set(raw_list) != {"user_id", "actions"}:
                raise ValueError("each equipment action list must contain only user_id and actions")
            user_id = raw_list.get("user_id")
            if not isinstance(user_id, str) or re.fullmatch(r"warehouse_user_\d{2}", user_id) is None:
                raise ValueError("action-list user_id must use warehouse_user_NN format")
            if user_id in new_lists:
                raise ValueError(f"duplicate action-list user_id: {user_id}")
            raw_actions = raw_list.get("actions")
            if not isinstance(raw_actions, list) or not 3 <= len(raw_actions) <= 5:
                raise ValueError("actions must be a list containing 3 to 5 entries")
            new_lists[user_id] = [self._make_action(entry, new_equipment) for entry in raw_actions]
        self.equipment = new_equipment
        self.user_action_lists = new_lists

    @staticmethod
    def _validate_equipment_groups(equipment: Dict[str, Equipment]) -> None:
        if len(equipment) < 40:
            raise ValueError("each warehouse scenario must contain at least 40 equipment items")
        category_counts = Counter(item.category for item in equipment.values())
        generated_categories = {
            item.category for item in equipment.values() if not item.appears_in_video
        }
        if any(category_counts[value] < 5 for value in generated_categories):
            raise ValueError("every generated category must have at least 5 equipment items")
        for field_name in ("ideal_storage_location", "brand"):
            counts = Counter(getattr(item, field_name) for item in equipment.values())
            grouped_values = (
                {
                    getattr(item, field_name)
                    for item in equipment.values()
                    if not item.appears_in_video
                }
                if field_name == "ideal_storage_location"
                else set(counts)
            )
            if any(counts[value] < 3 for value in grouped_values):
                raise ValueError(f"every represented {field_name} must have at least 3 equipment items")
        brand_countries: Dict[str, set[str]] = {}
        for item in equipment.values():
            brand_countries.setdefault(item.brand, set()).add(item.country_of_origin)
        if any(len(countries) != 1 for countries in brand_countries.values()):
            raise ValueError("each brand must map to exactly one country of origin")

    @staticmethod
    def _make_equipment(raw: Dict[str, Any]) -> Equipment:
        name = raw.get("equipment")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("equipment must be a non-empty string")
        category = raw.get("category")
        if category not in EQUIPMENT_CATEGORIES:
            raise ValueError(f"invalid equipment category: {category}")
        appears_in_video = raw.get("appears_in_video")
        if not isinstance(appears_in_video, bool):
            raise ValueError("appears_in_video must be a boolean")
        brand, country = raw.get("brand"), raw.get("country_of_origin")
        for field_name, value in (("brand", brand), ("country_of_origin", country)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        purchase_date = raw.get("purchase_date")
        purchased_on = _parse_date(purchase_date, "purchase_date")
        if not DATA_START <= purchased_on <= DATA_CUTOFF:
            raise ValueError("purchase_date must be between 2016-08-20 and 2026-08-01")
        location = raw.get("ideal_storage_location")
        if location not in STORAGE_LOCATIONS:
            raise ValueError(f"invalid equipment storage location: {location}")
        usage = list(raw.get("usage_history", []))
        if len(usage) > 7 or len(set(usage)) != len(usage):
            raise ValueError("usage_history must contain at most 7 unique dates")
        for used_on in usage:
            usage_date = _parse_date(used_on, "usage date")
            if not purchased_on <= usage_date <= DATA_CUTOFF:
                raise ValueError("usage dates must be between purchase_date and 2026-08-01")
        if usage != sorted(usage):
            raise ValueError("usage_history must be ordered by date")
        instructions = raw.get("maintenance_and_usage_instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            raise ValueError("maintenance_and_usage_instructions must be a non-empty string")
        if "\n" in instructions or "\r" in instructions:
            raise ValueError("maintenance_and_usage_instructions must be one paragraph")
        instruction_text = instructions.lower()
        life_matches = re.findall(
            r"maximum service life is (\d+) years? from purchase\.$", instruction_text
        )
        if len(life_matches) != 1 or not 1 <= int(life_matches[0]) <= 10:
            raise ValueError(
                "maintenance_and_usage_instructions must end with one maximum service life "
                "from 1 to 10 years and no end-of-life action"
            )
        recommended_methods = re.findall(
            r"\b(clean|inspect|lubricate|calibrate|sharpen|condition) every \d+ months?\b",
            instruction_text,
        )
        if len(set(recommended_methods)) < 2:
            raise ValueError("maintenance_and_usage_instructions must recommend at least two maintenance methods")
        if not instruction_text.startswith("usage:"):
            raise ValueError("maintenance_and_usage_instructions must include a usage instruction")
        maintenance = [WarehouseDB._make_maintenance_record(record) for record in raw.get("maintenance_history", [])]
        if not 3 <= len(maintenance) <= 7:
            raise ValueError("maintenance_history must contain 3 to 7 records")
        if [record.date for record in maintenance] != sorted(record.date for record in maintenance):
            raise ValueError("maintenance_history must be ordered by date")
        for record in maintenance:
            maintained_on = _parse_date(record.date, "maintenance date")
            if not purchased_on <= maintained_on <= DATA_CUTOFF:
                raise ValueError("maintenance dates must be between purchase_date and 2026-08-01")
            if record.action not in recommended_methods:
                raise ValueError("maintenance action must appear in maintenance_and_usage_instructions")
        return Equipment(
            name, appears_in_video, category, brand, country, purchase_date, location,
            usage, instructions, maintenance,
        )

    @staticmethod
    def _make_maintenance_record(raw: Dict[str, Any]) -> MaintenanceRecord:
        if set(raw) != {"date", "action"}:
            raise ValueError("maintenance records must contain only date and action")
        record_date = raw.get("date")
        _parse_date(record_date, "maintenance date")
        action = raw.get("action")
        if action not in MAINTENANCE_ACTIONS:
            raise ValueError(f"invalid equipment maintenance action: {action}")
        return MaintenanceRecord(record_date, action)

    @staticmethod
    def _make_action(raw: Dict[str, Any], equipment: Dict[str, Equipment]) -> EquipmentAction:
        name = raw.get("equipment")
        if name not in equipment:
            raise ValueError(f"unknown equipment: {name}")
        action = raw.get("required_action")
        if action not in EQUIPMENT_ACTIONS:
            raise ValueError(f"invalid equipment required action: {action}")
        due_date = raw.get("due_date")
        _parse_date(due_date, "due_date")
        if action in MAINTENANCE_ACTIONS:
            instruction_text = equipment[name].maintenance_and_usage_instructions.lower()
            prescribed = re.search(rf"\b{re.escape(action)} every \d+ months?\b", instruction_text)
            if prescribed is None:
                raise ValueError("maintenance action must be prescribed in the equipment's instructions")
        return EquipmentAction(name, action, due_date)

    def _equipment(self, equipment: str) -> Equipment:
        try:
            return self.equipment[equipment]
        except KeyError as exc:
            raise ValueError(f"equipment not found: {equipment}") from exc

    def get_all_equipment(self) -> List[str]:
        return list(self.equipment)

    def get_equipment_category(self, equipment: str) -> str:
        return self._equipment(equipment).category

    def find_equipment_by_category(self, category: str) -> List[str]:
        if category not in EQUIPMENT_CATEGORIES:
            raise ValueError(f"invalid equipment category: {category}")
        return [item.equipment for item in self.equipment.values() if item.category == category]

    def get_equipment_brand(self, equipment: str) -> str:
        return self._equipment(equipment).brand

    def find_equipment_by_brand(self, brand: str) -> List[str]:
        return [item.equipment for item in self.equipment.values() if item.brand == brand]

    def get_equipment_country_of_origin(self, equipment: str) -> str:
        return self._equipment(equipment).country_of_origin

    def find_equipment_by_country_of_origin(self, country: str) -> List[str]:
        return [item.equipment for item in self.equipment.values() if item.country_of_origin == country]

    def get_equipment_purchase_date(self, equipment: str) -> str:
        return self._equipment(equipment).purchase_date

    def find_equipment_by_purchase_date_range(self, start_date: str, end_date: str) -> List[str]:
        start, end = _parse_date(start_date, "start_date"), _parse_date(end_date, "end_date")
        if start > end:
            raise ValueError("start_date cannot be later than end_date")
        return [item.equipment for item in self.equipment.values()
                if start <= _parse_date(item.purchase_date, "purchase_date") <= end]

    def get_equipment_ideal_storage_location(self, equipment: str) -> str:
        return self._equipment(equipment).ideal_storage_location

    def find_equipment_by_ideal_storage_location(self, location: str) -> List[str]:
        if location not in STORAGE_LOCATIONS:
            raise ValueError(f"invalid equipment storage location: {location}")
        return [item.equipment for item in self.equipment.values() if item.ideal_storage_location == location]

    def get_equipment_usage_history(self, equipment: str) -> List[str]:
        return list(self._equipment(equipment).usage_history)

    def get_equipment_maintenance_and_usage_instructions(
        self, equipment: List[str]
    ) -> Dict[str, str]:
        if not isinstance(equipment, list) or not equipment:
            raise ValueError("equipment must be a non-empty list of equipment names")
        if any(not isinstance(name, str) or not name for name in equipment):
            raise ValueError("equipment must contain only non-empty strings")
        return {
            name: self._equipment(name).maintenance_and_usage_instructions
            for name in equipment
        }

    def get_equipment_maintenance_history(self, equipment: str) -> List[Dict[str, str]]:
        return [asdict(record) for record in self._equipment(equipment).maintenance_history]

    def add_to_equipment_action_list(
        self, user_id: str, equipment: str, required_action: str, due_date: str
    ) -> Dict[str, str]:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        self._equipment(equipment)
        action = self._make_action(
            {"equipment": equipment, "required_action": required_action, "due_date": due_date}, self.equipment
        )
        actions = self.user_action_lists.setdefault(user_id, [])
        actions.append(action)
        return {"message": "Equipment action added successfully."}

    def remove_from_equipment_action_list(
        self, user_id: str, equipment: str, required_action: str, due_date: str
    ) -> Dict[str, str]:
        if required_action not in EQUIPMENT_ACTIONS:
            raise ValueError(f"invalid equipment required action: {required_action}")
        _parse_date(due_date, "due_date")
        actions = self.user_action_lists.get(user_id, [])
        for index, action in enumerate(actions):
            if (
                action.equipment == equipment
                and action.required_action == required_action
                and action.due_date == due_date
            ):
                actions.pop(index)
                return {"message": "Equipment action removed successfully."}
        raise ValueError("matching equipment action was not found")

    def get_equipment_action_list(self, user_id: str) -> List[Dict[str, str]]:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        return [asdict(action) for action in deepcopy(self.user_action_lists.get(user_id, []))]
