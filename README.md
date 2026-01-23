# Daily Art Jail - UWVAC
Discord Bot for tracking dailies 
Project by w12l3-c and w1dering, badges created by codinghustlemoon

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
- [x] Badge upload system for admins/mods
- [x] Art chain collaboration system with GIF generation


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
- `/chain_start name amount`: Start a new art chain collaboration
- `/chain_on name`: Join an existing art chain
- `/chain_list`: List all active art chains
- `/chain_cancel name`: Cancel an art chain (creator/admin only)
- `/list_badges`: View all available badges
- `/badge_help`: Information about badge uploads

### User Attributes:
- `submission`: User status of sending image
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

## Badge Upload System:
Admins and users with the mod role can upload custom badges for seasons:

**Features:**
- Upload PNG badges with `#badge` tag
- Automatic backup of existing badges
- Badge management commands
- Secure permission checks

**Usage:**
1. Upload a PNG file with the message `#badge`
2. File will be saved to the `/badges` directory
3. Use naming convention: `UWVAC_Badges_Season{number}.png`

## Art Chain System:
Collaborative art feature where multiple users contribute to create an animated GIF:

**How it works:**
1. Someone starts a chain with `/chain_start name amount`
2. Other users join with `/chain_on name` and upload art with `#chain` tag
3. When the target number of submissions is reached, all images are compiled into a GIF
4. The final GIF is automatically posted to the channel

**Features:**
- Automatic GIF generation from all submissions
- Progress tracking and participant lists
- Chain management (cancel, list active chains)
- Prevents duplicate submissions from same user
- Automatic cleanup and file management