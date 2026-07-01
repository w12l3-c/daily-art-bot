"""
ChainService.py
This file contains the art-chain service and compatibility functions.
"""

import io
import logging
import os
from datetime import datetime

import aiohttp
import discord
from PIL import Image
import artbot.shared as shared

logger = logging.getLogger(__name__)

DEFAULT_CHAIN_FPS = 1.0
MIN_CHAIN_FPS = 0.2
MAX_CHAIN_FPS = 10.0


class ChainStatus:
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ChainService:
    def __init__(self) -> None:
        self.active_chains: dict[str, dict] = {}
        self.chain_submissions: dict[str, list[dict]] = {}
        self.selected_chains: dict[int, dict] = {}
        self._tracked_users_ref: dict[int, dict] = {}

    def get_tracked_users(self) -> dict[int, dict]:
        return self._tracked_users_ref

    def set_tracked_users_reference(self, tracked_users_ref: dict[int, dict]) -> None:
        self._tracked_users_ref = tracked_users_ref

    async def chain_start_command(
        self,
        interaction: discord.Interaction,
        name: str,
        amount: int,
        fps: float = DEFAULT_CHAIN_FPS,
    ) -> None:
        user_id = interaction.user.id
        tracked_users = self.get_tracked_users()

        if user_id not in tracked_users:
            await interaction.response.send_message("❌ You are not in the art tracking system.", ephemeral=True)
            return

        if amount < 2 or amount > 50:
            await interaction.response.send_message("❌ Chain amount must be between 2 and 50 submissions.", ephemeral=True)
            return

        if fps < MIN_CHAIN_FPS or fps > MAX_CHAIN_FPS:
            await interaction.response.send_message(
                f"❌ Chain FPS must be between {MIN_CHAIN_FPS} and {MAX_CHAIN_FPS}.",
                ephemeral=True,
            )
            return

        if name.lower() in [chain["name"].lower() for chain in self.active_chains.values()]:
            await interaction.response.send_message(f"❌ A chain with the name '{name}' already exists.", ephemeral=True)
            return

        chain_id = f"{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"
        chain_data = {
            "id": chain_id,
            "name": name,
            "creator": user_id,
            "creator_name": tracked_users[user_id]["user_nickname"],
            "target_amount": amount,
            "current_count": 0,
            "status": ChainStatus.ACTIVE,
            "created_at": datetime.now(),
            "participants": [],
            "submissions": [],
            "fps": fps,
        }

        self.active_chains[chain_id] = chain_data
        self.chain_submissions[chain_id] = []

        chain_message = (
            f"🔗 **NEW ART CHAIN STARTED** 🔗\n\n"
            f"**Chain Name:** {name}\n"
            f"**Creator:** {chain_data['creator_name']}\n"
            f"**Target:** {amount} submissions\n"
            f"**GIF Speed:** {fps:g} FPS\n"
            f"**Progress:** 0/{amount}\n\n"
            f"Use `/chain_on {name}` once, then tag uploads with `#chain` to add them to the chain!\n"
            f"When we reach {amount} submissions, all images will be compiled into a GIF! 🎬"
        )

        from artbot.shared import send_interaction_message

        await send_interaction_message(interaction, chain_message)
        logger.info("Chain started: '%s' by %s (target: %s)", name, chain_data["creator_name"], amount)

    async def chain_on_command(self, interaction: discord.Interaction, name: str) -> None:
        user_id = interaction.user.id
        tracked_users = self.get_tracked_users()

        if user_id not in tracked_users:
            await interaction.response.send_message("❌ You are not in the art tracking system.", ephemeral=True)
            return

        chain_id, chain_data = self.find_chain(name)
        if not chain_data:
            await interaction.response.send_message(f"❌ No active chain found with the name '{name}'.", ephemeral=True)
            return

        if chain_data["status"] != ChainStatus.ACTIVE:
            await interaction.response.send_message(f"❌ The chain '{name}' is no longer active.", ephemeral=True)
            return

        if chain_data["current_count"] >= chain_data["target_amount"]:
            await interaction.response.send_message(f"❌ The chain '{name}' has already reached its target!", ephemeral=True)
            return

        previous_selection = self.selected_chains.get(user_id)
        previous_chain_name = previous_selection["chain_name"] if previous_selection else None
        is_switching_chains = previous_chain_name is not None and previous_selection["chain_id"] != chain_id

        self.selected_chains[user_id] = {
            "chain_id": chain_id,
            "chain_name": name,
            "timestamp": datetime.now(),
        }

        selection_message = f"🔗 The '{name}' chain is now selected. "
        if is_switching_chains:
            selection_message = f"🔗 Switched from '{previous_chain_name}' to '{name}'. "

        await interaction.response.send_message(
            selection_message +
            f"Upload images with the tag `#chain` to keep adding to this chain.\n"
            f"**Current progress:** {chain_data['current_count']}/{chain_data['target_amount']}"
        )

    async def chain_off_command(self, interaction: discord.Interaction) -> None:
        user_id = interaction.user.id

        selected_chain = self.selected_chains.pop(user_id, None)
        if not selected_chain:
            await interaction.response.send_message("❌ You do not have a selected chain.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"🔗 Turned off chain submissions for '{selected_chain['chain_name']}'.",
            ephemeral=True,
        )

    async def process_chain_submission(self, user_id: int, message, attachment) -> bool:
        tracked_users = self.get_tracked_users()

        if user_id not in self.selected_chains:
            await message.channel.send(f"❌ {message.author.name}, you need to use `/chain_on <name>` first before submitting to a chain.")
            return False

        selected_chain = self.selected_chains[user_id]
        chain_id = selected_chain["chain_id"]

        if chain_id not in self.active_chains:
            del self.selected_chains[user_id]
            await message.channel.send(f"❌ {message.author.name}, the chain no longer exists.")
            return False

        chain_data = self.active_chains[chain_id]

        if chain_data["status"] != ChainStatus.ACTIVE:
            del self.selected_chains[user_id]
            await message.channel.send(f"❌ {message.author.name}, the chain '{chain_data['name']}' is no longer active.")
            return False

        if chain_data["current_count"] >= chain_data["target_amount"]:
            del self.selected_chains[user_id]
            await message.channel.send(f"❌ {message.author.name}, the chain '{chain_data['name']}' has already reached its target!")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status != 200:
                        return False

                    image_data = await resp.read()
                    submission_data = {
                        "user_id": user_id,
                        "user_name": tracked_users[user_id]["user_nickname"],
                        "message_id": message.id,
                        "image_data": image_data,
                        "filename": attachment.filename,
                        "timestamp": datetime.now(),
                    }

                    self.chain_submissions[chain_id].append(submission_data)
                    if user_id not in chain_data["participants"]:
                        chain_data["participants"].append(user_id)
                    chain_data["current_count"] += 1

                    if chain_data["current_count"] >= chain_data["target_amount"]:
                        await self.complete_chain(chain_id, message.channel)
                    else:
                        await message.channel.send(
                            f"🔗 {tracked_users[user_id]['user_nickname']} joined the '{chain_data['name']}' chain! "
                            f"Progress: {chain_data['current_count']}/{chain_data['target_amount']}"
                        )

                    logger.info(
                        "Chain submission added: %s -> '%s' (%s/%s)",
                        tracked_users[user_id]["user_nickname"],
                        chain_data["name"],
                        chain_data["current_count"],
                        chain_data["target_amount"],
                    )
                    return True

        except Exception as e:
            logger.error("Error processing chain submission: %s", e)
            await message.channel.send(f"❌ {message.author.name}, there was an error processing your chain submission.")
            return False

        return False

    async def complete_chain(self, chain_id: str, channel) -> None:
        if chain_id not in self.active_chains or chain_id not in self.chain_submissions:
            return

        chain_data = self.active_chains[chain_id]
        submissions = self.chain_submissions[chain_id]

        try:
            gif_path = await self.create_chain_gif(
                chain_id,
                chain_data["name"],
                submissions,
                chain_data.get("fps", DEFAULT_CHAIN_FPS),
            )

            if gif_path:
                participants = list(dict.fromkeys(sub["user_name"] for sub in submissions))
                completion_message = (
                    f"🎬 **CHAIN COMPLETED** 🎬\n\n"
                    f"**Chain:** {chain_data['name']}\n"
                    f"**Creator:** {chain_data['creator_name']}\n"
                    f"**Participants:** {', '.join(participants)}\n"
                    f"**Total Submissions:** {len(submissions)}\n\n"
                    f"Here's your collaborative art GIF! 🎨✨"
                )

                with open(gif_path, "rb") as gif_file:
                    discord_file = discord.File(gif_file, filename=f"{chain_data['name']}_chain.gif")
                    from artbot.shared import send_discord_message

                    await send_discord_message(channel, completion_message, file=discord_file)

                try:
                    os.remove(gif_path)
                except OSError:
                    pass

                logger.info("Chain completed: '%s' with %s submissions", chain_data["name"], len(submissions))
            else:
                await channel.send(f"🔗 Chain '{chain_data['name']}' completed but there was an error creating the GIF.")

        except Exception as e:
            logger.error("Error completing chain: %s", e)
            await channel.send(f"🔗 Chain '{chain_data['name']}' completed but there was an error creating the GIF.")

        chain_data["status"] = ChainStatus.COMPLETED
        self.clear_selected_chain(chain_id)

    async def create_chain_gif(
        self,
        chain_id: str,
        chain_name: str,
        submissions,
        fps: float = DEFAULT_CHAIN_FPS,
    ):
        try:
            chains_dir = "chains"
            if not os.path.exists(chains_dir):
                os.makedirs(chains_dir)

            images = []
            target_size = (512, 512)

            for submission in submissions:
                try:
                    image = Image.open(io.BytesIO(submission["image_data"]))

                    if image.mode in ["RGBA", "P"]:
                        background = Image.new("RGB", image.size, (255, 255, 255))
                        if image.mode == "P":
                            image = image.convert("RGBA")
                        background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                        image = background
                    elif image.mode != "RGB":
                        image = image.convert("RGB")

                    image.thumbnail(target_size, Image.Resampling.LANCZOS)

                    if image.size != target_size:
                        padded = Image.new("RGB", target_size, (255, 255, 255))
                        paste_x = (target_size[0] - image.size[0]) // 2
                        paste_y = (target_size[1] - image.size[1]) // 2
                        padded.paste(image, (paste_x, paste_y))
                        image = padded

                    images.append(image)

                except Exception as e:
                    logger.error("Error processing image in chain: %s", e)

            if not images:
                logger.error("No valid images to create GIF")
                return None

            gif_filename = f"{chain_name.replace(' ', '_')}_{chain_id}.gif"
            gif_path = os.path.join(chains_dir, gif_filename)
            duration = self.get_frame_duration_ms(fps)

            images[0].save(
                gif_path,
                save_all=True,
                append_images=images[1:],
                duration=duration,
                loop=0,
                optimize=True,
            )

            logger.info("Created GIF: %s with %s frames", gif_path, len(images))
            return gif_path

        except Exception as e:
            logger.error("Error creating chain GIF: %s", e)
            return None

    def get_frame_duration_ms(self, fps: float) -> int:
        if fps < MIN_CHAIN_FPS or fps > MAX_CHAIN_FPS:
            fps = DEFAULT_CHAIN_FPS
        return int(1000 / fps)

    async def chain_list_command(self, interaction: discord.Interaction) -> None:
        if not self.active_chains:
            await interaction.response.send_message("🔗 No active chains currently!", ephemeral=True)
            return

        active_list = [
            chain for chain in self.active_chains.values()
            if chain["status"] == ChainStatus.ACTIVE
        ]

        if not active_list:
            await interaction.response.send_message("🔗 No active chains currently!", ephemeral=True)
            return

        list_message = "🔗 **ACTIVE ART CHAINS** 🔗\n\n"

        for chain in active_list:
            list_message += f"**{chain['name']}**\n"
            list_message += f"  Creator: {chain['creator_name']}\n"
            list_message += f"  Progress: {chain['current_count']}/{chain['target_amount']}\n"
            list_message += f"  Use `/chain_on {chain['name']}` to join!\n\n"

        from artbot.shared import send_interaction_message

        await send_interaction_message(interaction, list_message)

    async def chain_cancel_command(self, interaction: discord.Interaction, name: str) -> None:
        user_id = interaction.user.id
        chain_id, chain_data = self.find_chain(name)

        if not chain_data:
            await interaction.response.send_message(f"❌ No chain found with the name '{name}'.", ephemeral=True)
            return

        is_creator = user_id == chain_data["creator"]
        guild_permissions = getattr(interaction.user, "guild_permissions", None)
        is_admin = bool(guild_permissions and guild_permissions.administrator)
        is_mod = shared.has_named_role(interaction.user, ["wally"])

        if not (is_creator or is_admin or is_mod):
            await interaction.response.send_message("❌ Only the chain creator or admins can cancel chains.", ephemeral=True)
            return

        chain_data["status"] = ChainStatus.CANCELLED

        self.clear_selected_chain(chain_id)

        cancel_message = (
            f"🚫 **CHAIN CANCELLED** 🚫\n\n"
            f"**Chain:** {chain_data['name']}\n"
            f"**Cancelled by:** {interaction.user.display_name}\n"
            f"**Progress:** {chain_data['current_count']}/{chain_data['target_amount']}\n\n"
            f"The chain has been cancelled and no longer accepts submissions."
        )

        from artbot.shared import send_interaction_message

        await send_interaction_message(interaction, cancel_message)
        logger.info("Chain cancelled: '%s' by %s", chain_data["name"], interaction.user.display_name)

    def get_chain_data(self) -> dict:
        chains_serializable = {}
        submissions_serializable = {}

        for chain_id, chain in self.active_chains.items():
            serializable_chain = chain.copy()
            serializable_chain["created_at"] = chain["created_at"].isoformat()
            chains_serializable[chain_id] = serializable_chain

        for chain_id, submissions in self.chain_submissions.items():
            submissions_serializable[chain_id] = [
                {
                    "user_id": sub["user_id"],
                    "user_name": sub["user_name"],
                    "message_id": sub["message_id"],
                    "filename": sub["filename"],
                    "timestamp": sub["timestamp"].isoformat(),
                }
                for sub in submissions
            ]

        return {
            "active_chains": chains_serializable,
            "chain_submissions": submissions_serializable,
        }

    def load_chain_data(self, chain_data) -> None:
        if not chain_data:
            return

        chains_data = chain_data.get("active_chains", {})
        for chain_id, chain in chains_data.items():
            chain["created_at"] = datetime.fromisoformat(chain["created_at"])
            self.active_chains[chain_id] = chain

        submissions_data = chain_data.get("chain_submissions", {})
        for chain_id in submissions_data.keys():
            self.chain_submissions[chain_id] = []

        logger.info("Loaded %s chains", len(self.active_chains))

    def clear_all_chains(self) -> tuple[int, int]:
        chains_count = len(self.active_chains)
        submissions_count = sum(len(subs) for subs in self.chain_submissions.values())

        self.active_chains.clear()
        self.chain_submissions.clear()
        self.selected_chains.clear()

        logger.info("Cleared %s chains and %s submissions", chains_count, submissions_count)
        return chains_count, submissions_count

    def clear_selected_chain(self, chain_id: str) -> None:
        to_remove = [
            uid for uid, selected_chain in self.selected_chains.items()
            if selected_chain["chain_id"] == chain_id
        ]
        for uid in to_remove:
            del self.selected_chains[uid]

    def find_chain(self, name: str) -> tuple[str | None, dict | None]:
        for chain_id, chain in self.active_chains.items():
            if chain["name"].lower() == name.lower():
                return chain_id, chain
        return None, None


