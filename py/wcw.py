"""
wcw.py
This file contains functions related to the WCW tracking aspect of the bot
"""

import discord
from discord.ext import tasks
from datetime import datetime
import os
import json
import subprocess
from shared import bot, logger
import shared

def is_warden(user):
    return user.id in shared.WCW_WARDENS

# @tasks.loop(minutes=1)  # Save data every 8 hours
async def save_data_task():
    data = {
        "current_week": shared.wcw_current_week,
        "tracked_users": shared.wcw_tracked_users,
        "announcement_channel": shared.wcw_announcement_channel,
        "allowed_channels": shared.wcw_allowed_channels,
    }
    
    with open(shared.WCW_SAVED_DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ WCW data saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"WCW data saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


async def on_message_wcw(message):
    if "#wcw" in message.content.lower():
        if message.author.id not in shared.wcw_tracked_users:
            await message.channel.send(f"You are not tracked in WCW! Add yourself with /wcw_join")
            return

        
        


