"""
bot.py
This file contains the bot instance, and acts as the entry point for the bot
"""

from discord.ext import tasks # type: ignore
import json
import asyncio
from duel import register_duel_commands, set_tracked_users_reference, cleanup_expired_duels, load_duel_data
from chain import register_chain_commands, set_tracked_users_reference as set_chain_tracked_users, load_chain_data 

import shared
from shared import bot, logger
import daily
import  daily_commands

def load_data():
    try:
        with open(shared.SAVED_DATA_PATH, "r") as f:
            data = json.load(f)
            shared.current_day = data.get("current_day", shared.current_day)
            shared.season = data.get("season", shared.season)
            loaded_users = data.get("tracked_users", {})
            shared.announcement_channel = data.get("announcement_channel", shared.allowed_channels[0] if shared.allowed_channels else None)
            
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