default_chain_service = ChainService()


def get_tracked_users() -> dict[int, dict]:
    return default_chain_service.get_tracked_users()


def set_tracked_users_reference(tracked_users_ref: dict[int, dict]) -> None:
    default_chain_service.set_tracked_users_reference(tracked_users_ref)


async def chain_start_command(
    interaction: discord.Interaction,
    name: str,
    amount: int,
    fps: float = DEFAULT_CHAIN_FPS,
) -> None:
    await default_chain_service.chain_start_command(interaction, name, amount, fps)


async def chain_on_command(interaction: discord.Interaction, name: str) -> None:
    await default_chain_service.chain_on_command(interaction, name)


async def chain_off_command(interaction: discord.Interaction) -> None:
    await default_chain_service.chain_off_command(interaction)


async def process_chain_submission(user_id: int, message, attachment) -> bool:
    return await default_chain_service.process_chain_submission(user_id, message, attachment)


async def complete_chain(chain_id: str, channel) -> None:
    await default_chain_service.complete_chain(chain_id, channel)


async def create_chain_gif(
    chain_id: str,
    chain_name: str,
    submissions,
    fps: float = DEFAULT_CHAIN_FPS,
):
    return await default_chain_service.create_chain_gif(chain_id, chain_name, submissions, fps)


async def chain_list_command(interaction: discord.Interaction) -> None:
    await default_chain_service.chain_list_command(interaction)


async def chain_cancel_command(interaction: discord.Interaction, name: str) -> None:
    await default_chain_service.chain_cancel_command(interaction, name)


def get_chain_data() -> dict:
    return default_chain_service.get_chain_data()


def load_chain_data(chain_data) -> None:
    default_chain_service.load_chain_data(chain_data)


def clear_all_chains() -> tuple[int, int]:
    return default_chain_service.clear_all_chains()
