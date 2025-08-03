# Daily Art Jail - UWVAC
Discord Bot for tracking dailies

### Dev
Python Version > 3.9 
Use Conda/Mamba or Download Python from the official website

Setup:
``` pip install discord.py ```

Beginning Example:
[Tutorial](https://discordpy.readthedocs.io/en/stable/)

### Assigned
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

todo:
- [ ] Random Events
- [ ] Currently bot must be run on terminal, be able to host bot (AWS E2)

**Moon:**

**Grace:**

**Deceased:**

**Jakob:**

**Celery:**

### Not assigned
- [ ] Potential functionality to account for flexibility in people doing dailies (writing dailies, cooking dailies, other cases etc)

### Commands Currently:
- `/add_channel #channel`: Adds a channel to the daily system
- `/remove_channel #channel`: Removes a channel from the daily system
- `/list_channels`: Lists all channels in the daily system
- `/add_user @user`: Adds a user to the daily system 
- `/remove_user @user`: Removes a user from the daily system
- `/list_users`: Lists all users in the daily system
- `/query_user @user`: Queries a user's info
- `/edit_user @user attribute value`: Edits a user's attribute

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