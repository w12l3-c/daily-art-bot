"""
daily.py
This file contains functions related to the daily art tracking aspect of the bot
"""
import asyncio
import discord
from discord.ext import tasks
from datetime import datetime
import os
import json
import subprocess
import random
import forced_events
from duel import update_duel_progress, get_duel_rankings, get_duel_data
from chain import process_chain_submission, get_chain_data
from challenge import end_challenge, is_challenge_active
import asyncio

import shared
from shared import bot, logger, save_data_task

def reset_user_stats():
    """Reset all user stats for a new season while preserving core identity info"""
    for user in shared.tracked_users.values():
        # Keep these fields (user identity, preferences and Challenge stats)
        username = user['username']
        user_nickname = user['user_nickname'] 
        ping = user['ping']
        in_challenges = user['in_challenges']
        challenge_participations = user['challenge_participations']
        challenge_completions = user['challenge_completions']
        challenge_streak = user['challenge_streak']
        challenge_submissions = user['challenge_submissions']
        
        # Reset all stats to starting values
        user.update(shared.get_default_user_values(
            username=username,
            user_nickname=user_nickname,
            ping=ping,
            in_challenges=in_challenges,
            challenge_participations=challenge_participations,
            challenge_completions=challenge_completions,
            challenge_streak=challenge_streak,
            challenge_submissions=challenge_submissions
        ))
    
    logger.info(f"Reset stats for {len(shared.tracked_users)} users for new season")
    print(f"✅ Reset stats for {len(shared.tracked_users)} users for new season")


def message_has_media(message):
    return (message.attachments and any(
            attachment.content_type.startswith("image/") or 
            attachment.content_type.startswith("video/mp4") or
            attachment.filename.lower().endswith(('.mp4', '.mov'))
            for attachment in message.attachments
        )) or (message.embeds and any(
            embed.type in ['image', 'video'] or 
            (embed.image and embed.image.url) or 
            (embed.video and embed.video.url)
            for embed in message.embeds
        )) or (message.attachments and any(
            attachment.content_type.startswith("image/") or 
            attachment.content_type.startswith("video/mp4") or
            attachment.filename.lower().endswith(('.mp4', '.mov'))
            for attachment in message.attachments
        ))


