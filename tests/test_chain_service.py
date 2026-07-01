from datetime import datetime
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import artbot.shared
from artbot.core.chain.ChainService import ChainService, ChainStatus


class FakeChannel:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


class FakeResponse:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def read(self) -> bytes:
        return b"image-bytes"


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    def get(self, url: str) -> FakeResponse:
        return FakeResponse()


class FakeInteractionResponse:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send_message(self, message: str, ephemeral: bool = False) -> None:
        self.messages.append(message)


class FakeInteraction:
    def __init__(self, user_id: int) -> None:
        self.user = SimpleNamespace(id=user_id)
        self.response = FakeInteractionResponse()


class ChainServiceTest(unittest.IsolatedAsyncioTestCase):
    def add_chain(self, service: ChainService, chain_id: str, name: str) -> None:
        service.active_chains[chain_id] = {
            "id": chain_id,
            "name": name,
            "creator": 123,
            "creator_name": "artist",
            "target_amount": 3,
            "current_count": 0,
            "status": ChainStatus.ACTIVE,
            "created_at": datetime.now(),
            "participants": [],
            "submissions": [],
        }
        service.chain_submissions[chain_id] = []

    async def test_selected_chain_allows_multiple_submissions_from_same_user(self) -> None:
        service = ChainService()
        service.set_tracked_users_reference({123: {"user_nickname": "artist"}})
        chain_id = "sketch_1"
        self.add_chain(service, chain_id, "sketch")
        service.selected_chains[123] = {
            "chain_id": chain_id,
            "chain_name": "sketch",
            "timestamp": datetime.now(),
        }
        channel = FakeChannel()
        message = SimpleNamespace(
            id=1,
            author=SimpleNamespace(id=123, name="artist"),
            channel=channel,
        )
        attachment = SimpleNamespace(url="https://example.test/image.png", filename="image.png")

        with patch("artbot.core.chain.ChainService.aiohttp.ClientSession", FakeSession):
            first_result = await service.process_chain_submission(123, message, attachment)
            second_result = await service.process_chain_submission(123, message, attachment)

        self.assertTrue(first_result)
        self.assertTrue(second_result)
        self.assertEqual(2, service.active_chains[chain_id]["current_count"])
        self.assertEqual([123], service.active_chains[chain_id]["participants"])
        self.assertEqual(2, len(service.chain_submissions[chain_id]))
        self.assertIn(123, service.selected_chains)

    async def test_chain_on_switches_selected_chain_for_user(self) -> None:
        service = ChainService()
        service.set_tracked_users_reference({123: {"user_nickname": "artist"}})
        self.add_chain(service, "sketch_1", "sketch")
        self.add_chain(service, "paint_1", "paint")
        service.selected_chains[123] = {
            "chain_id": "sketch_1",
            "chain_name": "sketch",
            "timestamp": datetime.now(),
        }
        interaction = FakeInteraction(123)

        await service.chain_on_command(interaction, "paint")

        self.assertEqual("paint_1", service.selected_chains[123]["chain_id"])
        self.assertEqual("paint", service.selected_chains[123]["chain_name"])
        self.assertEqual([], service.chain_submissions["sketch_1"])
        self.assertIn("Switched from 'sketch' to 'paint'", interaction.response.messages[0])

    async def test_chain_off_clears_selected_chain_for_user(self) -> None:
        service = ChainService()
        service.selected_chains[123] = {
            "chain_id": "sketch_1",
            "chain_name": "sketch",
            "timestamp": datetime.now(),
        }
        interaction = FakeInteraction(123)

        await service.chain_off_command(interaction)

        self.assertNotIn(123, service.selected_chains)
        self.assertIn("Turned off chain submissions", interaction.response.messages[0])

    async def test_chain_start_stores_gif_fps(self) -> None:
        service = ChainService()
        service.set_tracked_users_reference({123: {"user_nickname": "artist"}})
        interaction = FakeInteraction(123)

        with patch("artbot.shared.send_interaction_message") as send_message:
            await service.chain_start_command(interaction, "sketch", 3, fps=2.5)

        chain = next(iter(service.active_chains.values()))
        self.assertEqual(2.5, chain["fps"])
        self.assertEqual(400, service.get_frame_duration_ms(chain["fps"]))
        send_message.assert_called_once()
        self.assertIn("2.5 FPS", send_message.call_args.args[1])

    async def test_chain_start_rejects_invalid_fps(self) -> None:
        service = ChainService()
        service.set_tracked_users_reference({123: {"user_nickname": "artist"}})
        interaction = FakeInteraction(123)

        await service.chain_start_command(interaction, "sketch", 3, fps=20)

        self.assertEqual({}, service.active_chains)
        self.assertIn("Chain FPS must be between", interaction.response.messages[0])


if __name__ == "__main__":
    unittest.main()
