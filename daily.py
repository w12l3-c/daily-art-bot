"""
daily.py
This file contains functions related to the daily art tracking aspect of the bot
"""
import discord
from discord.ext import tasks
from datetime import datetime
import os
import json
from bot import bot, allowed_channels, logger, tracked_users, reset_user_stats, announcement_channel, time_deploy, saved_data, subprocess, handle_badge_upload
from duel import update_duel_progress, get_duel_rankings, get_duel_data
from chain import process_chain_submission, get_chain_data

def reset_user_stats():
    """Reset all user stats for a new season while preserving core identity info"""
    for user in tracked_users.values():
        # Keep these fields (user identity and preferences)
        username = user['username']
        user_nickname = user['user_nickname'] 
        ping = user['ping']
        
        # Reset all stats to starting values
        user.update({
            'username': username,
            'user_nickname': user_nickname,
            'sent_image': False,
            'parole_days': 0,
            'deceased': False,
            'deceased_days': 0,
            'missing_days': 0,
            'consecutive_missed_days': 0,
            'revival': 0,
            'buffer': 0,
            'probation': False,
            'ping': ping,
            'duels_won': 0,
            'duels_lost': 0
        })
    
    logger.info(f"Reset stats for {len(tracked_users)} users for new season")
    print(f"✅ Reset stats for {len(tracked_users)} users for new season")

