import discord


class DiscordMessageSender:
    message_limit = 2000
    safe_message_limit = 1900
    markdown_break = "\n\u200b\n"

    def split_message(self, message: str, max_length: int | None = None) -> list[str]:
        max_length = max_length or self.safe_message_limit
        if len(message) <= max_length:
            return [message]

        chunks = []
        current_chunk = ""

        for line in message.splitlines(keepends=True):
            if len(line) > max_length:
                if current_chunk:
                    chunks.append(self._with_markdown_break(current_chunk, max_length))
                    current_chunk = ""
                for start in range(0, len(line), max_length):
                    chunk = line[start:start + max_length]
                    if chunk:
                        chunks.append(chunk)
                continue

            if len(current_chunk) + len(line) > max_length:
                chunks.append(self._with_markdown_break(current_chunk, max_length))
                current_chunk = line
            else:
                current_chunk += line

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def send_channel(self, destination, message: str, **kwargs) -> list[discord.Message]:
        sent_messages = []
        chunks = self.split_message(message)
        for index, chunk in enumerate(chunks):
            send_kwargs = kwargs if index == 0 else {}
            sent_messages.append(await destination.send(chunk, **send_kwargs))
        return sent_messages

    async def send_interaction(
        self,
        interaction: discord.Interaction,
        message: str,
        ephemeral: bool = False,
        **kwargs,
    ) -> None:
        chunks = self.split_message(message)
        await interaction.response.send_message(
            chunks[0],
            ephemeral=ephemeral,
            **kwargs,
        )
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk, ephemeral=ephemeral)

    async def send_followup(
        self,
        interaction: discord.Interaction,
        message: str,
        ephemeral: bool = False,
        **kwargs,
    ) -> None:
        chunks = self.split_message(message)
        for index, chunk in enumerate(chunks):
            send_kwargs = kwargs if index == 0 else {}
            await interaction.followup.send(
                chunk,
                ephemeral=ephemeral,
                **send_kwargs,
            )

    def _with_markdown_break(self, chunk: str, max_length: int) -> str:
        if len(chunk) + len(self.markdown_break) <= max_length:
            return chunk + self.markdown_break
        return chunk