async def on_message_daily(message):
    if message.author.id == 374012168028291073 and message.content.startswith("🔥"):
        guild = message.guild
        member = guild.get_member(message.author.id)
        nickname = member.nick if member and member.nick else member.name
        await message.channel.send(f"Hi! {nickname} <3")

    # Check if the message has an image/video attachment, is a forwarded message with media, or is a reply to a message that has media
    has_media = message_has_media(message)
    
    # Check referenced messages (replies/forwards) safely 
    if not has_media and message.reference is not None and isinstance(message.reference.resolved, discord.Message):
        # Check if it's a self-reply with media
        if message_has_media(message.reference.resolved) and (message.reference.resolved.author == message.author or message.author in shared.MOD_IDS):
            has_media = True

            # Allows daily bot admins to add dailies for others
            if message.author.id in shared.MOD_IDS or shared.has_admin_or_mod_permissions(message):
                message = message.reference.resolved

        else:
            # Check forwarded message snapshots safely
            try:
                snapshots = getattr(message.reference.resolved, "message_snapshots", None)
                if snapshots:
                    # Make a copy to avoid race conditions
                    snapshots_copy = list(snapshots)
                    if snapshots_copy and isinstance(snapshots_copy[0], discord.MessageSnapshot):
                        has_media = message_has_media(snapshots_copy[0])
            except (IndexError, AttributeError):
                # If there's any error accessing snapshots, treat as no media
                pass
    
    if has_media:
        content_lower = message.content.lower()  # Convert message to lowercase for case-insensitive tagging

        # Handle badge uploads (specific role required)
        if "#badge" in content_lower:
            if await shared.handle_badge_upload(message):
                return  # Badge handled, don't process as regular art
        
        # Auto-track users who have the "daily" Discord role (if not already tracked)
        if message.author.id not in shared.tracked_users:
            # Check if user has the "Dailies Challenger" role
            member = message.guild.get_member(message.author.id)
            print(member.roles)
            if any(role.name.lower() == "dailies challenger" for role in member.roles):
                # Automatically add user to tracking if they have the "Dailies Challenger" role
                user_nickname = member.nick if member and member.nick else message.author.name
                

                shared.tracked_users[message.author.id] = shared.get_default_user_values(username = message.author.name, user_nickname=user_nickname)

                print(f"🎯 Auto-tracked {message.author.name} due to 'Dailies Challenger' role")
                logger.info(f"Auto-tracked {message.author.name} due to 'Dailies Challenger' role")
                await message.channel.send(f"🎨 Welcome to daily art tracking, {message.author.display_name}! You've been automatically added due to your 'Dailies Challenger' role.")

        if message.author.id in shared.tracked_users:
            user_data = shared.tracked_users[message.author.id]
            
            # Update user's nickname to current Discord nickname
            member = message.guild.get_member(message.author.id)
            if member:
                current_nickname = member.nick if member.nick else message.author.name
                if user_data['user_nickname'] != current_nickname:
                    old_nickname = user_data['user_nickname']
                    user_data['user_nickname'] = current_nickname
                    logger.info(f"Updated nickname for {message.author.name}: '{old_nickname}' -> '{current_nickname}'")
            
            if "#daily" in content_lower:

                # There's a 1/10 chance that Zak will get yelled at whenever submitting a daily
                random.seed()
                should_yell_at_zak = message.author.id == 472930608734142464 and random.random() * 10 < 1
                if should_yell_at_zak:
                    await message.channel.send(f"<@{message.author.id}> kekekekekekekeke")
                elif user_data['submission']:
                    # User already submitted daily art, count this as buffer
                    user_data['buffer'] = user_data.get('buffer', 0) + 1
                    print(f"🛑 {message.author.name} submitted additional #daily art as buffer.")
                    logger.info(f"{message.author.name} submitted additional #daily art as buffer.")
                    await message.channel.send(f"📌 {message.author.display_name}, you've already submitted today's art! This has been recorded as buffer art.")
                else:
                    # First daily submission
                    user_data['submission'] = f"{message.channel.id}/{message.id}"  # Mark as official art submission
                    if user_data["in_challenges"] and is_challenge_active():
                        print(f"✅ {message.author.name} completed their challenge.")
                        logger.info(f"{message.author.name} completed their challenge.")
                        await message.channel.send(f"{message.author.display_name}, you have completed your challenge today!")
                    else:
                        print(f"✅ {message.author.name} submitted official art.")
                        logger.info(f"{message.author.name} submitted official art.")
                        await message.channel.send(f"🎨 {message.author.display_name}, your art has been recorded for today! (Submission #{user_data['parole_days'] + 1})")
                        
                
                # Update duel progress for this user (regardless of buffer or daily)
                updated_duels = update_duel_progress(message.author.id, datetime.now())
                if updated_duels:
                    logger.info(f"Updated {len(updated_duels)} duels for {message.author.name}")

            elif "#buffer" in content_lower:
                user_data['buffer'] = user_data.get('buffer', 0) + 1  # Increase buffer count
                print(f"🛑 {message.author.name} submitted buffer art.")
                logger.info(f"{message.author.name} submitted buffer art.")
                await message.channel.send(f"📌 {message.author.display_name}, your buffer art has been recorded! This will not count for today's submission.")

            elif "#chain" in content_lower:
                # Handle chain submission - pass the first attachment if available, or None for forwarded messages
                first_attachment = message.attachments[0] if message.attachments else None
                chain_processed = await process_chain_submission(message.author.id, message, first_attachment)
                
                # Also count chain submissions towards daily/buffer art
                if chain_processed:
                    if user_data['submission']:
                        # User already submitted daily art, count chain as buffer
                        user_data['buffer'] = user_data.get('buffer', 0) + 1
                        print(f"🔗 {message.author.name} submitted chain art as buffer (already has daily submission).")
                        logger.info(f"{message.author.name} submitted chain art as buffer.")
                        await message.channel.send(f"🔗 {message.author.display_name}, your chain submission has been recorded! This also counts as buffer art since you've already submitted today.")
                    else:
                        # First submission of the day, count as daily art
                        user_data['submission'] = f"{message.channel.id}/{message.id}"
                        print(f"🔗 {message.author.name} submitted chain art as daily submission.")
                        logger.info(f"{message.author.name} submitted chain art as daily submission.")
                        await message.channel.send(f"🔗 {message.author.display_name}, your chain submission has been recorded! This also counts as today's daily art.")
                    
                    # Update duel progress for chain submissions too
                    updated_duels = update_duel_progress(message.author.id, datetime.now())
                    if updated_duels:
                        logger.info(f"Updated {len(updated_duels)} duels for {message.author.name} (chain submission)")

            else:
                print(f"📸 {message.author.name} uploaded an image but didn't tag it as art.")
                logger.info(f"{message.author.name} uploaded an image but didn't tag it as art.")

    