async def auto_commit_backup():
    """Automatically commit and push backup.json to git"""
    try:
        # Add backup.json to git
        result = subprocess.run(['git', 'add', 'backup.json'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode != 0:
            logger.warning(f"Git add failed: {result.stderr}")
            return False
        
        # Create commit message with current day and datetime
        commit_message = f"Auto-backup: Day {current_day} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}"
        
        # Commit the changes
        result = subprocess.run(['git', 'commit', '-m', commit_message], 
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode != 0:
            # If commit fails (e.g., no changes), log but don't treat as error
            logger.info(f"Git commit: {result.stdout if result.stdout else result.stderr}")
            return True  # No changes is not an error
        
        # Push to remote
        result = subprocess.run(['git', 'push', 'origin'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode != 0:
            logger.error(f"Git push failed: {result.stderr}")
            return False
        
        logger.info(f"✅ Successfully auto-committed and pushed backup for Day {current_day}")
        print(f"✅ Git auto-backup completed for Day {current_day}")
        return True
        
    except Exception as e:
        logger.error(f"Git auto-backup failed: {e}")
        return False


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

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.channel.id not in allowed_channels:
        return

    if message.author.id == 374012168028291073 and message.content.startswith("🔥"):
        guild = message.guild
        member = guild.get_member(message.author.id)
        nickname = member.nick if member and member.nick else member.name
        await message.channel.send(f"Hi! {nickname} <3")

    # Check if the message has an image/video attachment, is a forwarded message with media, or is a reply to a message that has media
    has_media = message_has_media(message) or (
        message.reference and
        isinstance(message.reference.resolved, discord.Message) and
        message.reference.resolved.author == message.author and
        message_has_media(message.reference.resolved)
    )
    
    if has_media:
        content_lower = message.content.lower()  # Convert message to lowercase for case-insensitive tagging
        
        # Handle badge uploads (specific role required)
        if "#badge" in content_lower:
            if await handle_badge_upload(message):
                return  # Badge handled, don't process as regular art
        
        # Auto-track users who have the "daily" Discord role (if not already tracked)
        if message.author.id not in tracked_users:
            # Check if user has the "Dailies Challenger" role
            member = message.guild.get_member(message.author.id)
            print(member.roles)
            if any(role.name.lower() == "dailies challenger" for role in member.roles):
                # Automatically add user to tracking if they have the "Dailies Challenger" role
                user_nickname = member.nick if member and member.nick else message.author.name
                
                tracked_users[message.author.id] = {
                    'username': message.author.name,
                    'user_nickname': user_nickname,
                    'sent_image': False,
                    'parole_days': 0,
                    'deceased': False,
                    'deceased_days': 0,
                    'missing_days': 0,
                    'consecutive_missed_days': 0,
                    'revival': 0,
                    'buffer': 0,
                    'probation': False,
                    'ping': False,  
                    'duels_won': 0,
                    'duels_lost': 0
                }

                print(f"🎯 Auto-tracked {message.author.name} due to 'Dailies Challenger' role")
                logger.info(f"Auto-tracked {message.author.name} due to 'Dailies Challenger' role")
                await message.channel.send(f"🎨 Welcome to daily art tracking, {message.author.display_name}! You've been automatically added due to your 'Dailies Challenger' role.")

        if message.author.id in tracked_users:
            user_data = tracked_users[message.author.id]

            if "#daily" in content_lower:
                if user_data['sent_image']:
                    # User already submitted daily art, count this as buffer
                    user_data['buffer'] = user_data.get('buffer', 0) + 1
                    print(f"🛑 {message.author.name} submitted additional #daily art as buffer.")
                    logger.info(f"{message.author.name} submitted additional #daily art as buffer.")
                    await message.channel.send(f"📌 {message.author.display_name}, you've already submitted today's art! This has been recorded as buffer art.")
                else:
                    # First daily submission
                    user_data['sent_image'] = True  # Mark as official art submission
                    print(f"✅ {message.author.name} submitted official art.")
                    logger.info(f"{message.author.name} submitted official art.")
                    await message.channel.send(f"🎨 {message.author.display_name}, your art has been recorded for today!")
                
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
                    if user_data['sent_image']:
                        # User already submitted daily art, count chain as buffer
                        user_data['buffer'] = user_data.get('buffer', 0) + 1
                        print(f"🔗 {message.author.name} submitted chain art as buffer (already has daily submission).")
                        logger.info(f"{message.author.name} submitted chain art as buffer.")
                        await message.channel.send(f"🔗 {message.author.display_name}, your chain submission has been recorded! This also counts as buffer art since you've already submitted today.")
                    else:
                        # First submission of the day, count as daily art
                        user_data['sent_image'] = True
                        print(f"🔗 {message.author.name} submitted chain art as daily submission.")
                        logger.info(f"{message.author.name} submitted chain art as daily submission.")
                        await message.channel.send(f"🔗 {message.author.display_name}, your chain submission has been recorded! This also counts as today's daily art.")
                    
                    # Update duel progress for chain submissions too
                    updated_duels = update_duel_progress(message.author.id, datetime.now())
                    if updated_duels:
                        logger.info(f"Updated {len(updated_duels)} duels for {message.author.name} (chain submission)")
                else:
                    # If chain processing failed and user didn't tag it as anything else, show the regular untagged message
                    if user_data['ping']:
                        await message.channel.send(f"⚠️ {message.author.display_name}, please tag your submission with `#daily` if it's an official art entry.")

            else:
                print(f"📸 {message.author.name} uploaded an image but didn't tag it as art.")
                logger.info(f"{message.author.name} uploaded an image but didn't tag it as art.")
                if user_data['ping']:
                    await message.channel.send(f"⚠️ {message.author.display_name}, please tag your submission with `#daily` if it's an official art entry.")

    # Process other commands
    await bot.process_commands(message)



# Edit the seconds 
@tasks.loop(minutes=30)  # Save data every 8 hours
async def send_daily_art_message():
    global current_day, season, season_theme, season_days, last_daily_message_day

    users_not_sent = [u for u in tracked_users.values() if not u['sent_image']]
    users_sent = [u for u in tracked_users.values() if u['sent_image']]
    print(season_theme)
    logger.debug(f"Current season theme: {season_theme}")
    message = f"## **Season {season} - {season_theme}: Day {current_day} - Daily Art Challenge** 🎨\n"
    message += f"**🔄 On parole:** \n{', '.join([u['user_nickname'] for u in users_sent])}\n"
    message += "\n**⛓️ Jailed:**\n"
    message += "🧱"*20 + "\n"

    # Filter users by category first
    jailed_users = [user for user in users_not_sent if not user['deceased']]
    deceased_users = [user for user in users_not_sent if user['deceased']]
    
    # Process jailed users
    for i, user in enumerate(jailed_users):
        message += f"|| {user['user_nickname']} 💨{user['missing_days']} || "

    message += "\n" + "🧱"*20 + "\n"
    
    message += "\n**🪦 Deceased:**\n"
    message += "☁️"*20 + "\n"
    
    # Process deceased users  
    for i, user in enumerate(deceased_users):
        message += f"|| {user['user_nickname']}(💨{user['missing_days']} 💀{user['deceased_days']} 😇{user['revival']}) || "
    
    message += "\n" + "☁️"*20

    # Daily reset logic at 12:30 AM EST (4:30 AM UTC) - only run once per day
    now = datetime.now()   
    print(f"Daily message check - Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC (Hour: {now.hour}, Minute: {now.minute})")
    logger.info(f"Daily message check - Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC (Hour: {now.hour}, Minute: {now.minute})")
    
    # EST is UTC-4, so 12:15-12:45 AM EST = 4:15-4:45 AM UTC  
    # 30-minute window centered around 12:30 AM EST - ONLY ADVANCE DAY (no message sent)
    if now.hour == 4 and 15 <= now.minute < 45 and last_daily_message_day != current_day:  # 12:15-12:45 AM EST (4:15-4:45 AM UTC)
        last_daily_message_day = current_day
        
        # Get channel for sending message
        channel = bot.get_channel(announcement_channel)
        
        # Only send daily message and advance day if there are tracked users
        if tracked_users:
            if channel:
                print("Sending daily art message - 12:30 AM EST...")
                logger.info("Sending daily art message - 12:30 AM EST...")
                await channel.send(message)
            else:
                logger.error(f"Could not send daily message - announcement channel {announcement_channel} not found")

            print(f"Day {current_day} has ended!")
            logger.info(f"Day {current_day} has ended!")
            current_day += 1
            
            # Auto-commit backup.json after day advancement
            await auto_commit_backup()
            
        else:
            print("No tracked users - pausing season progression")
            logger.info("No tracked users - season paused until users are added")
        if current_day == season_days + 1:
            badge_pathway = f"badges/UWVAC_Badges_Season{season}.png"
            if os.path.exists(badge_pathway):
                badge = discord.File(badge_pathway)
            results_message = f"# 🎉 **Season {season} has ended!** 🎉\n"
            results_message += f"🏆 **Congratulations to the all inmates!** 🏆\n"
            
            tracked_users_list = list(tracked_users.values())
            tracked_users_list.sort(key=lambda x: (-x['parole_days'], x['missing_days'], -x['revival']))
            
            rank = 1
            prev_user = None
            grouped_users = [] 

            for index, user in enumerate(tracked_users_list):
                # Check if this user has the same stats as the previous user
                if prev_user and (
                    prev_user['parole_days'] == user['parole_days'] and
                    prev_user['missing_days'] == user['missing_days'] and
                    prev_user['revival'] == user['revival']
                ):
                    grouped_users.append(user['user_nickname']) 
                else:
                    if grouped_users:
                        print(f"**{rank}.** {', '.join(grouped_users)} | 🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n")
                        logger.info(f"Rank {rank}: {', '.join(grouped_users)} | Parole: {prev_user['parole_days']} | Missing: {prev_user['missing_days']} | Revival: {prev_user['revival']}")
                        results_message += f"**{rank}.** {', '.join(grouped_users)} | 🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n"

                    rank = index + 1 
                    grouped_users = [user['user_nickname']]
                prev_user = user 
                print(grouped_users)
                logger.debug(f"Grouped users: {grouped_users}")
            if grouped_users:
                results_message += f"**{rank}.** {', '.join(grouped_users)} | 🏆 Parole: {prev_user['parole_days']} | ⏳ Missing: {prev_user['missing_days']} | 😇 Revival: {prev_user['revival']}\n"

            results_message += f"\n## **Funny Achievements:**\n"
            
            # Check if we have any users to avoid crashes
            if not tracked_users:
                results_message += "No tracked users for achievements.\n"
            else:
                max_revival = max(user['revival'] for user in tracked_users.values())
                highest_revival_users = [user['user_nickname'] for user in tracked_users.values() if user['revival'] == max_revival]
                max_buffer = max(user['buffer'] for user in tracked_users.values())
                highest_buffer_users = [user['user_nickname'] for user in tracked_users.values() if user['buffer'] == max_buffer]
                
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
                results_message += f"\n## **⚔️ Duel Champions:**\n"
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
            results_message += f"🎨 **The {season_theme} badge** 🎨\n"
            
            # Get channel for season end messages
            channel = bot.get_channel(announcement_channel)
            if channel:
                await channel.send(results_message, file=badge)
            else:
                logger.error(f"Could not send season end results - announcement channel {announcement_channel} not found")

            # Reset all user stats for the new season
            reset_user_stats()
            
            # Clear any active duels for the new season
            try:
                from duel import clear_all_duels
                clear_all_duels()
                logger.info("Cleared all active duels for new season")
            except Exception as e:
                logger.warning(f"Could not clear duels for new season: {e}")

            current_day = 1
            season += 1
            season_theme = f"{season_theme}"
            season_message = f"# 🎉 **Season {season} begins tomorrow!** 🎉\n"
            season_message += f"📊 **All user stats have been reset!** Fresh start for everyone! 🔄\n"
            
            if channel:
                await channel.send(season_message)
            else:
                logger.error(f"Could not send new season message - announcement channel {announcement_channel} not found")

        for user in tracked_users.values():
            # Initialize consecutive_missed_days if it doesn't exist (for existing users)
            if 'consecutive_missed_days' not in user:
                user['consecutive_missed_days'] = 0
            
            # Process daily submission status first
            if not user['sent_image']:
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
                    
            # Reset daily submission flag for next day
            user['sent_image'] = False
        


@tasks.loop(hours=time_deploy)  # Save data every 8 hours
async def save_data_task():
    data = {
        "current_day": current_day,
        "season": season,
        "tracked_users": tracked_users,
        "announcement_channel": announcement_channel,
        "allowed_channels": allowed_channels,
        "duel": get_duel_data(),
        "chain": get_chain_data()
    }
    
    with open(saved_data, "w") as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Data saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


@tasks.loop(minutes=30)  # Check every 30 minutes to catch both warning times
async def ping_jailed_users():
    global last_warning_1_day, last_warning_2_day
    
    now = datetime.now()
    # Add detailed time logging for debugging
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC (Hour: {now.hour})")
    logger.info(f"ping_jailed_users check - Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC (Hour: {now.hour})")
    
    message = ""
    
    # EST is UTC-5 in standard time (winter), UTC-4 in daylight time (summer)
    # For now, using UTC-4 (EDT) - 10:00-10:30 PM EST = 2:00-2:30 AM UTC, 11:00-11:30 PM EST = 3:00-3:30 AM UTC
    
    # Send daily art message WITH warnings at 10-10:30 PM EST and 11-11:30 PM EST
    if now.hour == 2 and now.minute < 30 and last_warning_1_day != current_day:  # 10:00-10:30 PM EST (2:00-2:30 AM UTC)
        print("Sending daily art message + first warning - 10:00-10:30 PM EST...")
        logger.info("Sending daily art message + first warning - 10:00-10:30 PM EST...")
        last_warning_1_day = current_day
        
        # Build the daily art message inline
        users_not_sent = [u for u in tracked_users.values() if not u['sent_image']]
        users_sent = [u for u in tracked_users.values() if u['sent_image']]
        
        message = f"## **Season {season} - {season_theme}: Day {current_day} - Daily Art Challenge** 🎨\n"
        message += f"**🔄 On parole:** \n{', '.join([u['user_nickname'] for u in users_sent])}\n"
        message += "\n**⛓️ Jailed:**\n"
        message += "🧱"*20 + "\n"
        
        # Filter jailed and deceased users
        jailed_users = [user for user in users_not_sent if not user['deceased']]
        deceased_users = [user for user in users_not_sent if user['deceased']]
        
        for i, user in enumerate(jailed_users):
            message += f"|| {user['user_nickname']} 💨{user['missing_days']}"
            if user['buffer'] > 0:
                message += f" (🛑{user['buffer']})"
            message += " || "
        
        message += "\n" + "🧱"*20 + "\n"
        message += "\n**🪦 Deceased:**\n"
        message += "☁️"*20 + "\n"
        
        for i, user in enumerate(deceased_users):
            message += f"|| {user['user_nickname']}(💨{user['missing_days']} 💀{user['deceased_days']} 😇{user['revival']})"
            if user['buffer'] > 0:
                message += f" 🛑{user['buffer']}"
            message += " || "
        
        message += "\n" + "☁️"*20
        
        # Add warning message
        message += "\n\n🚨 **Daily Art Reminder!** 🚨\n"
        message += "**You have roughly 2 hours before the daily reset!** ⏰\n\n"
        
        # Find users who need to submit
        ping_users = []
        for user_id, user in tracked_users.items():
            if user['ping'] and not user['sent_image']:
                member = bot.get_user(user_id)
                if member:
                    ping_users.append(member.mention)
        
        if ping_users:
            message += f"Haven't submitted today: {' '.join(ping_users)}\n"
            message += "**Don't forget to submit your daily art! 🎨**"
        else:
            message += "**Great job everyone! All tracked users have submitted their art today! 🎉**"
        
    elif now.hour == 3 and now.minute < 30 and last_warning_2_day != current_day:  # 11:00-11:30 PM EST (3:00-3:30 AM UTC)
        print("Sending daily art message + final warning - 11:00-11:30 PM EST...")
        logger.info("Sending daily art message + final warning - 11:00-11:30 PM EST...")
        last_warning_2_day = current_day
        
        # Build the daily art message inline
        users_not_sent = [u for u in tracked_users.values() if not u['sent_image']]
        users_sent = [u for u in tracked_users.values() if u['sent_image']]
        
        message = f"## **Season {season} - {season_theme}: Day {current_day} - Daily Art Challenge** 🎨\n"
        message += f"**🔄 On parole:** \n{', '.join([u['user_nickname'] for u in users_sent])}\n"
        message += "\n**⛓️ Jailed:**\n"
        message += "🧱"*20 + "\n"
        
        # Filter jailed and deceased users
        jailed_users = [user for user in users_not_sent if not user['deceased']]
        deceased_users = [user for user in users_not_sent if user['deceased']]
        
        for i, user in enumerate(jailed_users):
            message += f"|| {user['user_nickname']} 💨{user['missing_days']}"
            if user['buffer'] > 0:
                message += f" (🛑{user['buffer']})"
            message += " || "
        
        message += "\n" + "🧱"*20 + "\n"
        message += "\n**🪦 Deceased:**\n"
        message += "☁️"*20 + "\n"
        
        for i, user in enumerate(deceased_users):
            message += f"|| {user['user_nickname']}(💨{user['missing_days']} 💀{user['deceased_days']} 😇{user['revival']})"
            if user['buffer'] > 0:
                message += f" 🛑{user['buffer']}"
            message += " || "
        
        message += "\n" + "☁️"*20
        
        # Add final warning message
        message += "\n\n⚠️ **FINAL HOUR WARNING!** ⚠️\n"
        message += "**You have approximately 1 hour before the daily reset!** ⏰💀\n\n"
        
        # Find users who need to submit
        ping_users = []
        for user_id, user in tracked_users.items():
            if user['ping'] and not user['sent_image']:
                member = bot.get_user(user_id)
                if member:
                    ping_users.append(member.mention)
        
        if ping_users:
            message += f"Still need to submit: {' '.join(ping_users)}\n"
            message += "**Last chance to avoid the graveyard! Submit your art NOW! 🏃‍♂️💨**"
        else:
            message += "**Excellent! All tracked users are safe for today! 🎨✅**"
    
    if message:  # Only send if we have a message (10:30 PM or 11:30 PM EST)
        channel = bot.get_channel(announcement_channel)
        if channel:
            await channel.send(message)
        else:
            logger.error(f"Could not send warning message - announcement channel {announcement_channel} not found")