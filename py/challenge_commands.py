# """
# Runnable commands involving (weekly) challenges
# """

# import discord
# from discord import app_commands
# import os
# from challenge import *
# from daily import save_data_task
# import shared
# from shared import bot, logger, confirmation_prompt
# import random

# challenge_start_flavour_text = [
#     "Lock in!!!",
#     "Happy drawing!",
#     "Walbot out!",
#     "I'm always watching...",
#     "01110100 01100101 01100101 01101000 01100101 01100101",
#     "Good luck gamers!",
#     "ZAK!!! I have something very important to tell you..."
# ]

# # <----------------------------------------------------- Mod commands ----------------------------------------------------->

# @bot.tree.command(name="challenge_start", description="Start a challenge! (Must be mod)")
# @app_commands.describe(theme="The theme for this challenge", threshold="The number of submissions a user must reach to complete the challenge (default is length)", length="The length of this challenge in days (default is 7)")
# async def challenge_start(interaction: discord.Interaction, theme: str, threshold: int = -1, length: int = 7):
#     if threshold == -1:
#         threshold = length

#     if not shared.has_admin_or_mod_permissions(interaction) and interaction.user not in shared.CHALLENGE_MODS:
#         await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
#         return
    
#     if is_challenge_active():
#         await interaction.response.send_message(f"You currently have a challenge by the theme {shared.challenge_theme} on day {shared.challenge_day}. Please run /challenge_cancel first")
#         return
    
#     channel = bot.get_channel(shared.announcement_channel)

#     if not channel:
#         logger.error(f"Error starting challenge: couldn't find announcement channel of id {shared.announcement_channel}")
#         await interaction.response.send_message(f"Error starting challenge: couldn't find announcement channel of id {shared.announcement_channel}")
#         return

#     shared.challenge_number += 1
#     shared.challenge_day = 1
#     shared.challenge_length = length
#     shared.challenge_theme = theme
#     shared.challenge_threshold = threshold
    
#     await save_data_task()

#     message = (f"# Welcome to Challenge #{shared.challenge_number}: {shared.challenge_theme}!\n" +
#                        f"For this challenge, we have:\n" + 
#                        f"**Host:** <@{interaction.user.id}>\n" +
#                        f"**Theme:** {shared.challenge_theme}" +
#                        f"**Length:** {shared.challenge_length} day(s)" +
#                        f"**Threshold to complete:** {shared.challenge_threshold} submissions")
    
#     await channel.send(message)

#     participants = list(filter(lambda user: user["in_challenge"]))

#     if len(participants) is not 0:
#         message = f"In this challenge, we have **{len(participants)}**:\n" + ", ".join(list(map(participants(lambda user: user["user_nickname"]))))
#     else:
#         message =f"In this challenge, we currently have no participants 😢"

#     message += f"\n-# Join this challenge using /challenge_join, and automatically join all challenges with /challenge_opt"

#     await channel.send(message)

#     # add random flavour text cuz im bored
#     random.seed()
#     message = f"Our host will send more details below! (Or maybe not)\nThe challenge starts NOW!!!" + f"-# {random.choice(challenge_start_flavour_text)}"
#     await channel.send(message)


    

# @bot.tree.command(name="challenge_cancel", description="Cancel a challenge. (Must be mod)")
# async def challenge_cancel(interaction: discord.Interaction):
#     if not shared.has_admin_or_mod_permissions(interaction) and interaction.user not in shared.CHALLENGE_MODS:
#         await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
#         return

#     confirmation = await confirmation_prompt(interaction, warning=f"Are you sure you want to cancel of theme {shared.challenge_theme}?", ephemeral=True)
#     if confirmation:
#         await end_challenge()
#         await interaction.response.send_message("Challenge cancelled!", ephemeral=True)
#     else:
#         await interaction.response.send_message("Cancel request terminated!", ephemeral=True)
    


# @bot.tree.command(name="challenge_add_user", description="Add a user to a challenge! If there isn't one ongoing, they will be in the next! (Must be mod)")
# @app_commands.describe(user="Select a user")
# async def challenge_add_user(interaction: discord.Interaction, user: discord.User):
#     if not shared.has_admin_or_mod_permissions(interaction) and interaction.user not in shared.CHALLENGE_MODS:
#         await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
#         return
    
#     if user.id not in shared.tracked_users:
#         await interaction.response.send_message(f"{user.display_name} is not in dailies! Please register them before adding them to a challenge.", ephemeral=True)
#         return

#     if shared.tracked_users[user.id]["in_challenge"]:
#         await interaction.response.send_message(f"{shared.tracked_users[user.id]["user_nickname"]} is already in!")
#         return

#     await add_user(user)

#     if is_challenge_active():
#         await interaction.response.send_message(f"{shared.tracked_users[user.id]["user_nickname"]} has been added to the challenge!")
#     else:
#         await interaction.response.send_message(f"{shared.tracked_users[user.id]["user_nickname"]} will be added to the next challenge!")



