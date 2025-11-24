import discord
from discord import app_commands
import shared
from shared import bot, logger


@bot.tree.command(name="wcw_join", description="Join or leave WCW!")
@app_commands.describe(joining="Whether or not you're joining")
async def wcw_join(interaction: discord.Interaction, joining: bool, pretentious = False):
    user = interaction.author
    if user.id in shared.wcw_tracked_users:
        if joining:
            if pretentious:
                await interaction.channel.message("It seems that you have already been cordially invited to our commune, that which we call \"Word Count Wednesday\" in colloquial terms.")
            else:
                await interaction.channel.message("You're already part of WCW!")
        else:
            shared.wcw_tracked_users[user.id]['active'] = False

            if pretentious:
                await interaction.channel.message("It is with a heavy weight in our hearts that we bid you adieu, O wonderous writer friend. May our paths intertwine again in the near future.")
            else:
                await interaction.channel.message("Hope you've enjoyed your stay at WCW!")
    else:
        if not joining:
            if pretentious:
                await interaction.channel.message("Fie! Begone, false disciple! You never knew the true meaning of Word Count!")
            else:
                await interaction.channel.message("You aren't part of WCW!")
        else:
            user = interaction.author
            member = await interaction.guild.fetch_member(user.id)
            user_nickname = member.nick if member and member.nick else user.name
            shared.wcw_tracked_users[user.id] = {
                'username': user.name,
                'user_nickname': user_nickname,
                'status': 'pending', # 'standby' for not yet submitted, 'excused' if they talk to dc, 'indebted' if they missed last week's too, 'submitted' if submitted
                'submissions': 0,
                'active': True,
            }
            if pretentious:
                await interaction.channel.message("Prithee and well met, thou artful scribe. Thou shalt make merry with like-minded auteurs in the lobby we call \"Word Count Wednesday.\"")
            else:
                await interaction.channel.message("Welcome to WCW!")
    return



@bot.tree.command(name="wcw_partake", description="Involve thyself in our weekly conference in which we congregate to share amongst ourselves the beauty of the written word")
@app_commands.describe(membership="If you want to join")
async def wcw_partake(interaction: discord.Interaction, membership: bool):
    wcw_join(interaction, membership, True)