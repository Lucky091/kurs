import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from systems.persistence import DEFAULT_SETTINGS, LeaderboardDB, SettingsStore, data_directory


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def database(self):
        database = LeaderboardDB(self.root / "nested/scores.sqlite3")
        self.addCleanup(database.close)
        return database

    def test_empty_database_and_score_survives_reopen(self):
        database = self.database()
        self.assertEqual(database.top_scores(), [])
        self.assertTrue(database.save_score("run-1", "Алексей", 42, 3))
        another = LeaderboardDB(database.path)
        self.addCleanup(another.close)
        entry = another.top_scores()[0]
        self.assertEqual(entry["name"], "Алексей")
        self.assertEqual((entry["score"], entry["wave"]), (42, 3))
        self.assertRegex(entry["played_at"], r"\d{4}-\d{2}-\d{2}T")

    def test_result_saved_once_and_empty_name_uses_pilot(self):
        database = self.database()
        self.assertTrue(database.save_score("same-run", "  ", 30, 1))
        self.assertFalse(database.save_score("same-run", "Changed", 900, 10))
        self.assertEqual(len(database.top_scores()), 1)
        self.assertEqual(database.top_scores()[0]["name"], "Пилот")
        self.assertEqual(database.top_scores()[0]["score"], 30)

    def test_sql_input_is_data_and_top_ten_have_correct_order(self):
        database = self.database()
        name = "'; DROP TABLE scores;--"
        database.save_score("injection", name, 200, 2)
        for i in range(12):
            database.save_score(str(i), "Пилот " + str(i), i * 10, 1)
        database.save_score("tie", "Ветеран", 200, 4)
        entries = database.top_scores()
        self.assertEqual(len(entries), 10)
        self.assertEqual(entries[0]["name"], "Ветеран")
        self.assertEqual(entries[1]["name"], name)
        self.assertEqual(entries[2]["score"], 110)
        self.assertEqual(database.top_scores(0), [])

    def test_corrupt_file_and_typed_invalid_values_use_safe_defaults(self):
        store = SettingsStore(self.root / "settings.json")
        self.assertEqual(store.load(), DEFAULT_SETTINGS)
        store.path.write_text("{invalid json", encoding="utf-8")
        self.assertEqual(store.load(), DEFAULT_SETTINGS)
        store.path.write_text(json.dumps({"music_volume": "loud", "effects_volume": True,
                                          "particles": float("nan"),
                                          "fullscreen": 1, "camera_shake": "yes"}),
                              encoding="utf-8")
        self.assertEqual(store.load(), DEFAULT_SETTINGS)

    def test_settings_are_clamped_and_round_trip(self):
        store = SettingsStore(self.root / "nested/settings.json")
        store.save({"music_volume": 5, "effects_volume": -2, "particles": .5,
                    "fullscreen": True, "camera_shake": False})
        self.assertEqual(store.load(), {"music_volume": 1., "effects_volume": 0.,
                                       "particles": .5, "fullscreen": True,
                                       "camera_shake": False})
        self.assertEqual(list(store.path.parent.glob("*.tmp")), [])

    def test_data_dir_override_is_used_for_both_stores(self):
        with patch.dict(os.environ, {"STAR_FRONTIER_DATA_DIR": str(self.root)}):
            self.assertEqual(data_directory(), self.root)
            self.assertEqual(SettingsStore().path.parent, self.root)
            database = LeaderboardDB()
            self.addCleanup(database.close)
            self.assertEqual(database.path.parent, self.root)


if __name__ == "__main__":
    unittest.main()
