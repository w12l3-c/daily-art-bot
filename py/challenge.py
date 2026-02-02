"""
Functions regarding (weekly) challenges run by Orsafia
"""

import discord
from discord import app_commands
import os
import shared
from shared import bot, logger, save_data_task

def is_challenge_active() -> bool:
    return shared.challenge_day != 0 or shared.challenge_theme == ""


async def end_challenge():
    if not is_challenge_active():
        logger.log("Challenge is still not active! Returning...")
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



async def add_user(user: discord.User):
    if user.id in shared.tracked_users:
        shared.tracked_users[user.id]["in_challenges"] = True
        await save_data_task()


async def remove_user(user: discord.User):
    if user.id in shared.tracked_users:
        shared.tracked_users[user.id]["in_challenges"] = False
        await save_data_task()