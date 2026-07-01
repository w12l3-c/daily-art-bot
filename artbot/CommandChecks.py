from discord import app_commands

import artbot.shared as shared


async def get_interaction_member(interaction):
    user = interaction.user
    if getattr(user, "roles", None):
        return user

    guild = getattr(interaction, "guild", None)
    if guild is None:
        return user

    member = guild.get_member(user.id)
    if member is not None:
        return member

    try:
        return await guild.fetch_member(user.id)
    except Exception:
        return user


async def has_admin_or_mod_permissions(interaction) -> bool:
    member = await get_interaction_member(interaction)
    if not shared.has_admin_or_mod_permissions(member):
        raise app_commands.CheckFailure(
            "❌ You need administrator permissions or mod role to use this command."
        )
    return True


async def has_wcw_permissions(interaction) -> bool:
    member = await get_interaction_member(interaction)
    if not (
        interaction.user.id in shared.WCW_WARDENS
        or shared.has_admin_or_mod_permissions(member)
    ):
        raise app_commands.CheckFailure("You must be mod or warden to use this command!")
    return True


async def has_challenge_mod_permissions(interaction) -> bool:
    member = await get_interaction_member(interaction)
    if (
        not shared.has_admin_or_mod_permissions(member)
        and interaction.user.id not in shared.CHALLENGE_MODS
    ):
        raise app_commands.CheckFailure(
            "❌ You need administrator permissions or mod role to use this command."
        )
    return True


def requires_admin_or_mod():
    return app_commands.check(has_admin_or_mod_permissions)


def requires_wcw_permission():
    return app_commands.check(has_wcw_permissions)


def requires_challenge_mod():
    return app_commands.check(has_challenge_mod_permissions)
