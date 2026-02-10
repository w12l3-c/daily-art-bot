"""
bot.py
This file contains the bot instance, and acts as the entry point for the bot
"""

from discord.ext import tasks
import json
import asyncio
from duel import register_duel_commands, set_tracked_users_reference, cleanup_expired_duels, load_duel_data
from chain import register_chain_commands, set_tracked_users_reference as set_chain_tracked_users, load_chain_data 

import shared
from shared import bot, logger
import daily
import daily_commands
import challenge
import challenge_commands
import wcw
import wcw_commands
import forced_events  # Import forced events to register debug commands

def load_data():
    try:
        # load daily art and challenge json
        with open(shared.SAVED_DATA_PATH, "r") as f:
            data = json.load(f)
            shared.guild_id = data.get("guild_id", shared.guild_id)
            shared.current_day = data.get("current_day", shared.current_day)
            shared.season = data.get("season", shared.season)
            shared.season_days = data.get("season_days", shared.season_days)
            shared.season_theme = data.get("season_theme", shared.season_theme)
            loaded_users = data.get("tracked_users", {})
            loaded_archived = data.get("archived_users", {})
            shared.announcement_channel = data.get("announcement_channel", shared.allowed_channels[0] if shared.allowed_channels else shared.announcement_channel)

            shared.challenge_day = data.get("challenge_day", shared.challenge_day)
            shared.challenge_length = data.get("challenge_length", shared.challenge_length)
            shared.challenge_theme = data.get("challenge_theme", shared.challenge_theme)
            shared.challenge_number = data.get("challenge_number", shared.challenge_number)
            
            # Load allowed_channels if it exists, otherwise keep the current one
            loaded_allowed_channels = data.get("allowed_channels", shared.allowed_channels)
            if loaded_allowed_channels:
                shared.allowed_channels = loaded_allowed_channels
            
            # Convert string keys back to integers (JSON stores dict keys as strings)
            shared.tracked_users = {}
            for user_id_str, user_data in loaded_users.items():
                try:
                    user_id_int = int(user_id_str)
                    shared.tracked_users[user_id_int] = user_data
                except ValueError:
                    logger.warning(f"Could not convert user ID '{user_id_str}' to integer")

            shared.archived_users = {}
            for user_id_str, user_data in loaded_archived.items():
                try:
                    user_id_int = int(user_id_str)
                    shared.archived_users[user_id_int] = user_data
                except ValueError:
                    logger.warning(f"Could not convert archived user ID '{user_id_str}' to integer")
            
            # Load duel data if it exists
            duel_data = data.get("duel", None)
            load_duel_data(duel_data)
            
            # Load chain data if it exists
            chain_data = data.get("chain", None)
            load_chain_data(chain_data)
                    
            print(f"✅ Data loaded successfully! (Day {shared.current_day}, Season {shared.season})")
            logger.info(f"Data loaded successfully! (Day {shared.current_day}, Season {shared.season})")
            logger.info(f"Loaded {len(shared.tracked_users)} users with IDs: {list(shared.tracked_users.keys())}")
            logger.info(f"Announcement channel set to: {shared.announcement_channel}")
            logger.info(f"Allowed channels: {shared.allowed_channels}")
    except (FileNotFoundError, json.JSONDecodeError):
        print("⚠️ No save file found. Starting fresh.")
        logger.warning("No save file found. Starting fresh.")
        shared.current_day = 1
        shared.season = 7
        shared.tracked_users = {}
        shared.announcement_channel = shared.allowed_channels[0] if shared.allowed_channels else None
        load_duel_data(None)  # Initialize empty duel data
        load_chain_data(None)  # Initialize empty chain data

    try:
        # load wcw json
        with open(shared.WCW_SAVED_DATA_PATH, "r") as f:
            data = json.load(f)
            shared.wcw_current_week = data.get("current_week", shared.wcw_current_week)
            loaded_users = data.get("tracked_users", {})
            shared.wcw_announcement_channel = data.get("announcement_channel", shared.wcw_allowed_channels[0] if shared.wcw_allowed_channels else None)
            shared.wcw_last_message_week = data.get("last_message_week", shared.wcw_last_message_week)
            shared.wcw_last_reminder_1_week = data.get("last_reminder_1_week", shared.wcw_last_reminder_1_week)
            shared.wcw_last_reminder_2_week = data.get("last_reminder_2_week", shared.wcw_last_reminder_2_week)

            # Load allowed_channels if it exists, otherwise keep the current one
            loaded_allowed_channels = data.get("allowed_channels", shared.wcw_allowed_channels)
            if loaded_allowed_channels:
                shared.wcw_allowed_channels = loaded_allowed_channels
            
            # Convert string keys back to integers (JSON stores dict keys as strings)
            shared.wcw_tracked_users = {}
            for user_id_str, user_data in loaded_users.items():
                try:
                    user_id_int = int(user_id_str)
                    shared.wcw_tracked_users[user_id_int] = user_data
                except ValueError:
                    logger.warning(f"Could not convert user ID '{user_id_str}' to integer")
                    
            print(f"✅ WCW data loaded successfully! (Week {shared.wcw_current_week})")
            logger.info(f"WCW data loaded successfully! (Week {shared.wcw_current_week})")
            logger.info(f"Loaded {len(shared.wcw_tracked_users)} users with IDs: {list(shared.wcw_tracked_users.keys())}")
            logger.info(f"WCW announcement channel set to: {shared.wcw_announcement_channel}")
            logger.info(f"WCW allowed channels: {shared.wcw_allowed_channels}")
    except (FileNotFoundError, json.JSONDecodeError):
        print("⚠️ No WCW save file found. Starting fresh.")
        logger.warning("No WCW save file found. Starting fresh.")
        shared.wcw_current_week = 10
        shared.wcw_tracked_users = {}
        shared.wcw_announcement_channel = shared.wcw_allowed_channels[0] if shared.wcw_allowed_channels else None

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    logger.info(f'Bot logged in as {bot.user}')
    try:
        load_data()
        
        # Initialize duel system with tracked users reference
        try:
            set_tracked_users_reference(shared.tracked_users)
            await register_duel_commands(bot)
            print("✅ Duel commands registered successfully")
            logger.info("Duel commands registered successfully")
        except Exception as e:
            print(f"❌ Failed to register duel commands: {e}")
            logger.error(f"Failed to register duel commands: {e}")
        
        # Initialize chain system with tracked users reference
        try:
            set_chain_tracked_users(shared.tracked_users)
            await register_chain_commands(bot)
            print("✅ Chain commands registered successfully")
            logger.info("Chain commands registered successfully")
        except Exception as e:
            print(f"❌ Failed to register chain commands: {e}")
            logger.error(f"Failed to register chain commands: {e}")
        
        # Small delay to ensure commands are properly registered before syncing
        await asyncio.sleep(1)
        
        # Sync ALL commands (including duel and chain) AFTER registering them
        try:
            synced = await bot.tree.sync()  # Sync slash commands
            print(f"Synced {len(synced)} commands.")
            logger.info(f"Synced {len(synced)} commands.")
        except Exception as e:
            print(f"Error syncing commands: {e}")
            logger.error(f"Error syncing commands: {e}")
            
    except Exception as e:
        print(f"Error in on_ready: {e}")
        logger.error(f"Error in on_ready: {e}")

    daily.send_daily_art_message.start()
    daily.save_data_task.start()
    daily.ping_jailed_users.start()
    cleanup_duels.start()


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.channel.id in shared.allowed_channels:
        await daily.on_message_daily(message)

    if message.channel.id in shared.wcw_allowed_channels:
        await wcw.on_message_wcw(message)
    
    # Process other commands
    await bot.process_commands(message)

@tasks.loop(hours=shared.time_deploy)  # Check every hour for expired duels
async def cleanup_duels():
    """Clean up expired duels every hour"""
    try:
        cleaned = await cleanup_expired_duels(bot, shared.allowed_channels, shared.announcement_channel)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired duels")
    except Exception as e:
        logger.error(f"Error cleaning up duels: {e}")

bot.run(shared.BOT_TOKEN)
