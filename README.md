# Daily Art Jail - UWVAC
Discord Bot for tracking dailies

### Dev
Python Version > 3.9 

Setup:
``` pip install discord.py ```
Beginning Example:
[Tutorial](https://discordpy.readthedocs.io/en/stable/)

### Assigned
**Wal:**
- [x] Basic system for tracking dailies
- [x] User registration
- [ ] Primative Internal Debugging Tools
- [x] Commands for manipulating daily counter (resetting, etc) 
- [x] Storing of preferences for who wants to be pinged
- [x] The graveyard system for when people fail dailies

**Moon:**
- [ ] Visual commandsd such as showing lists 

**Grace:**
- [ ] Currently bot must be run on terminal, be able to host bot (planning on using a csc cloud account)
- [ ] autofill commands
- [ ] / slash commands

**Deceased:**
- [ ] the visual system of jailing, alphabetisizing dailies (daily spoiler jail system)

**Jakob:**
- [ ] The revival system for when people wish to join dailies again

**Celery:**


### Not assigned
- [ ] Bot monitor across multiple channels
- [ ] Potential functionality for doing multiple dailies for a buffer
- [ ] Potential functionality to account for flexibility in people doing dailies (writing dailies, cooking dailies, other cases etc)
- [ ] Badge/Medal system to account for milestones
- [ ] A system to acknowledge a soft reset for every term.


### Commands Currently:
- `!add_user @user`: Adds a user to the daily system 
  - `ping=True`: Adds the user to the ping list
- `!remove_user @user`: Removes a user from the daily system
- `!list_users`: Lists all users in the daily system
- `!query_user @user`: Queries a user's info
- `!change_ping_status @user`: Flips a user's ping status (This could definitely be improved)