# Edit the seconds 
@tasks.loop(minutes=1)
async def send_daily_art_message():
    now = shared.now_et()   
    
    if (now.hour == 0 and now.minute <= 1 and shared.last_daily_message_day != shared.now_et_day_str()) or forced_events.forced_daily:  # 12:15-12:45 AM EST (4:15-4:45 AM UTC)
        shared.last_daily_message_day = shared.now_et_day_str()

        print(f"Daily message check SUCCESS - Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} EST (Hour: {now.hour}, Minute: {now.minute})")
        logger.info(f"Daily message check SUCCESS - Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} EST (Hour: {now.hour}, Minute: {now.minute})")
        logger.info(f"Forced event: {forced_events.forced_daily}")
        
        messages = build_reminder_message(3)
        
        logger.info("Daily reset window reached - advancing day")
        
        
        # Get channel for sending message
        channel = bot.get_channel(shared.announcement_channel)
        
        # Only send daily message and advance day if there are tracked users
        if shared.tracked_users:
            if channel:
                print("Sending daily art message - 12:00 AM ET...")
                logger.info("Sending daily art message - 12:00 AM ET...")
                for message in messages:
                    await channel.send(message)
            else:
                logger.error(f"Could not send daily message - announcement channel {shared.announcement_channel} not found")

            print(f"Day {shared.current_day} has ended!")
            logger.info(f"Day {shared.current_day} has ended!")

            shared.current_day += 1
            if is_challenge_active():
                print(f"Challenge {shared.challenge_day} has ended!")
                logger.info(f"Challenge {shared.challenge_day} has ended!")

                shared.challenge_day += 1

                print(f"Challenge day is now {shared.challenge_day}")
                logger.info(f"Challenge {shared.challenge_day}")

            print(f"Day is now {shared.current_day}")
            logger.info(f"Day is now {shared.current_day}")
            
        else:
            print("No tracked users - pausing season progression")
            logger.info("No tracked users - season paused until users are added")

        if shared.current_day >= shared.season_days + 1:
            badge_pathway = f"badges/UWVAC_Badges_Season{shared.season}.png"
            badge = None
            if os.path.exists(badge_pathway):
                badge = discord.File(badge_pathway)
            results_message = f"# 🎉 **Season {shared.season} has ended!** 🎉 \n"
            results_message += f"🏆 **Congratulations to the all inmates!** 🏆\n\n"
            shared.tracked_users_list = list(shared.tracked_users.values())
            shared.tracked_users_list.sort(key=lambda x: (-x['parole_days'], x['missing_days'], -x['revival']))
            
            rank = 1
            prev_user = None
            grouped_users = [] 

            for index, user in enumerate(shared.tracked_users_list):
                # Check if this user has the same stats as the previous user
                if prev_user and (
                    prev_user['parole_days'] == user['parole_days'] and
                    prev_user['missing_days'] == user['missing_days'] and
                    prev_user['revival'] == user['revival']
                ):
                    grouped_users.append(user['user_nickname']) 
                else:
                    if grouped_users:
                        logger.info(f"Rank {rank}: {', '.join(grouped_users)} | Parole: {prev_user['parole_days']} | Missing: {prev_user['missing_days']} | Revival: {prev_user['revival']}")
                        results_message += f"{rank}. **{', '.join(grouped_users)}**:     "
                        results_message += f"🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n"

                    rank = index + 1 
                    grouped_users = [user['user_nickname']]
                prev_user = user 
                logger.debug(f"Grouped users: {grouped_users}")
            if grouped_users:
                results_message += f"{rank}. **{', '.join(grouped_users)}**:    "  
                results_message += f"🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n"

            results_message += f"\n**Funny Achievements:**\n"
            
            # Check if we have any users to avoid crashes
            if not shared.tracked_users:
                results_message += "No tracked users for achievements.\n"
            else:
                max_revival = max(user['revival'] for user in shared.tracked_users.values())
                highest_revival_users = [user['user_nickname'] for user in shared.tracked_users.values() if user['revival'] == max_revival]
                max_buffer = max(user['buffer'] for user in shared.tracked_users.values())
                highest_buffer_users = [user['user_nickname'] for user in shared.tracked_users.values() if user['buffer'] == max_buffer]
                
                # Only show achievements if someone actually has meaningful stats
                if max_buffer > 0:
                    results_message += f"**💾 Most Remaining Buffer Art:** {', '.join(highest_buffer_users)} - {max_buffer}\n"
                
                if max_revival > 0:
                    results_message += f"**😇 Most Revived:** {', '.join(highest_revival_users)} - {max_revival}\n"
                
                if max_buffer == 0 and max_revival == 0:
                    results_message += "🏆 **Perfect Season!** No one died or needed buffer art! 🎉\n"
            
            # Add duel rankings
            duel_rankings = get_duel_rankings()
            if duel_rankings:
                results_message += f"\n**⚔️ Duel Champions:**\n"
                for i, duelist in enumerate(duel_rankings[:5], 1):  # Top 5 duelists
                    results_message += f"**{i}.** {duelist['user_nickname']} - {duelist['wins']}W/{duelist['losses']}L ({duelist['win_rate']:.1f}% win rate)\n"
                
                # Special achievements
                if duel_rankings:
                    most_wins = duel_rankings[0]
                    most_active = max(duel_rankings, key=lambda x: x['total'])
                    best_win_rate = max([d for d in duel_rankings if d['total'] >= 3], key=lambda x: x['win_rate'], default=None)
                    
                    results_message += f"\n🏆 **Most Duel Wins:** {most_wins['user_nickname']} ({most_wins['wins']} wins)\n"
                    results_message += f"⚔️ **Most Active Duelist:** {most_active['user_nickname']} ({most_active['total']} duels)\n"
                    if best_win_rate:
                        results_message += f"🎯 **Best Win Rate:** {best_win_rate['user_nickname']} ({best_win_rate['win_rate']:.1f}%)\n"
            
            results_message += f"\nCongratulations to all participants! See you all next season🎉\n"
            
            # Get channel for season end messages
            channel = bot.get_channel(shared.announcement_channel)
            if channel:
                # Split message if it exceeds Discord's 2000 char limit (using 1900 to be safe)
                MAX_LENGTH = 1900
                ZERO_WIDTH_BREAK = "\n\u200b\n"  # hard reset for Discord markdown

                # Split message if needed
                if len(results_message) > MAX_LENGTH:
                    lines = results_message.split('\n')
                    chunks = []
                    current_chunk = ""

                    for line in lines:
                        # +1 for newline
                        if len(current_chunk) + len(line) + 1 > MAX_LENGTH:
                            # Force a markdown reset at chunk boundary
                            safe_chunk = current_chunk.rstrip() + ZERO_WIDTH_BREAK
                            chunks.append(safe_chunk)
                            current_chunk = line + "\n"
                        else:
                            current_chunk += line + "\n"

                    if current_chunk.strip():
                        chunks.append(current_chunk.rstrip())

                    # Debug info (optional but useful)
                    logger.info(f"Season results split into {len(chunks)} chunks")
                    for i, c in enumerate(chunks, 1):
                        logger.debug(f"Chunk {i} length: {len(c)}")

                    # Send badge first if available, then send chunks separately
                    if badge:
                        await channel.send("🎉 **Season Badge** 🎉", file=badge)
                        await asyncio.sleep(0.2)
                    
                    # Send all chunks without attachment
                    for i, chunk in enumerate(chunks):
                        await asyncio.sleep(0.1)
                        await channel.send(chunk)

                else:
                    # Message fits in one send
                    if badge:
                        await channel.send(results_message, file=badge)
                    else:
                        await channel.send(results_message)
                
                # Send badge message separately if we split the main message
                if len(results_message) > MAX_LENGTH:
                    await channel.send(f"🎨 **The {shared.season_theme} badge** 🎨")
                else:
                    await channel.send(f"🎨 **The {shared.season_theme} badge** 🎨")
            else:
                logger.error(f"Could not send season end results - announcement channel {shared.announcement_channel} not found")

            # Reset all user stats for the new season
            reset_user_stats()
            
            # Clear any active duels for the new season
            try:
                from duel import clear_all_duels
                clear_all_duels()
                logger.info("Cleared all active duels for new season")
            except Exception as e:
                logger.warning(f"Could not clear duels for new season: {e}")

            shared.current_day = 1
            shared.season += 1
            season_message = f"# 🎉 **Season {shared.season} begins tomorrow!** 🎉\n"
            season_message += f"📊 **All user stats have been reset!** Fresh start for everyone! 🔄\n"
            
            if channel:
                await channel.send(season_message)
            else:
                logger.error(f"Could not send new season message -  announcement channel {shared.announcement_channel} not found")

        for user in shared.tracked_users.values():
            # Initialize consecutive_missed_days if it doesn't exist (for existing users)
            if 'consecutive_missed_days' not in user:
                user['consecutive_missed_days'] = 0
            
            # Process daily submission status first
            if not user['submission']:
                if not user['probation']:
                    # Increment consecutive missed days
                    user['consecutive_missed_days'] += 1
                    user['missing_days'] += 1
                    
                    # Buffer rules: Can only save from death if NOT consecutive days
                    # If consecutive_missed_days >= 2, buffer cannot save them
                    can_use_buffer = user['consecutive_missed_days'] == 1 and user['buffer'] > 0
                    
                    if can_use_buffer:
                        # Consume buffer to save from missing day (only on first consecutive miss)
                        user['buffer'] -= 1
                        user['missing_days'] -= 1
                        logger.info(f"Buffer saved {user['user_nickname']} from missing day (non-consecutive)")
                        
                        # Buffer saved them - revive if needed
                        if user['deceased']:
                            user['revival'] += 1
                            user['deceased'] = False
                    else:
                        # No buffer can save them OR consecutive miss
                        if user['consecutive_missed_days'] >= 2:
                            logger.info(f"{user['user_nickname']} missed {user['consecutive_missed_days']} consecutive days - buffer disabled")
                        
                        # Mark as deceased
                        if not user['deceased']:
                            user['deceased'] = True
                        user['deceased_days'] += 1
            else:
                # User submitted art - reset consecutive counter and restore buffer functionality
                user['consecutive_missed_days'] = 0
                user['parole_days'] += 1
                if user['deceased']:
                    user['revival'] += 1
                    user['deceased'] = False
                
                # Reduce missing days when they submit
                if user['missing_days'] > 0:
                    user['missing_days'] -= 1
                
                # Also consume buffer if they have any remaining missing days
                if user['missing_days'] > 0 and user['buffer'] > 0:
                    reduction = min(user['missing_days'], user['buffer'])
                    user['missing_days'] -= reduction
                    user['buffer'] -= reduction
                    logger.info(f"Auto-consumed {reduction} buffer for {user['user_nickname']} to reduce remaining missing days")

                if user["in_challenges"]:
                    user["challenge_submissions"] += 1


            # Reset daily submission flag for next day
            user['submission'] = ""
        
        # End challenge logic
        if is_challenge_active() and shared.challenge_day > shared.challenge_length:
            channel = bot.get_channel(shared.announcement_channel)

            # build message
            message = f"## Challenge #{shared.challenge_number}: \"{shared.challenge_theme}\" has ended!\n"

            message += "Completed: " + ", ".join(
                list(
                    map(
                        lambda user: shared.format_username(user["user_nickname"]),
                        filter(
                            lambda user: user["in_challenges"] and user["challenge_submissions"] >= shared.challenge_threshold,
                            shared.tracked_users.values()
                        )
                    )
                )
            )

            message += "\n\nFailed: " + ", ".join(
                list(
                    map(
                        lambda user: shared.format_username(user["user_nickname"]),
                        filter(
                            lambda user: user["in_challenges"] and user["challenge_submissions"] < shared.challenge_threshold,
                            shared.tracked_users.values()
                        )
                    )
                )
            )

            message += "\n\nGuys you gotta do #daily for it to count. Come on"

            if channel:
                await channel.send(message)    
            else:
                logger.error(f"Could not send challenge end results - announcement channel {shared.announcement_channel} not found")
            
            await end_challenge()
        
        
        await save_data_task()

        




