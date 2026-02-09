import discord
from discord import app_commands
import shared
from shared import bot, logger
import wcw

# ------------------------------------------------ Mod commands ------------------------------------------------

@bot.tree.command(name="wcw_edit_user", description="Edit a user in WCW. (Must be mod or warden)")
@app_commands.describe(
    user="Select a user",
    status="Set the status",
    submission="Set the submission message",
    submission_words="Set the number of words of this week's submission",
    submissions="Set the number of submissions",
    active="Set if the user is active",
    total_word_count="Set the user's total word count",
    goal="Set the user's goal",
    weekly_streak="Set the user's weekly submission streak",
    weeks_submitted="Set the user's number of weeks they submitted",
    weeks_missed="Set the user's number of weeks missed",
    weeks_excused="Set the user's number of weeks excused",
    ping="Set the user's preference for reminder pings"
)
async def wcw_edit_user(
    interaction: discord.Interaction,
    user: discord.User,
    status: str = None,
    submission: str = None,
    submission_words: int = None,
    submissions: int = None,
    active: bool = None,
    total_word_count: int = None,
    goal: str = None,
    weekly_streak: int = None,
    weeks_submitted: int = None,
    weeks_missed: int = None,
    weeks_excused: int = None,
    ping: bool = None,
):
    if not wcw.has_perms(interaction.user):
        await interaction.response.send_message(f"You must be mod or warden to use this command!", ephemeral=True)
        return
    
    if not wcw.is_active_member(user):
        await interaction.response.send_message(f"{user.display_name} is not in WCW!", ephemeral=True)
        return
    
    await wcw.edit_user(
        user=user,
        status=status,
        submission=submission,
        submission_words=submission_words,
        submissions=submissions,
        active=active,
        total_word_count=total_word_count,
        goal=goal,
        weekly_streak=weekly_streak,
        weeks_submitted=weeks_submitted,
        weeks_missed=weeks_missed,
        weeks_excused=weeks_excused,
        ping=ping,
    )

    message = "**Edits saved! User data is now:**\n" + wcw.view_user(user)

    await interaction.response.send_message(
        message,
        ephemeral=True
    )



@bot.tree.command(name="wcw_add", description="Add a user to WCW. (Must be mod or warden)")
@app_commands.describe(user="Select a user")
async def wcw_add(interaction: discord.Interaction, user: discord.User):
    if not wcw.has_perms(interaction.user):
        await interaction.response.send_message(f"You must be mod or warden to use this command!", ephemeral=True)
        return

    if wcw.is_active_member(user):
        await interaction.response.send_message(f"{user.display_name} is already part of WCW!", ephemeral=True)
    else:
        await wcw.add_user(user)
        await interaction.response.send_message(f"{user.display_name} has been added to WCW!", ephemeral=True)



@bot.tree.command(name="wcw_remove", description="Remove a user from WCW. (Must be mod or warden)")
@app_commands.describe(user="Select a user")
async def wcw_remove(interaction: discord.Interaction, user: discord.User):
    if not wcw.has_perms(interaction.user):
        await interaction.response.send_message(f"You must be mod or warden to use this command!", ephemeral=True)
        return
    
    if wcw.is_active_member(user):
        await wcw.remove_user(user)
        await interaction.response.send_message(f"{user.display_name} has been removed from WCW!", ephemeral=True)
    else:
        await interaction.response.send_message(f"{user.display_name} is not in WCW!", ephemeral=True)



@bot.tree.command(name="wcw_excuse", description="Excuse a user from this week's WCW. (Must be mod or warden)")
@app_commands.describe(user="Select a user")
async def wcw_excuse(interaction: discord.Interaction, user: discord.User):
    if not wcw.has_perms(interaction.user):
        await interaction.response.send_message(f"You must be mod or warden to use this command!", ephemeral=True)
        return
    
    if wcw.is_active_member(user):
        result = await wcw.excuse_user(user)
        if result:
            await interaction.response.send_message(f"{user.display_name} has been excused for this week.")
        else:
            await interaction.response.send_message(f"{user.display_name} has already submitted this week. They cannot be excused.")

    else:
        await interaction.response.send_message(f"{user.display_name} is not in WCW!", ephemeral=True)



# ------------------------------------------------ Non-mod commands ------------------------------------------------



@bot.tree.command(name="wcw_join", description="Join WCW!")
async def wcw_join(interaction: discord.Interaction):
    user = interaction.user
    if wcw.is_active_member(user):
        await interaction.response.send_message("You're already part of WCW!", ephemeral=True)
    else:
        await wcw.add_user(user)
        await interaction.response.send_message("Welcome to WCW!", ephemeral=True)



