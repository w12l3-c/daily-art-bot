"""
Runnable commands involving (weekly) challenges
"""

import discord
from discord import app_commands
from typing import Optional
import os
from challenge import *
import shared
from shared import bot, logger, confirmation_prompt, save_data_task
import random

challenge_start_flavour_text = [
    "Lock in!!!",
    "Happy drawing!",
    "Walbot out!",
    "🤨🤨🤨",
    "01110100 01100101 01100101 01101000 01100101 01100101",
    "Good luck gamers!",
    "ZAK!!! I have something VERY IMPORTANT to tell you...",
    "so am I getting paid for this",
    "<:happymiku:1178130719646679061> <:happymiku:1178130719646679061> <:happymiku:1178130719646679061>"
]

# <----------------------------------------------------- Mod commands ----------------------------------------------------->

@bot.tree.command(name="challenge_start", description="Start a challenge! (Must be mod)")
@app_commands.describe(
    theme="The theme for this challenge",
    threshold="The number of submissions a user must reach to complete the challenge (default is length)",
    length="The length of this challenge in days (default is 7)",
    channel="The channel to send the start message to (default is where dailies is sent)")
async def challenge_start(interaction: discord.Interaction, theme: str, threshold: int = -1, length: int = 7, channel: discord.TextChannel = None):
    if not shared.has_admin_or_mod_permissions(interaction) and interaction.user.id not in shared.CHALLENGE_MODS:
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return

    if threshold == -1:
        threshold = length
    
    if channel is None:
        channel = bot.get_channel(shared.announcement_channel)
    
    if is_challenge_active():
        await interaction.response.send_message(f"You currently have a challenge by the theme \"{shared.challenge_theme}\" on day {shared.challenge_day}. Please run /challenge_cancel first.", ephemeral=True)
        return

    if not channel:
        logger.error(f"Error starting challenge: couldn't find channel!")
        await interaction.response.send_message(f"Error starting challenge: couldn't find channel!", ephemeral=True)
        return

    confirmation, msg = await confirmation_prompt(interaction, title="Are you sure you want to start a challenge with the following parameters?", description=f"Challenge number: {shared.challenge_number + 1}\nChallenge length: {length}\nChallenge theme: {theme}\nThreshold to complete: {threshold}")
    if confirmation:
        await msg.edit(content=f"Starting a challenge! You will see an announcement in <#{channel.id}> shortly...", embed=None, view=None)
    else:
        await msg.edit(content="Terminating challenge start request...", embed=None, view=None)
        return

    shared.challenge_number += 1
    shared.challenge_day = 1
    shared.challenge_length = length
    shared.challenge_theme = theme
    shared.challenge_threshold = threshold
    
    await save_data_task()

    message = (f"# Welcome to Challenge #{shared.challenge_number}: \"{shared.challenge_theme}\"!\n" +
                       f"For this challenge, we have:\n" + 
                       f"**Host:** <@{interaction.user.id}>\n" +
                       f"**Theme:** {shared.challenge_theme}\n" +
                       f"**Length:** {shared.challenge_length} day(s)\n" +
                       f"**Threshold to complete:** {shared.challenge_threshold} submission(s)\n\n")
    

    participants = list(filter(lambda user: user["in_challenges"], shared.tracked_users.values()))

    if len(participants) != 0:
        message += f"We currently have **{len(participants)}** participant(s):\n" + ", ".join(list(map(lambda user: shared.format_username(user["user_nickname"]), participants)))
    else:
        message += f"We currently have no participants 😢"

    # message += f"\n-# Join Challenges using /challenge_join!!!\n\n"

    # add random flavour text cuz im bored
    # random.seed()
    # message += f"-# {random.choice(challenge_start_flavour_text)}"
    await channel.send(message)


    

@bot.tree.command(name="challenge_cancel", description="Cancel a challenge. (Must be mod)")
async def challenge_cancel(interaction: discord.Interaction):
    if not shared.has_admin_or_mod_permissions(interaction) and interaction.user.id not in shared.CHALLENGE_MODS:
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    if not is_challenge_active():
        await interaction.response.send_message("There isn't currently an ongoing challenge to cancel...", ephemeral=True)
        return

    confirmation, msg = await confirmation_prompt(interaction, title=f"Are you sure you want to cancel the challenge of theme \"{shared.challenge_theme}\"?")
    if confirmation:
        await end_challenge()
        await msg.edit(content="Challenge cancelled!", view=None, embed=None)
    else:
        await msg.edit(content="Cancel request terminated!", view=None, embed=None)
    