def build_reminder_message(num = 1):        
    # Build the daily art message inline
    USERS_PER_LINE = 4
    messages = []

    users_not_sent = [u for u in shared.tracked_users.values() if not u['submission']]
    users_sent = [u for u in shared.tracked_users.values() if u['submission']]
    
    message = f"## Day Complete!\n" if num == 3 else ""

    message += f"**Season {shared.season} - {shared.season_theme}: Day {shared.current_day} - Daily Art Challenge** 🎨\n"
    message += f"**🔄 On parole:** \n"
    for i, user in enumerate(users_sent):
        if i % USERS_PER_LINE != 0:
            message += "  •  "
        elif i != 0:
            message += "\n"
        message += f"{shared.format_username(user['user_nickname'])} {'<happymiku:1178130719646679061>' if is_challenge_active() and user['in_challenges'] else ''}"
    
    # split message here to avoid 2k character limit
    messages.append(message)

    message = "\n\n**⛓️ Jailed:**\n"
    # message += "🧱"*20 + "\n"
    
    # Filter jailed and deceased users
    jailed_users = [user for user in users_not_sent if not user['deceased']]
    deceased_users = [user for user in users_not_sent if user['deceased']]
    
    for i, user in enumerate(jailed_users):
        if i % USERS_PER_LINE != 0:
            message += "  •  "
        elif i != 0:
            message += "\n"
        message += f"{shared.format_username(user['user_nickname'])} {'<happymiku:1178130719646679061>' if is_challenge_active() and user['in_challenges'] else ''}"

    message += "\n\n**🪦 Deceased:**\n"

    for i, user in enumerate(deceased_users):
        if i % USERS_PER_LINE != 0:
            message += "  •  "
        message += f"{shared.format_username(user['user_nickname'])} {'<happymiku:1178130719646679061>' if is_challenge_active() and user['in_challenges'] else ''}"
        if i % USERS_PER_LINE == USERS_PER_LINE - 1:
            message += "\n"
    
    if num == 1 or num == 2:
        message += "\n\n🚨 **Daily Art Reminder!** 🚨\n"
        message += f"**You have roughly {3 - num} hour{'s' if num == 1 else ''} before the daily reset!** ⏰\n\n"
    
    messages.append(message)
    message = ""


    # Find users who need to submit
    ping_users = []
    for user_id, user in shared.tracked_users.items():
        if user['ping'] and not user['submission']:
            member = bot.get_user(user_id)
            if member:
                ping_users.append(member.mention)
    
    if num == 1:
        if ping_users:
            message += f"Haven't submitted today: {' '.join(ping_users)}\n"
            message += "**Don't forget to submit your daily art! 🎨**"
        elif not jailed_users and not deceased_users:
            message += "**Great job everyone! All tracked users have submitted their art today! 🎉**"
        else:
            message += "**Make sure to submit your art if you haven't already!**"
        message += "\n-# You can toggle ping reminders with the /ping command"
    elif num == 2:
        if ping_users:
            message += f"Still need to submit: {' '.join(ping_users)}\n"
            message += "**Last chance to avoid the graveyard! Submit your art NOW! 🏃‍♂️💨**"
        elif not jailed_users and not deceased_users:
            message += "**Excellent! All tracked users are safe for today! 🎨✅**"    
        else:
            message += "**Make sure to submit your art if you haven't already!**"

    if message:
        messages.append(message)
    
    return messages

