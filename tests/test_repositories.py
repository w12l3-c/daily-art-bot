import json
import tempfile
import unittest
from pathlib import Path

from artbot.persistence.DailyStateRepository import DailyStateRepository
from artbot.persistence.WcwStateRepository import WcwStateRepository


class RepositoryTest(unittest.TestCase):
    def test_daily_state_round_trip_preserves_shape(self) -> None:
        data = {
            "current_day": 1,
            "season": 7,
            "tracked_users": {"123": {"username": "artist"}},
            "allowed_channels": [456],
            "duel": {"pending_duels": {}, "active_duels": {}},
            "chain": {"active_chains": {}, "chain_submissions": {}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backup.json"
            repository = DailyStateRepository(path)

            repository.save(data)

            self.assertEqual(data, repository.load())
            self.assertEqual(data, json.loads(path.read_text()))

    def test_wcw_state_round_trip_preserves_shape(self) -> None:
        data = {
            "current_week": 21,
            "announcement_channel": 123,
            "allowed_channels": [123, 456],
            "tracked_users": {"789": {"username": "writer", "status": "pending"}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "wcw.json"
            repository = WcwStateRepository(path)

            repository.save(data)

            self.assertEqual(data, repository.load())
            self.assertEqual(data, json.loads(path.read_text()))


if __name__ == "__main__":
    unittest.main()
