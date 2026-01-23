"""
Functions regarding (weekly) challenges run by Orsafia
"""

import discord
from discord import app_commands
import os
import shared
from shared import bot, logger, confirmation_prompt
from daily import save_data_task

def is_challenge_active() -> bool:
    return shared.challenge_day != 0


async def end_challenge():
    if not is_challenge_active():
        return

    for user in shared.tracked_users.values():
        if user["in_challenge"]:
            user["in_challenge"] = False

            if user["challenge_submissions"] >= shared.challenge_threshold:
                user["challenge_completions"] += 1
                user["challenge_streak"] += 1
            else:
                user["challenge_streak"] = 0
            user["challenge_participations"] += 1
        user["challenge_submissions"] = 0

        if user["opted_in_challenges"]:
            user["in_challenge"] = True

    shared.challenge_day = 0
    shared.challenge_length = 7
    shared.challenge_theme = ""
    shared.challenge_threshold = 7

    await save_data_task()



async def add_user(user: discord.User):
    if user.id in shared.tracked_users:
        shared.tracked_users[user.id]["in_challenge"] = True
        await save_data_task()


async def remove_user(user: discord.User):
    if user.id in shared.tracked_users:
        shared.tracked_users[user.id]["in_challenge"] = False
        await save_data_task()

async def set_opt_user(user: discord.User, opt: bool):
    if user.id in shared.tracked_users:
        shared.tracked_users[user.id]["opted_in_challenges"] = opt
        shared.tracked_users[user.id]["in_challenge"] = opt
        await save_data_task()