@tasks.loop(minutes=1)  # Check every 30 minutes to catch both warning times
async def ping_jailed_users():
    now = shared.now_et()
    # Add detailed time logging for debugging
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} ET (Hour: {now.hour})")
    
    messages = []
    if now.hour == 22 and now.minute <= 1  and shared.last_warning_1_day != shared.now_et_day_str(): 
        print("Sending daily art message + first warning - 10:00-10:30 PM EST...")
        logger.info("Sending daily art message + first warning - 10:00-10:30 PM EST...")
        shared.last_warning_1_day = shared.now_et_day_str()
        messages = build_reminder_message(1)
        
    elif now.hour == 23 and now.minute <= 1 and shared.last_warning_2_day != shared.now_et_day_str(): 
        print("Sending daily art message + final warning - 11:00-11:30 PM EST...")
        logger.info("Sending daily art message + final warning - 11:00-11:30 PM EST...")
        shared.last_warning_2_day = shared.shared.now_et_day_str()
        messages = build_reminder_message(2)
    
    if messages:  # Only send if we have a message (10:30 PM or 11:30 PM EST)
        channel = bot.get_channel(shared.announcement_channel)
        if channel:
            for message in messages:
                await channel.send(message)
        else:
            logger.error(f"Could not send warning message - announcement channel {shared.announcement_channel} not found")