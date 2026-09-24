"""In-memory database and tool implementations for the household scenario."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional


ITEM_CATEGORIES = {
    "furniture", "tableware", "cookware", "bedding", "clothing", "footwear",
    "home_textile", "storage_item", "home_appliance", "electronics", "lighting",
    "decoration", "cleaning_item", "daily_supply", "other",
}
STORAGE_LOCATIONS = {
    "living_room", "dining_room", "bedroom", "study", "wardrobe", "linen_closet",
    "shoe_cabinet", "kitchen_cabinet", "pantry", "bathroom_cabinet", "laundry_area",
    "storage_room", "bookshelf", "display_shelf", "balcony", "garage",
}
MAINTENANCE_ACTIONS = {"clean", "condition", "disinfect", "wash", "inspect"}
HOUSEHOLD_ACTIONS = MAINTENANCE_ACTIONS | {
    "repair", "relocate", "dry", "iron", "replace", "dispose",
}
DATA_START = date(2016, 8, 20)
DATA_CUTOFF = date(2026, 8, 1)


def _parse_date(value: str, field_name: str) -> date:
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
class HouseholdItem:
    name: str
    appears_in_video: bool
    category: str
    ideal_storage_location: str
    purchase_date: Optional[str]
    purchase_price: float
    usage_history: List[str]
    maintenance_history: List[MaintenanceRecord]
    care_and_usage_instructions: str


@dataclass(frozen=True)
class HouseholdAction:
    name: str
    required_action: str
    due_date: str


class HouseholdDB:
    """Store household item profiles and per-user household action lists."""

    def __init__(self) -> None:
        self.items: Dict[str, HouseholdItem] = {}
        self.user_action_lists: Dict[str, List[HouseholdAction]] = {}

    def init_from_json(self, data: Dict[str, Any]) -> None:
        """Replace all current state with validated dictionary data."""
        new_items: Dict[str, HouseholdItem] = {}
        for raw in data.get("items", []):
            item = self._make_item(raw)
            if item.name in new_items:
                raise ValueError(f"duplicate household item name: {item.name}")
            new_items[item.name] = item
        self._validate_item_groups(new_items)

        new_lists: Dict[str, List[HouseholdAction]] = {}
        raw_action_lists = data.get("household_action_lists", [])
        if not isinstance(raw_action_lists, list) or not 3 <= len(raw_action_lists) <= 5:
            raise ValueError("household_action_lists must contain 3 to 5 users")
        for raw_list in raw_action_lists:
            if set(raw_list) != {"user_id", "actions"}:
                raise ValueError("each household action list must contain only user_id and actions")
            user_id = raw_list.get("user_id")
            if not isinstance(user_id, str) or re.fullmatch(r"household_user_\d{2}", user_id) is None:
                raise ValueError("action-list user_id must use household_user_NN format")
            if user_id in new_lists:
                raise ValueError(f"duplicate action-list user_id: {user_id}")
            raw_actions = raw_list.get("actions")
            if not isinstance(raw_actions, list) or not 3 <= len(raw_actions) <= 5:
                raise ValueError("actions must be a list containing 3 to 5 entries")
            actions = [self._make_action(entry, new_items) for entry in raw_actions]
            new_lists[user_id] = actions

        self.items = new_items
        self.user_action_lists = new_lists

    @staticmethod
    def _validate_item_groups(items: Dict[str, HouseholdItem]) -> None:
        if len(items) < 40:
            raise ValueError("each household scenario must contain at least 40 items")
        # Video annotations are authoritative and may legitimately contain a
        # singleton category.  Coverage minima apply only to synthetic records;
        # padding a source category would reintroduce semantically confusable
        # generated objects.
        generated_items = [
            item for item in items.values() if not item.appears_in_video
        ]
        category_counts = Counter(item.category for item in generated_items)
        if category_counts and min(category_counts.values()) < 5:
            raise ValueError("every generated category must have at least 5 household items")
        for field_name in ("ideal_storage_location",):
            counts = Counter(
                getattr(item, field_name) for item in generated_items
            )
            if counts and min(counts.values()) < 3:
                raise ValueError(
                    f"every generated {field_name} must have at least 3 household items"
                )

    def _make_item(self, raw: Dict[str, Any]) -> HouseholdItem:
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("item name must be a non-empty string")
        category = raw.get("category")
        if category not in ITEM_CATEGORIES:
            raise ValueError(f"invalid household item category: {category}")
        appears_in_video = raw.get("appears_in_video")
        if not isinstance(appears_in_video, bool):
            raise ValueError("appears_in_video must be a boolean")
        location = raw.get("ideal_storage_location")
        if location not in STORAGE_LOCATIONS:
            raise ValueError(f"invalid household storage location: {location}")
        purchase_date = raw.get("purchase_date")
        if purchase_date is not None:
            purchased_on = _parse_date(purchase_date, "purchase_date")
            if not DATA_START <= purchased_on <= DATA_CUTOFF:
                raise ValueError("purchase_date must be between 2016-08-20 and 2026-08-01")
        price = raw.get("purchase_price")
        if not isinstance(price, (int, float)) or isinstance(price, bool) or price < 0:
            raise ValueError("purchase_price must be a non-negative number")

        usage_history = list(raw.get("usage_history", []))
        self._validate_usage_history(usage_history, purchase_date)
        instructions = raw.get("care_and_usage_instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            raise ValueError("care_and_usage_instructions must be non-empty")
        instruction_text = instructions.lower()
        recommended_methods = re.findall(
            r"\b(clean|condition|disinfect|wash|inspect) every \d+ (?:days?|months?)\b",
            instruction_text,
        )
        if len(set(recommended_methods)) < 2:
            raise ValueError("care_and_usage_instructions must recommend at least two maintenance methods")
        life_matches = re.findall(
            r"maximum service life is (\d+) years? from purchase\.$", instruction_text
        )
        if len(life_matches) != 1 or not 1 <= int(life_matches[0]) <= 10:
            raise ValueError(
                "care_and_usage_instructions must end with one maximum service life "
                "from 1 to 10 years and no end-of-life action"
            )
        maintenance = [self._make_maintenance_record(record) for record in raw.get("maintenance_history", [])]
        if not 3 <= len(maintenance) <= 7:
            raise ValueError("maintenance_history must contain 3 to 7 records")
        if [record.date for record in maintenance] != sorted(record.date for record in maintenance):
            raise ValueError("maintenance_history must be ordered by date")
        for record in maintenance:
            maintained_on = _parse_date(record.date, "maintenance date")
            if purchase_date is not None and maintained_on < purchased_on:
                raise ValueError("maintenance date cannot be earlier than purchase_date")
            if maintained_on > DATA_CUTOFF:
                raise ValueError("maintenance date cannot be later than 2026-08-01")
            if record.action not in recommended_methods:
                raise ValueError("maintenance action must appear in care_and_usage_instructions")
        return HouseholdItem(
            name=name, appears_in_video=appears_in_video, category=category,
            ideal_storage_location=location,
            purchase_date=purchase_date, purchase_price=float(price),
            usage_history=usage_history, maintenance_history=maintenance,
            care_and_usage_instructions=instructions,
        )

    @staticmethod
    def _make_maintenance_record(raw: Dict[str, Any]) -> MaintenanceRecord:
        if set(raw) != {"date", "action"}:
            raise ValueError("maintenance records must contain only date and action")
        record_date = raw.get("date")
        _parse_date(record_date, "maintenance date")
        action = raw.get("action")
        if action not in MAINTENANCE_ACTIONS:
            raise ValueError(f"invalid household maintenance action: {action}")
        return MaintenanceRecord(record_date, action)

    @staticmethod
    def _validate_usage_history(history: List[str], purchase_date: Optional[str]) -> None:
        if len(history) > 7:
            raise ValueError("usage_history may contain at most 7 ranges")
        previous_end: Optional[date] = None
        for value in history:
            if not isinstance(value, str) or value.count("/") != 1:
                raise ValueError("usage ranges must use START/END format")
            start_text, end_text = value.split("/")
            if start_text == "PURCHASE_DATE":
                if purchase_date is None:
                    raise ValueError("PURCHASE_DATE cannot be used when purchase_date is null")
                start = _parse_date(purchase_date, "purchase_date")
            else:
                start = _parse_date(start_text, "usage start")
            if purchase_date is not None and start < _parse_date(purchase_date, "purchase_date"):
                raise ValueError("usage range cannot start before purchase_date")
            if start > DATA_CUTOFF:
                raise ValueError("usage range cannot start after 2026-08-01")
            end = date.max if end_text == "PRESENT" else _parse_date(end_text, "usage end")
            if end_text != "PRESENT" and end > DATA_CUTOFF:
                raise ValueError("usage range cannot end after 2026-08-01")
            if start > end:
                raise ValueError("usage range start cannot be later than its end")
            if previous_end is not None and start <= previous_end:
                raise ValueError("usage ranges must be ordered and non-overlapping")
            previous_end = end

    @staticmethod
    def _make_action(raw: Dict[str, Any], items: Dict[str, HouseholdItem]) -> HouseholdAction:
        name = raw.get("name")
        if name not in items:
            raise ValueError(f"unknown household item: {name}")
        action = raw.get("required_action")
        if action not in HOUSEHOLD_ACTIONS:
            raise ValueError(f"invalid household required action: {action}")
        due_date = raw.get("due_date")
        _parse_date(due_date, "due_date")
        return HouseholdAction(name, action, due_date)

    def _item(self, item_name: str) -> HouseholdItem:
        try:
            return self.items[item_name]
        except KeyError as exc:
            raise ValueError(f"household item not found: {item_name}") from exc

    def get_all_item_names(self) -> List[str]:
        return list(self.items)

    def get_item_category(self, item_name: str) -> str:
        return self._item(item_name).category

    def find_items_by_category(self, category: str) -> List[str]:
        if category not in ITEM_CATEGORIES:
            raise ValueError(f"invalid household item category: {category}")
        return [item.name for item in self.items.values() if item.category == category]

    def get_item_ideal_storage_location(self, item_name: str) -> str:
        return self._item(item_name).ideal_storage_location

    def find_items_by_ideal_storage_location(self, location: str) -> List[str]:
        if location not in STORAGE_LOCATIONS:
            raise ValueError(f"invalid household storage location: {location}")
        return [item.name for item in self.items.values() if item.ideal_storage_location == location]

    def get_item_purchase_date(self, item_name: str) -> Optional[str]:
        return self._item(item_name).purchase_date

    def find_items_by_purchase_date_range(self, start_date: str, end_date: str) -> List[str]:
        start, end = _parse_date(start_date, "start_date"), _parse_date(end_date, "end_date")
        if start > end:
            raise ValueError("start_date cannot be later than end_date")
        return [item.name for item in self.items.values()
                if item.purchase_date is not None and start <= _parse_date(item.purchase_date, "purchase_date") <= end]

    def get_item_purchase_price(self, item_name: str) -> float:
        return self._item(item_name).purchase_price

    def find_items_by_purchase_price_range(self, min_price: float, max_price: float) -> List[str]:
        if min_price < 0 or max_price < 0 or min_price > max_price:
            raise ValueError("prices must be non-negative and min_price cannot exceed max_price")
        return [item.name for item in self.items.values() if min_price <= item.purchase_price <= max_price]

    def get_item_usage_history(self, item_name: str) -> List[str]:
        return list(self._item(item_name).usage_history)

    def find_items_used_during_date_range(self, start_date: str, end_date: str) -> List[str]:
        query_start, query_end = _parse_date(start_date, "start_date"), _parse_date(end_date, "end_date")
        if query_start > query_end:
            raise ValueError("start_date cannot be later than end_date")
        matches: List[str] = []
        for item in self.items.values():
            for value in item.usage_history:
                start_text, end_text = value.split("/")
                actual_start = item.purchase_date if start_text == "PURCHASE_DATE" else start_text
                range_start = _parse_date(actual_start, "usage start")
                range_end = date.today() if end_text == "PRESENT" else _parse_date(end_text, "usage end")
                if range_start <= query_end and query_start <= range_end:
                    matches.append(item.name)
                    break
        return matches

    def get_item_maintenance_history(self, item_name: str) -> List[Dict[str, str]]:
        return [asdict(record) for record in self._item(item_name).maintenance_history]

    def get_item_maintenance_and_usage_instructions(
        self, item_name: List[str]
    ) -> Dict[str, str]:
        if not isinstance(item_name, list) or not item_name:
            raise ValueError("item_name must be a non-empty list of household item names")
        if any(not isinstance(name, str) or not name for name in item_name):
            raise ValueError("item_name must contain only non-empty strings")
        return {
            name: self._item(name).care_and_usage_instructions
            for name in item_name
        }

    def add_to_household_action_list(
        self, user_id: str, name: str, required_action: str, due_date: str
    ) -> Dict[str, str]:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        self._item(name)
        action = self._make_action(
            {"name": name, "required_action": required_action, "due_date": due_date}, self.items
        )
        actions = self.user_action_lists.setdefault(user_id, [])
        actions.append(action)
        return {"message": "Household action added successfully."}

    def remove_from_household_action_list(
        self, user_id: str, name: str, required_action: str, due_date: str
    ) -> Dict[str, str]:
        if required_action not in HOUSEHOLD_ACTIONS:
            raise ValueError(f"invalid household required action: {required_action}")
        _parse_date(due_date, "due_date")
        actions = self.user_action_lists.get(user_id, [])
        for index, action in enumerate(actions):
            if (
                action.name == name
                and action.required_action == required_action
                and action.due_date == due_date
            ):
                actions.pop(index)
                return {"message": "Household action removed successfully."}
        raise ValueError("matching household action was not found")

    def get_household_action_list(self, user_id: str) -> List[Dict[str, str]]:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        return [asdict(action) for action in deepcopy(self.user_action_lists.get(user_id, []))]
