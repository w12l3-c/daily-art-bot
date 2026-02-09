"""
wcw.py
This file contains functions related to the WCW tracking aspect of the bot
"""

import discord
from discord.ext import tasks
import json
from shared import bot, logger
import shared
import re

def has_perms(user) -> bool:
    return user.id in shared.WCW_WARDENS or shared.has_admin_or_mod_permissions(user)

def is_active_member(user) -> bool:
    return user.id in shared.wcw_tracked_users and shared.wcw_tracked_users[user.id]['active']

async def edit_user(
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

    if user.id not in shared.wcw_tracked_users:
        return

    user_data = shared.wcw_tracked_users[user.id]

    if status is not None:
        user_data['status'] = status

    if submission is not None:
        user_data['submission'] = submission

    if submission_words is not None:
        user_data['submission_words'] = submission_words

    if submissions is not None:
        user_data['submissions'] = submissions

    if active is not None:
        user_data['active'] = active

    if total_word_count is not None:
        user_data['total_word_count'] = total_word_count

    if goal is not None:
        user_data['goal'] = goal

    if weekly_streak is not None:
        user_data['weekly_streak'] = weekly_streak

    if weeks_submitted is not None:
        user_data['weeks_submitted'] = weeks_submitted

    if weeks_missed is not None:
        user_data['weeks_missed'] = weeks_missed

    if weeks_excused is not None:
        user_data['weeks_excused'] = weeks_excused

    if ping is not None:
        user_data['ping'] = ping
    
    await save_data()


def view_user(user: discord.User) -> str:
    if not is_active_member(user):
        return ""
    
    data = shared.wcw_tracked_users[user.id]

    lines = [
        f"Username: {data['username']}",
        f"Nickname: {data['user_nickname']}",
        f"Status: {data['status']}",
        f"Submission: {shared.get_submission_link(user.id, wcw=True)}",
        f"Submissions: {data['submissions']}",
        f"Active: {data['active']}",
        f"Total word count: {data['total_word_count']}",
        f"Words (submission): {data['submission_words']}",
        f"Goal: {data['goal'] or '(none)'}",
        f"Weekly streak: {data['weekly_streak']}",
        f"Weeks submitted: {data['weeks_submitted']}",
        f"Weeks missed: {data['weeks_missed']}",
        f"Weeks excused: {data['weeks_excused']}",
        f"Ping: {data['ping']}",
    ]

    return "\n".join(lines)


async def excuse_user(user: discord.User) -> bool:
    if not is_active_member(user):
        return False
    
    if shared.wcw_tracked_users[user.id]['status'] == "submitted":
        return False
    
    await edit_user(user, status = "excused")
    return True


async def add_user(user: discord.User):
    user_nickname = user.display_name if user and user.display_name else user.name
    if user.id in shared.wcw_tracked_users:
        shared.wcw_tracked_users[user.id]['active'] = True
    else:
        shared.wcw_tracked_users[user.id] = {
            'username': user.name,
            'user_nickname': user_nickname,
            'status': "pending",
            'submission': "",
            'submissions': 0,
            'active': True,
            'total_word_count': 0,
            'submission_words': 0,
            'goal': "", 
            'weekly_streak': 0,
            'weeks_submitted': 0,
            'weeks_missed': 0,
            'weeks_excused': 0,
            'ping': False,
        }

    await save_data()



async def remove_user(user: discord.User):
    if is_active_member(user):
        await edit_user(user, active=False, submission="", status="pending", submission_words=0, ping=False)



# @tasks.loop(minutes=1)  # Save data every 8 hours
async def save_data():
    data = {
        "current_week": shared.wcw_current_week,
        "announcement_channel": shared.wcw_announcement_channel,
        "allowed_channels": shared.wcw_allowed_channels,
        "last_message_week": shared.wcw_last_message_week,
        "last_reminder_1_week": shared.wcw_last_reminder_1_week,
        "last_reminder_2_week": shared.wcw_last_reminder_2_week,
        "tracked_users": shared.wcw_tracked_users,
    }
    
    with open(shared.WCW_SAVED_DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ WCW data saved at {shared.now_et().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"WCW data saved at {shared.now_et().strftime('%Y-%m-%d %H:%M:%S')}")



async def on_message_wcw(message: discord.Message):
    if "#wcw" not in message.content.lower():
        return
    
    if message.author.id not in shared.wcw_tracked_users or not shared.wcw_tracked_users[message.author.id]['active']:
        await message.channel.send(f"You are not tracked in WCW! Add yourself with /wcw_join")
        return
    
    user_data = shared.wcw_tracked_users[message.author.id]

    match = re.search(r'#wcw: ?(\d+)', message.content.lower())
    if not match:
        await message.channel.send(f"Please submit using the format \"#wcw:<word count>\"! For example, \"#wcw:500\"")
        return

    word_count = int(match.group(1))
    submission = f"{message.channel.id}/"
    
    # check if it's a reply
    if message.reference is not None and isinstance(message.reference.resolved, discord.Message) and (message.reference.resolved.author.id == message.author.id or has_perms(message.author)):
        submission += str(message.reference.resolved.id)
    else:
        submission += str(message.id)

    previous_submission = user_data['submission']
    await edit_user(message.author, submission=submission, submission_words=word_count, status="submitted")

    if previous_submission:
        await message.channel.send(f"{user_data['user_nickname']}, your WCW submission for this week has been counted! (Your previous submission was overridden)")
    else:
        await message.channel.send(f"{user_data['user_nickname']}, your WCW submission for this week has been counted!")



def build_announcement_message(id: str):
    message = f"# Word Count Wednesdays - Week {shared.wcw_current_week}\n"
    if id == "reminder_1": # sent at 9 am wednesday
        message += "Good morning, writers! Your WCW submissions are due in 15 hours. Happy writing!"
    elif id == "reminder_2": # sent at 9 pm wednesday
        message += "Your WCW submissions are due in 3 hours. Best submit if you haven't already!"
    elif id == "weekly": # sent at 12 am wednesday/thursday
        message += "The week has concluded!"
    else:
        return ""


    pending_emoji = "◻️"
    missed_emoji = "❌"
    submitted_emoji = "✅"
    excused_emoji = "💬"

    message += "\n\n"

    message += f"{submitted_emoji} **Submitted** {submitted_emoji}\n"
    submitted = [
        shared.format_username(u["user_nickname"])
        for u in shared.wcw_tracked_users.values()
        if u['active'] and u['status'] == "submitted"
    ]
    message += "  •  ".join(submitted) if submitted else "(none)"
    message += "\n\n"

    if id == "weekly":
        message += f"{missed_emoji} **Not submitted** {missed_emoji}\n"
    else:
        message += f"{pending_emoji} **Pending** {pending_emoji}\n"
       
    pending = [
        shared.format_username(u["user_nickname"])
        for u in shared.wcw_tracked_users.values()
        if u['active'] and u['status'] == "pending"
    ]
    message += "  •  ".join(pending) if pending else "(none)"

    message += "\n\n"

    message += f"{excused_emoji} **Excused** {excused_emoji}\n"
    excused = [
        shared.format_username(u["user_nickname"])
        for u in shared.wcw_tracked_users.values()
        if u['active'] and u['status'] == "excused"
    ]
    message += "  •  ".join(excused) if excused else "(none)"
    message += "\n\n"

    to_ping = [
        f"<@{user_id}>"
        for user_id, user_data in shared.wcw_tracked_users.items()
        if user_data['active'] and user_data["ping"] and user_data['status'] == "pending"
    ]

    if id != "weekly" and to_ping:
        message += f"Make sure to submit! {' '.join(to_ping)}\n\n"

    if id == "weekly":
        message += "Keep it up, writers!"

    return message


@tasks.loop(minutes=1)
async def send_announcement_message(debug: int = 0):
    now = shared.now_et()

    if debug == 1 or now.weekday() == 2 and now.hour == 9 and now.minute <= 1 and shared.wcw_last_reminder_1_week != shared.wcw_current_week:
        shared.wcw_last_reminder_1_week = shared.wcw_current_week
        message = build_announcement_message("reminder_1")

        channel = bot.get_channel(shared.wcw_announcement_channel)
        if not channel:
            logger.error(f"Could not send WCW reminder 1 - announcement channel {shared.wcw_announcement_channel} not found")
        else:
            await channel.send(message)

        await save_data()

    elif debug == 2 or now.weekday() == 2 and now.hour == 21 and now.minute <= 1 and shared.wcw_last_reminder_2_week != shared.wcw_current_week:
        shared.wcw_last_reminder_2_week = shared.wcw_current_week

        message = build_announcement_message("reminder_2")

        channel = bot.get_channel(shared.wcw_announcement_channel)
        if not channel:
            logger.error(f"Could not send WCW reminder 2 - announcement channel {shared.wcw_announcement_channel} not found")
        else:
            await channel.send(message)

        await save_data()

    elif debug == 3 or now.weekday() == 3 and now.hour == 0 and now.minute <= 1 and shared.wcw_last_message_week != shared.wcw_current_week:
        shared.wcw_last_message_week = shared.wcw_current_week
        message = build_announcement_message("weekly")

        channel = bot.get_channel(shared.wcw_announcement_channel)
        if not channel:
            logger.error(f"Could not send WCW week end - announcement channel {shared.wcw_announcement_channel} not found")
        else:
            await channel.send(message)

        # end week logic
        for user in shared.wcw_tracked_users.values():
            if not user['active']:
                continue

            if user['status'] == "submitted":
                user['submissions'] += 1
                user['weekly_streak'] += 1
                user['weeks_submitted'] += 1
                user['total_word_count'] += user['submission_words']
            
            elif user['status'] == "excused":
                user['weeks_excused'] += 1

            else:
                user['weekly_streak'] = 0
                user['weeks_missed'] += 1

            user['submission_words'] = 0
            user['status'] = "pending"
            user['submission'] = ""

        shared.wcw_current_week += 1

        await save_data()
