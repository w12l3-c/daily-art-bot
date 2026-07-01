import discord

import artbot.shared as shared
from artbot.shared import logger, save_data_task


class ChallengeService:
    def is_challenge_active(self) -> bool:
        return shared.challenge_day != 0

    async def end_challenge(self) -> None:
        if not self.is_challenge_active():
            logger.warning("Challenge is still not active! Returning...")
            return

        for user in shared.tracked_users.values():
            if user["in_challenges"]:
                if user["challenge_submissions"] >= shared.challenge_threshold:
                    user["challenge_completions"] += 1
                    user["challenge_streak"] += 1
                else:
                    user["challenge_streak"] = 0
                user["challenge_participations"] += 1

            user["challenge_submissions"] = 0

        shared.challenge_day = 0
        shared.challenge_length = 7
        shared.challenge_theme = ""
        shared.challenge_threshold = 7

        await save_data_task()

    async def add_user(self, user: discord.User) -> None:
        if user.id in shared.tracked_users:
            shared.tracked_users[user.id]["in_challenges"] = True
            await save_data_task()

    async def remove_user(self, user: discord.User) -> None:
        if user.id in shared.tracked_users:
            shared.tracked_users[user.id]["in_challenges"] = False
            await save_data_task()


default_challenge_service = ChallengeService()


def is_challenge_active() -> bool:
    return default_challenge_service.is_challenge_active()


async def end_challenge() -> None:
    await default_challenge_service.end_challenge()


async def add_user(user: discord.User) -> None:
    await default_challenge_service.add_user(user)


async def remove_user(user: discord.User) -> None:
    await default_challenge_service.remove_user(user)