# @bot.tree.command(name="challenge_edit", description="Edit an ongoing challenge's attributes. (Must be mod)")
# @app_commands.describe(day_number="Set the day number", challenge_number="Set the challenge number", theme="Set the theme", length="Set the length")
# async def challenge_edit(
#     interaction: discord.Interaction, 
#     day_number: int = shared.challenge_day, 
#     challenge_number: int = shared.challenge_number, 
#     theme: str = shared.challenge_theme,
#     length: int = shared.challenge_length
# ):
#     if not shared.has_admin_or_mod_permissions(interaction) and interaction.user.id not in shared.CHALLENGE_MODS:
#         await interaction.response.send_message("❌ You need administrator permissions or mod role to use this command.", ephemeral=True)
#         return
    
#     if not is_challenge_active():
#         await interaction.response.send_message(f"There isn't currently an ongoing challenge", ephemeral=True)
#         return

#     shared.challenge_day = day_number
#     shared.challenge_length = length
#     shared.challenge_theme = theme
#     shared.challenge_number = challenge_number

#     await interaction.response.send_message(f"Edits saved! The challenge's attributes are:\n" +
#                                             f"**Challenge number:** {shared.challenge_number}\n" + 
#                                             f"**Challenge day:** {shared.challenge_day}\n" +
#                                             f"**Challenge length:** {shared.challenge_length}\n" +
#                                             f"**Challenge theme:** {shared.challenge_theme}\n")

#     await save_data_task()


# # <----------------------------------------------------- Mod commands ----------------------------------------------------->


# @bot.tree.command(name="challenge_join", description="Join or leave an ongoing challenge! If there isn't one, automatically the next!")
# @app_commands.describe(day_number="Set the day number", challenge_number="Set the challenge number", theme="Set the theme", length="Set the length")
# @app_commands.choices(join=[
#     app_commands.Choice(name="Join", value=True),
#     app_commands.Choice(name="Leave", value=False),
# ])
# async def challenge_join(interaction: discord.Interaction, join: app_commands.Choice[bool]):
#     if interaction.user.id not in shared.tracked_users:
#         await interaction.response.send_message(f"You are not in the daily art tracking system! Please join that first.", ephemeral=True)
#         return

#     if join:
#         await add_user(interaction.user)
#         if is_challenge_active():
#             await interaction.response.send_message(f"You have joined the challenge!", ephemeral=True)
#         else:
#             await interaction.response.send_message(f"There isn't current an ongoing challenge. You will automatically join the next one!", ephemeral=True)
#     else:
#         await remove_user(interaction.user)
#         if is_challenge_active():
#             await interaction.response.send_message(f"You have left the challenge.", ephemeral=True)
#         else:
#             await interaction.response.send_message(f"You will no longer automatically join the next challenge, **unless** you are opted in. Run /challenge_opt to opt out.")



# @bot.tree.command(name="challenge_opt", description="Choose whether or not you want to automatically join all future challenges!")
# @app_commands.describe(day_number="Set the day number", challenge_number="Set the challenge number", theme="Set the theme", length="Set the length")
# @app_commands.choices(join=[
#     app_commands.Choice(name="Opt in", value=True),
#     app_commands.Choice(name="Opt out", value=False),
# ])
# async def challenge_join(interaction: discord.Interaction, opt: app_commands.Choice[bool]):
#     if interaction.user.id not in shared.tracked_users:
#         await interaction.response.send_message(f"You are not in the daily art tracking system! Please join that first.", ephemeral=True)
#         return
    
#     await set_opt_user(interaction.user, opt)

#     if opt:
#         await interaction.response.send_message(f"You have opted in, and will automatically join all future challenges!", ephemeral=True)
#     else:
#         await interaction.response.send_message(f"You have opted out, and will no longer automatically join all future challenges!", ephemeral=True)

# @bot.tree.command(name="challenge_stats", description="See your challenge stats!")
# @app_commands.describe(day_number="Set the day number", challenge_number="Set the challenge number", theme="Set the theme", length="Set the length")
# async def challenge_join(interaction: discord.Interaction):
#     if interaction.user.id not in shared.tracked_users:
#         await interaction.response.send_message(f"You are not in the daily art tracking system! Please join that first.", ephemeral=True)
#         return

#     user = shared.tracked_users[interaction.user.id]

#     await interaction.response.send_message(f"**Your stats:**\n"+
#                                             f"Challenge participations: {user["challenge_participations"]}\n"+
#                                             f"Challenge completions: {user["challenge_completions"]}\n"+
#                                             f"Challenge streak: {user["challenge_streak"]}\n"+
#                                             f"Challenge submissions this challenge: {user["challenge_submissions"]}\n"+
#                                             f"In this challenge? {"Yes" if user["in_challenge"] else "No"}\n"
#                                             )    