@bot.tree.command(name="challenge_add", description="Add a user to the Challenges! (Must be mod)")
@app_commands.describe(user="Select a user")
async def challenge_add(interaction: discord.Interaction, user: discord.User):
    if not shared.has_admin_or_mod_permissions(interaction) and interaction.user.id not in shared.CHALLENGE_MODS:
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    if user.id not in shared.tracked_users:
        await interaction.response.send_message(f"{user.display_name} is not in dailies! Please register them before adding them to a challenge.", ephemeral=True)
        return

    in_challenges = shared.tracked_users[user.id]["in_challenges"]
    nickname = shared.tracked_users[user.id]["user_nickname"]

    await add_user(user)

    if in_challenges:
        await interaction.response.send_message(f"{nickname} was already in Challenges!", ephemeral=True)
    else:
        await interaction.response.send_message(f"{nickname} has been added to Challenges!", ephemeral=True)   



@bot.tree.command(name="challenge_remove", description="Remove a user from Challenges. (Must be mod)")
@app_commands.describe(user="Select a user")
async def challenge_remove(interaction: discord.Interaction, user: discord.User):
    if not shared.has_admin_or_mod_permissions(interaction) and interaction.user.id not in shared.CHALLENGE_MODS:
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    if user.id not in shared.tracked_users:
        await interaction.response.send_message(f"{user.display_name} is not in dailies! Please register them before adding them to a challenge.", ephemeral=True)
        return

    in_challenges = shared.tracked_users[user.id]["in_challenges"]
    nickname = shared.tracked_users[user.id]["user_nickname"]
    await remove_user(user)

    if in_challenges:
        await interaction.response.send_message(f"{nickname} has been removed from the Challenges.", ephemeral=True)
    else:
        await interaction.response.send_message(f"{nickname} was not in Challenges.", ephemeral=True)



@bot.tree.command(name="challenge_edit", description="Edit or view an ongoing challenge's attributes. (Must be mod)")
@app_commands.describe(day_number="Set the day number", challenge_number="Set the challenge number", theme="Set the theme", length="Set the length")
async def challenge_edit(
    interaction: discord.Interaction, 
    day_number: int = -1, 
    challenge_number: int = -1, 
    theme: str = "",
    length: int = -1
):
    if not shared.has_admin_or_mod_permissions(interaction) and interaction.user.id not in shared.CHALLENGE_MODS:
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return
    
    if not is_challenge_active():
        await interaction.response.send_message(f"There isn't currently an ongoing challenge to edit...", ephemeral=True)
        return

    
    if day_number != -1:
        shared.challenge_day = day_number
    
    if length != -1:
        shared.challenge_length = length
    
    if theme != "":
        shared.challenge_theme = theme
    
    if challenge_number != -1:
        shared.challenge_number = challenge_number

    await interaction.response.send_message(f"Edits saved! The challenge's attributes are:\n" +
                                            f"**Challenge number:** {shared.challenge_number}\n" + 
                                            f"**Challenge day:** {shared.challenge_day}\n" +
                                            f"**Challenge length:** {shared.challenge_length}\n" +
                                            f"**Challenge theme:** \"{shared.challenge_theme}\"\n", ephemeral=True)

    await save_data_task()



@bot.tree.command(name="challenge_edit_user", description="Edit or view a user's attributes. (Must be mod)")
@app_commands.describe(
    user="Select a user",
    in_challenges="Whether this user is in this challenge",
    challenge_participations="The number of Challenges this user has participated in",
    challenge_completions="The number of Challenges this user has completed",
    challenge_streak="The user's completion streak",
    challenge_submissions="The number of submissions this user has made for the ongoing challenge",
)
async def challenge_edit_user(
    interaction: discord.Interaction, 
    user: discord.User,
    in_challenges: Optional[bool] = None,
    challenge_participations: int = -1,
    challenge_completions: int = -1,
    challenge_streak: int = -1,
    challenge_submissions: int = -1,
):
    if not shared.has_admin_or_mod_permissions(interaction) and interaction.user.id not in shared.CHALLENGE_MODS:
        await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
        return

    if user.id not in shared.tracked_users:
        await interaction.response.send_message(f"{user.name} is not in the daily art tracking system! Please add them first.", ephemeral=True)
        return

    if in_challenges is not None:
        shared.tracked_users[user.id]["in_challenges"] = in_challenges

    if challenge_participations != -1:
        shared.tracked_users[user.id]["challenge_participations"] = challenge_participations

    if challenge_completions != -1:
        shared.tracked_users[user.id]["challenge_completions"] = challenge_completions

    if challenge_streak != -1:
        shared.tracked_users[user.id]["challenge_streak"] = challenge_streak

    if challenge_submissions != -1:
        shared.tracked_users[user.id]["challenge_submissions"] = challenge_submissions

    
    await interaction.response.send_message(f"Edits saved! The user's attributes are:\n" +
                                            f"**In Challenges? ** {'Yes' if shared.tracked_users[user.id]['in_challenges'] else 'No' }\n" + 
                                            f"**Challenge participations: ** {shared.tracked_users[user.id]['challenge_participations']}\n" +
                                            f"**Challenge completions: ** {shared.tracked_users[user.id]['challenge_completions']}\n" +
                                            f"**Challenge streak: ** {shared.tracked_users[user.id]['challenge_streak']}\n" +
                                            f"**Challenge submissions: ** {shared.tracked_users[user.id]['challenge_submissions']}\n" +
                                            f"**Submission: ** {shared.tracked_users[user.id]['submission']}"
                                            , ephemeral=True)


    await save_data_task()

