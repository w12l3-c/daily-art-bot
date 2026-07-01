from discord.ext import commands

from artbot.AppContext import AppContext
from artbot.BotLifecycleCog import BotLifecycleCog
from artbot.CommandErrors import handle_app_command_error
from artbot.core.chain.ChainCommands import ChainCog
from artbot.core.challenge.ChallengeCommands import ChallengeCog
from artbot.core.daily.DailyCommands import DailyCog
from artbot.core.duel.DuelCommands import DuelCog
from artbot.core.wcw.WcwCommands import WcwCog
from artbot.debug.DebugCommands import DebugCog


COG_TYPES = (
    BotLifecycleCog,
    DailyCog,
    WcwCog,
    ChallengeCog,
    DuelCog,
    ChainCog,
    DebugCog,
)


async def register_cogs(bot: commands.Bot, app_context: AppContext) -> None:
    for cog_type in COG_TYPES:
        if bot.get_cog(cog_type.__name__) is None:
            await bot.add_cog(cog_type(bot, app_context))

    bot.tree.on_error = handle_app_command_error
