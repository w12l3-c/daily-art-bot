import unittest

from artbot.DiscordMessageSender import DiscordMessageSender


class DiscordMessageSenderTest(unittest.TestCase):
    def test_split_message_keeps_chunks_under_safe_limit(self) -> None:
        sender = DiscordMessageSender()
        message = "x" * 5000

        chunks = sender.split_message(message)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= sender.safe_message_limit for chunk in chunks))
        self.assertEqual(message, "".join(chunks))

    def test_split_message_preserves_line_content(self) -> None:
        sender = DiscordMessageSender()
        message = "\n".join(f"line {index}" for index in range(500))

        chunks = sender.split_message(message)

        normalized_chunks = "".join(chunks).replace(sender.markdown_break, "")
        self.assertEqual(message, normalized_chunks)


if __name__ == "__main__":
    unittest.main()
