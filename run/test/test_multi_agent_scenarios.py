import tempfile
import unittest
from pathlib import Path

from run.multi_agent import (
    SCENARIO_NUMBER_RANGES,
    _create_household_db,
    resolve_video_path,
)
from tools.household.household_db import HouseholdDB


class MultiAgentScenarioTest(unittest.TestCase):
    def test_restaurant6_is_a_restaurant_variant(self):
        self.assertEqual((1, 6), SCENARIO_NUMBER_RANGES["restaurant"])
        self.assertNotIn("restaurant6", SCENARIO_NUMBER_RANGES)

    def test_household_variants_can_be_initialized(self):
        self.assertEqual((1, 18), SCENARIO_NUMBER_RANGES["household"])
        for scenario_number in (1, 18):
            database = _create_household_db(scenario_number)
            self.assertIsInstance(database, HouseholdDB)
            self.assertGreaterEqual(len(database.items), 40)

    def test_legacy_video_url_resolves_against_local_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir, "restaurant5.mp4")
            video.write_bytes(b"video")

            resolved = resolve_video_path(
                "https://legacy.invalid/media/restaurant5.MOV",
                temp_dir,
            )

            self.assertEqual(video, Path(resolved))


if __name__ == "__main__":
    unittest.main()