@bot.tree.command(name="wcw_leave", description="Leave WCW. Your stats will remain archived.")
async def wcw_leave(interaction: discord.Interaction):
    user = interaction.user
    if wcw.is_active_member(user):
        await wcw.remove_user(user)
        await interaction.response.send_message("Hope you've enjoyed your stay at WCW!", ephemeral=True)
    else:
        await interaction.response.send_message("You aren't part of WCW!", ephemeral=True)



@bot.tree.command(name="wcw_partake", description="Enlighten thyself of the beauty of the written word.")
async def wcw_partake(interaction: discord.Interaction):
    user = interaction.user
    if wcw.is_active_member(user):
        await interaction.response.send_message("It seems that you have already been cordially invited to our commune, that which is colloquially known as \"Word Count Wednesday.\"", ephemeral=True)
    else:
        await wcw.add_user(user)     
        await interaction.response.send_message("Prithee and well met, thou artful scribe. Thou shalt make merry with like-minded auteurs in the lobby we call \"Word Count Wednesday.\"", ephemeral=True)



@bot.tree.command(name="wcw_withdraw", description="Remove thyself from our commune, and regress to oblivion and obscurity.")
async def wcw_withdraw(interaction: discord.Interaction):
    user = interaction.user
    if wcw.is_active_member(user):
        await wcw.remove_user(user)
        await interaction.response.send_message("It is with a heavy weight in our hearts that we bid you adieu, O wonderous writer friend. May our paths intertwine again in the near future.", ephemeral=True)

    else:
        await interaction.response.send_message("Fie! Begone, false disciple! You never knew the true meaning of Word Count Wednesday!", ephemeral=True)



@bot.tree.command(name="wcw_goal", description="Set your weekly writing goal! It can be a word count, a description or something else.")
@app_commands.describe(goal="Your weekly goal! This is not enforced.")
async def wcw_set_goal(interaction: discord.Interaction, goal: str):  
    user = interaction.user
    if wcw.is_active_member(user):
        await wcw.edit_user(user, goal=goal)
        await interaction.response.send_message("Your goal has been set!", ephemeral=True)
    else:
        await interaction.response.send_message("You aren't part of WCW!", ephemeral=True)



@bot.tree.command(name="wcw_find_submissions", description="Find a user or all user's submissions for this week!")
@app_commands.describe(user="Select a user, or leave blank to view all")
async def wcw_find_submissions(interaction: discord.Interaction, user: discord.User = None):  
    message = f"**WCW Submissions**:\n"
    if user:
        if not wcw.is_active_member(user):
            await interaction.response.send_message("This user is not in WCW!", ephemeral=True)
            return

        message += f"{shared.format_username(shared.wcw_tracked_users[user.id]['user_nickname'])}: " + shared.get_submission_link(user.id, wcw=True)
    else:
        for user_id in shared.wcw_tracked_users.keys():
            if shared.wcw_tracked_users[user_id]['active']:
                message += f"{shared.format_username(shared.wcw_tracked_users[user_id]['user_nickname'])}: " + shared.get_submission_link(user_id, wcw=True)
                message += "\n"
    
    await interaction.response.send_message(message, ephemeral=True)



@bot.tree.command(name="wcw_ping", description="Set your ping preference! Reminders are at 9 AM and 9 PM every Wednesday")
@app_commands.describe(ping="Whether or not you want pings")
async def wcw_set_goal(interaction: discord.Interaction, ping: bool):  
    user = interaction.user
    if wcw.is_active_member(user):
        await wcw.edit_user(user, ping=ping)
        await interaction.response.send_message(f"Your ping status has been set to: {ping}", ephemeral=True)
    else:
        await interaction.response.send_message("You aren't part of WCW!", ephemeral=True)


@bot.tree.command(name="wcw_view_stats", description="View your own or someone else's stats!")
@app_commands.describe(user="The user you want to view the stats of. Leave blank for yourself")
async def wcw_set_goal(interaction: discord.Interaction, user: discord.User = None):
    if user is None:
        user = interaction.user
    
    if not wcw.is_active_member(user):
        await interaction.response.send_message("This user is not part of WCW!", ephemeral=True)
        return

    message = f"**WCW Stats:**\n" + wcw.view_user(user)

    await interaction.response.send_message(message, ephemeral=True)


# DEBUG
@bot.tree.command(name="wcw_debug", description="E")
@app_commands.describe(debug="int")
async def wcw_debug(interaction: discord.Interaction, debug: int = 0):
    await interaction.response.send_message(f"Sending message of id {debug}...", ephemeral=True)
    await wcw.send_announcement_message(debug=debug) 
    
