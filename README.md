# Daily Art Jail - UWVAC
Discord Bot for tracking dailies

### Dev
Python Version > 3.9 
Use Conda/Mamba or Download Python from the official website

Setup:
```bash
pip install -r requirements.txt
```

Environment Setup:
1. Copy `.env.example` to `.env`
2. Add your Discord bot token to the `.env` file
3. Run with `python bot.py` or use Docker

Docker Setup:
```bash
make build    # Build the Docker image
make run      # Run the container
make deploy   # Deploy to production
```

Beginning Example:
[Tutorial](https://discordpy.readthedocs.io/en/stable/)

### Progress
**Wal:**
- [x] Basic system for tracking dailies
- [x] User registration
- [x] Primative Internal Debugging Tools
- [x] Commands for manipulating daily counter (resetting, etc) 
- [x] Storing of preferences for who wants to be pinged
- [x] The graveyard system for when people fail dailies
- [x] Bot monitor across multiple channels
- [x] Visual commandsd such as showing lists 
- [x] the visual system of jailing, alphabetisizing dailies (daily spoiler jail system)
- [x] The revival system for when people wish to join dailies again
- [x] Function to account for people who are busy and cannot do dailies
- [x] Potential functionality for doing multiple dailies for a buffer 
- [x] Marker for determining daily, buffer and regular image
- [x] Autofill commands
- [x] Slash commands 
- [x] Function to backup data and load when bot is restarted
- [x] Badge/Medal system to account for milestones
- [x] A system to acknowledge a soft reset for every term.
- [x] Dockerfile and Makefile for quick setup
- [x] Duel system with multiple challenge types (volume, streak, time)
- [x] Duel forfeit functionality and season rankings
- [x] Docker containerization for easy deployment


todo:
- [ ] Random Events
- [ ] Deploy in Raspberry Pi
- [ ] Potential functionality to account for flexibility in people doing dailies (writing dailies, cooking dailies, other cases etc)

## Commands:
- `/add_channel #channel`: Adds a channel to the daily system
- `/remove_channel #channel`: Removes a channel from the daily system
- `/list_channels`: Lists all channels in the daily system
- `/add_user @user`: Adds a user to the daily system 
- `/remove_user @user`: Removes a user from the daily system
- `/list_users`: Lists all users in the daily system
- `/query_user @user`: Queries a user's info
- `/edit_user @user attribute value`: Edits a user's attribute
- `/duel_challenge @user type`: Challenge another user to a duel (volume/streak/time)
- `/duel_accept`: Accept a pending duel challenge
- `/duel_deny`: Deny a pending duel challenge
- `/duel_forfeit`: Forfeit your current active duel
- `/duel_leaderboard`: View current season duel rankings
- `/duel_status`: Check your current duel status

### User Attributes:
- `sent_image`: User status of sending image
- `parole_days`: Days until user is released from jail
- `deceased`: User status of being deceased 
- `deceased_days`: Days since user has been deceased 
- `missing_days`: Days since user missed a daily
- `revival`: Amount of revivals user have used
- `buffer`: Amount of buffer art user has
- `probation`: Whether user are busy and cannot do dailies
- `ping`: Whether user wants to be pinged

## Duel System:
The bot features a comprehensive duel system where users can challenge each other in three different types of contests:

**Duel Types:**
- **Volume**: Most art pieces submitted during the duel period
- **Streak**: Longest consecutive daily streak during the duel period  
- **Time**: First to complete a daily after the duel starts

**Duel Flow:**
1. Challenge another user with `/duel_challenge @user type`
2. The challenged user can `/duel_accept` or `/duel_deny`
3. Once accepted, the duel begins and progress is tracked automatically
4. Duels complete when conditions are met or time expires
5. Winners are announced in the channel with updated rankings

**Features:**
- Season-end rankings with most active dueler and best win rate
- Forfeit functionality if you need to exit a duel early
- Automatic cleanup of expired duels
- Debug mode available for testing (120-second duels)