# <----------------------------------------------------- Non-mod commands ----------------------------------------------------->


@bot.tree.command(name="challenge_join", description="Join Challenges!")
async def challenge_join(interaction: discord.Interaction):
    if interaction.user.id not in shared.tracked_users:
        await interaction.response.send_message(f"You are not in the daily art tracking system! Please join that first.", ephemeral=True)
        return
    
    if is_challenge_active():
        await interaction.response.send_message(f"You cannot join an ongoing challenge!", ephemeral=True)
        return

    in_challenges = shared.tracked_users[interaction.user.id]["in_challenges"]
    await add_user(interaction.user)

    if in_challenges:
        await interaction.response.send_message(f"You have already joined Challenges!", ephemeral=True)
    else:
        await interaction.response.send_message(f"You have joined Challenges!", ephemeral=True)
    


@bot.tree.command(name="challenge_leave", description="Leave Challenges.")
async def challenge_leave(interaction: discord.Interaction):
    if interaction.user.id not in shared.tracked_users:
        await interaction.response.send_message(f"You are not in the daily art tracking system! Please join that first.", ephemeral=True)
        return

    in_challenges = shared.tracked_users[interaction.user.id]["in_challenges"]
    await remove_user(interaction.user)

    if in_challenges:
        await interaction.response.send_message(f"You have left Challenges.", ephemeral=True)
    else:
        await interaction.response.send_message(f"You weren't in Challenges.", ephemeral=True)




@bot.tree.command(name="challenge_stats", description="See your challenge stats!")
async def challenge_stats(interaction: discord.Interaction):
    if interaction.user.id not in shared.tracked_users:
        await interaction.response.send_message(f"You are not in the daily art tracking system! Please join that first.", ephemeral=True)
        return

    user = shared.tracked_users[interaction.user.id]

    await interaction.response.send_message(f"**Your stats:**\n"+
                                            f"Challenge participations: {user['challenge_participations']}\n"+
                                            f"Challenge completions: {user['challenge_completions']}\n"+
                                            f"Challenge streak: {user['challenge_streak']}\n"+
                                            f"Submissions for this challenge: {user['challenge_submissions']}\n"+
                                            f"In Challenges? {'Yes' if user['in_challenges'] else 'No'}\n", ephemeral=True)    

@bot.tree.command(name="challenge_find_submissions", description="Find today's challenge submission of a user or all users!")
@app_commands.describe(user="Select a user, or leave blank to view all")
async def challenge_find_submissions(interaction: discord.Interaction, user: discord.User = None):
    message = f"Submissions for Day {shared.current_day}:\n"
    if user:
        if user.id not in shared.tracked_users:
            await interaction.response.send_message(f"User {user.name} not found in tracking.", ephemeral=True)
            return
        
        if not shared.tracked_users[user.id]["in_challenges"]:
            await interaction.response.send_message(f"User {user.name} is not in Challenges.", ephemeral=True)
            return
        
        message += f"{shared.format_username(shared.tracked_users[user.id]['user_nickname'])}: " + shared.get_submission_link(user.id)
    else:
        for user_id in shared.tracked_users.keys():
            if shared.tracked_users[user_id]["in_challenges"]:
                message += f"{shared.format_username(shared.tracked_users[user_id]['user_nickname'])}: " + shared.get_submission_link(user_id)
                message += "\n"
    
    await interaction.response.send_message(message, ephemeral=True)