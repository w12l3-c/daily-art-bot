"""
chain.py
This file contains functions related to the chain-art aspect of the bot
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import logging
import aiohttp
import io
from PIL import Image
import os

logger = logging.getLogger(__name__)

# Global chain storage
active_chains = {}
chain_submissions = {}

class ChainStatus:
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

def get_tracked_users():
    """Import tracked_users from bot.py - this will be set by the main bot"""
    return getattr(get_tracked_users, 'tracked_users', {})

def set_tracked_users_reference(tracked_users_ref):
    """Set reference to tracked_users from main bot"""
    get_tracked_users.tracked_users = tracked_users_ref

async def chain_start_command(interaction: discord.Interaction, name: str, amount: int):
    """Start a new art chain"""
    user_id = interaction.user.id
    tracked_users = get_tracked_users()
    
    # Check if user is tracked
    if user_id not in tracked_users:
        await interaction.response.send_message("❌ You are not in the art tracking system.", ephemeral=True)
        return
    
    # Validate amount
    if amount < 2 or amount > 50:
        await interaction.response.send_message("❌ Chain amount must be between 2 and 50 submissions.", ephemeral=True)
        return
    
    # Check if chain name already exists
    if name.lower() in [chain['name'].lower() for chain in active_chains.values()]:
        await interaction.response.send_message(f"❌ A chain with the name '{name}' already exists.", ephemeral=True)
        return
    
    # Generate unique chain ID
    chain_id = f"{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"
    
    # Create chain data
    chain_data = {
        'id': chain_id,
        'name': name,
        'creator': user_id,
        'creator_name': tracked_users[user_id]['user_nickname'],
        'target_amount': amount,
        'current_count': 0,
        'status': ChainStatus.ACTIVE,
        'created_at': datetime.now(),
        'participants': [],
        'submissions': []
    }
    
    # Store the chain
    active_chains[chain_id] = chain_data
    chain_submissions[chain_id] = []
    
    # Create announcement message
    chain_message = (
        f"🔗 **NEW ART CHAIN STARTED** 🔗\n\n"
        f"**Chain Name:** {name}\n"
        f"**Creator:** {chain_data['creator_name']}\n"
        f"**Target:** {amount} submissions\n"
        f"**Progress:** 0/{amount}\n\n"
        f"Use `/chain_on {name}` with your art to join the chain!\n"
        f"When we reach {amount} submissions, all images will be compiled into a GIF! 🎬"
    )
    
    await interaction.response.send_message(chain_message)
    logger.info(f"Chain started: '{name}' by {chain_data['creator_name']} (target: {amount})")

async def chain_on_command(interaction: discord.Interaction, name: str):
    """Join an existing art chain"""
    user_id = interaction.user.id
    tracked_users = get_tracked_users()
    
    # Check if user is tracked
    if user_id not in tracked_users:
        await interaction.response.send_message("❌ You are not in the art tracking system.", ephemeral=True)
        return
    
    # Find the chain
    chain_data = None
    chain_id = None
    
    for c_id, chain in active_chains.items():
        if chain['name'].lower() == name.lower():
            chain_data = chain
            chain_id = c_id
            break
    
    if not chain_data:
        await interaction.response.send_message(f"❌ No active chain found with the name '{name}'.", ephemeral=True)
        return
    
    if chain_data['status'] != ChainStatus.ACTIVE:
        await interaction.response.send_message(f"❌ The chain '{name}' is no longer active.", ephemeral=True)
        return
    
    # Check if chain is already complete
    if chain_data['current_count'] >= chain_data['target_amount']:
        await interaction.response.send_message(f"❌ The chain '{name}' has already reached its target!", ephemeral=True)
        return
    
    # Store user's intent to submit to this chain
    # They need to upload an image with #chain tag next
    if not hasattr(chain_on_command, 'pending_submissions'):
        chain_on_command.pending_submissions = {}
    
    chain_on_command.pending_submissions[user_id] = {
        'chain_id': chain_id,
        'chain_name': name,
        'timestamp': datetime.now()
    }
    
    await interaction.response.send_message(
        f"🔗 Ready to join the '{name}' chain! "
        f"Now upload your image with the tag `#chain` to add it to the chain.\n"
        f"**Current progress:** {chain_data['current_count']}/{chain_data['target_amount']}"
    )

async def process_chain_submission(user_id: int, message, attachment):
    """Process a chain submission when user uploads image with #chain tag"""
    tracked_users = get_tracked_users()
    
    # Check if user has a pending chain submission
    if not hasattr(chain_on_command, 'pending_submissions'):
        return False
    
    if user_id not in chain_on_command.pending_submissions:
        await message.channel.send(f"❌ {message.author.name}, you need to use `/chain_on <name>` first before submitting to a chain.")
        return False
    
    pending = chain_on_command.pending_submissions[user_id]
    chain_id = pending['chain_id']
    
    # Check if pending submission is still valid (within 10 minutes)
    if (datetime.now() - pending['timestamp']).total_seconds() > 600:
        del chain_on_command.pending_submissions[user_id]
        await message.channel.send(f"❌ {message.author.name}, your chain submission intent expired. Use `/chain_on <name>` again.")
        return False
    
    # Get chain data
    if chain_id not in active_chains:
        del chain_on_command.pending_submissions[user_id]
        await message.channel.send(f"❌ {message.author.name}, the chain no longer exists.")
        return False
    
    chain_data = active_chains[chain_id]
    
    # Check if chain is still active
    if chain_data['status'] != ChainStatus.ACTIVE:
        del chain_on_command.pending_submissions[user_id]
        await message.channel.send(f"❌ {message.author.name}, the chain '{chain_data['name']}' is no longer active.")
        return False
    
    # Check if chain is already complete
    if chain_data['current_count'] >= chain_data['target_amount']:
        del chain_on_command.pending_submissions[user_id]
        await message.channel.send(f"❌ {message.author.name}, the chain '{chain_data['name']}' has already reached its target!")
        return False
    
    # Check if user already participated
    if user_id in chain_data['participants']:
        del chain_on_command.pending_submissions[user_id]
        await message.channel.send(f"❌ {message.author.name}, you have already contributed to the '{chain_data['name']}' chain!")
        return False
    
    # Download and store the image
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    
                    # Add submission to chain
                    submission_data = {
                        'user_id': user_id,
                        'user_name': tracked_users[user_id]['user_nickname'],
                        'message_id': message.id,
                        'image_data': image_data,
                        'filename': attachment.filename,
                        'timestamp': datetime.now()
                    }
                    
                    chain_submissions[chain_id].append(submission_data)
                    chain_data['participants'].append(user_id)
                    chain_data['current_count'] += 1
                    
                    # Remove pending submission
                    del chain_on_command.pending_submissions[user_id]
                    
                    # Check if chain is complete
                    if chain_data['current_count'] >= chain_data['target_amount']:
                        await complete_chain(chain_id, message.channel)
                    else:
                        await message.channel.send(
                            f"🔗 {tracked_users[user_id]['user_nickname']} joined the '{chain_data['name']}' chain! "
                            f"Progress: {chain_data['current_count']}/{chain_data['target_amount']}"
                        )
                    
                    logger.info(f"Chain submission added: {tracked_users[user_id]['user_nickname']} -> '{chain_data['name']}' ({chain_data['current_count']}/{chain_data['target_amount']})")
                    return True
                    
    except Exception as e:
        logger.error(f"Error processing chain submission: {e}")
        await message.channel.send(f"❌ {message.author.name}, there was an error processing your chain submission.")
        return False
    
    return False

async def complete_chain(chain_id: str, channel):
    """Complete a chain and create the GIF"""
    if chain_id not in active_chains or chain_id not in chain_submissions:
        return
    
    chain_data = active_chains[chain_id]
    submissions = chain_submissions[chain_id]
    
    try:
        # Create GIF from submissions
        gif_path = await create_chain_gif(chain_id, chain_data['name'], submissions)
        
        if gif_path:
            # Create completion message
            participants = [sub['user_name'] for sub in submissions]
            completion_message = (
                f"🎬 **CHAIN COMPLETED** 🎬\n\n"
                f"**Chain:** {chain_data['name']}\n"
                f"**Creator:** {chain_data['creator_name']}\n"
                f"**Participants:** {', '.join(participants)}\n"
                f"**Total Submissions:** {len(submissions)}\n\n"
                f"Here's your collaborative art GIF! 🎨✨"
            )
            
            # Send the GIF
            with open(gif_path, 'rb') as gif_file:
                discord_file = discord.File(gif_file, filename=f"{chain_data['name']}_chain.gif")
                await channel.send(completion_message, file=discord_file)
            
            # Clean up the temporary file
            try:
                os.remove(gif_path)
            except:
                pass
            
            logger.info(f"Chain completed: '{chain_data['name']}' with {len(submissions)} submissions")
        else:
            await channel.send(f"🔗 Chain '{chain_data['name']}' completed but there was an error creating the GIF.")
    
    except Exception as e:
        logger.error(f"Error completing chain: {e}")
        await channel.send(f"🔗 Chain '{chain_data['name']}' completed but there was an error creating the GIF.")
    
    # Mark chain as completed
    chain_data['status'] = ChainStatus.COMPLETED
    
    # Clean up after some time (optional - you might want to keep completed chains for records)
    # You can remove this if you want to keep completed chains
    # del active_chains[chain_id]
    # del chain_submissions[chain_id]

async def create_chain_gif(chain_id: str, chain_name: str, submissions):
    """Create a GIF from chain submissions"""
    try:
        # Ensure chains directory exists
        chains_dir = "chains"
        if not os.path.exists(chains_dir):
            os.makedirs(chains_dir)
        
        # Process images
        images = []
        target_size = (512, 512)  # Standard size for all images
        
        for submission in submissions:
            try:
                # Load image from binary data
                image = Image.open(io.BytesIO(submission['image_data']))
                
                # Convert to RGB if necessary
                if image.mode in ['RGBA', 'P']:
                    # Create white background
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Resize to target size (maintain aspect ratio)
                image.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Pad to exact target size if necessary
                if image.size != target_size:
                    padded = Image.new('RGB', target_size, (255, 255, 255))
                    paste_x = (target_size[0] - image.size[0]) // 2
                    paste_y = (target_size[1] - image.size[1]) // 2
                    padded.paste(image, (paste_x, paste_y))
                    image = padded
                
                images.append(image)
                
            except Exception as e:
                logger.error(f"Error processing image in chain: {e}")
                continue
        
        if not images:
            logger.error("No valid images to create GIF")
            return None
        
        # Create GIF
        gif_filename = f"{chain_name.replace(' ', '_')}_{chain_id}.gif"
        gif_path = os.path.join(chains_dir, gif_filename)
        
        # Save as GIF with proper duration
        duration = max(500, min(2000, 1000))  # 0.5 to 2 seconds per frame
        
        images[0].save(
            gif_path,
            save_all=True,
            append_images=images[1:],
            duration=duration,
            loop=0,
            optimize=True
        )
        
        logger.info(f"Created GIF: {gif_path} with {len(images)} frames")
        return gif_path
        
    except Exception as e:
        logger.error(f"Error creating chain GIF: {e}")
        return None

async def chain_list_command(interaction: discord.Interaction):
    """List all active chains"""
    if not active_chains:
        await interaction.response.send_message("🔗 No active chains currently!", ephemeral=True)
        return
    
    active_list = [chain for chain in active_chains.values() if chain['status'] == ChainStatus.ACTIVE]
    
    if not active_list:
        await interaction.response.send_message("🔗 No active chains currently!", ephemeral=True)
        return
    
    list_message = "🔗 **ACTIVE ART CHAINS** 🔗\n\n"
    
    for chain in active_list:
        list_message += f"**{chain['name']}**\n"
        list_message += f"  Creator: {chain['creator_name']}\n"
        list_message += f"  Progress: {chain['current_count']}/{chain['target_amount']}\n"
        list_message += f"  Use `/chain_on {chain['name']}` to join!\n\n"
    
    await interaction.response.send_message(list_message)

async def chain_cancel_command(interaction: discord.Interaction, name: str):
    """Cancel a chain (only creator or admin can do this)"""
    user_id = interaction.user.id
    
    # Find the chain
    chain_data = None
    chain_id = None
    
    for c_id, chain in active_chains.items():
        if chain['name'].lower() == name.lower():
            chain_data = chain
            chain_id = c_id
            break
    
    if not chain_data:
        await interaction.response.send_message(f"❌ No chain found with the name '{name}'.", ephemeral=True)
        return
    
    # Check permissions (creator or admin)
    is_creator = user_id == chain_data['creator']
    is_admin = interaction.user.guild_permissions.administrator
    
    # Check for mod role (reuse the logic from main bot)
    is_mod = False
    if hasattr(interaction.user, 'roles'):
        for role in interaction.user.roles:
            if role.name.lower() == "wally":  # MOD_ROLE_NAME from main bot
                is_mod = True
                break
    
    if not (is_creator or is_admin or is_mod):
        await interaction.response.send_message("❌ Only the chain creator or admins can cancel chains.", ephemeral=True)
        return
    
    # Cancel the chain
    chain_data['status'] = ChainStatus.CANCELLED
    
    # Clean up pending submissions for this chain
    if hasattr(chain_on_command, 'pending_submissions'):
        to_remove = [uid for uid, pending in chain_on_command.pending_submissions.items() 
                    if pending['chain_id'] == chain_id]
        for uid in to_remove:
            del chain_on_command.pending_submissions[uid]
    
    cancel_message = (
        f"🚫 **CHAIN CANCELLED** 🚫\n\n"
        f"**Chain:** {chain_data['name']}\n"
        f"**Cancelled by:** {interaction.user.display_name}\n"
        f"**Progress:** {chain_data['current_count']}/{chain_data['target_amount']}\n\n"
        f"The chain has been cancelled and no longer accepts submissions."
    )
    
    await interaction.response.send_message(cancel_message)
    logger.info(f"Chain cancelled: '{chain_data['name']}' by {interaction.user.display_name}")

# Command registration function
async def register_chain_commands(bot):
    """Register all chain commands with the bot"""
    
    @bot.tree.command(name="chain_start", description="Start a new art chain collaboration!")
    @app_commands.describe(
        name="Name for your art chain",
        amount="Number of submissions needed to complete the chain (2-50)"
    )
    async def chain_start(interaction: discord.Interaction, name: str, amount: int):
        await chain_start_command(interaction, name, amount)
    
    @bot.tree.command(name="chain_on", description="Join an existing art chain!")
    @app_commands.describe(name="Name of the chain you want to join")
    async def chain_on(interaction: discord.Interaction, name: str):
        await chain_on_command(interaction, name)
    
    @bot.tree.command(name="chain_list", description="List all active art chains")
    async def chain_list(interaction: discord.Interaction):
        await chain_list_command(interaction)
    
    @bot.tree.command(name="chain_cancel", description="Cancel an art chain (creator or admin only)")
    @app_commands.describe(name="Name of the chain to cancel")
    async def chain_cancel(interaction: discord.Interaction, name: str):
        await chain_cancel_command(interaction, name)

def get_chain_data():
    """Get chain data for saving to backup"""
    # Convert datetime objects to ISO strings for JSON serialization
    chains_serializable = {}
    submissions_serializable = {}
    
    for chain_id, chain in active_chains.items():
        serializable_chain = chain.copy()
        serializable_chain['created_at'] = chain['created_at'].isoformat()
        chains_serializable[chain_id] = serializable_chain
    
    # Don't serialize image data - it's too large for JSON
    # Instead, we'll rely on regenerating chains from Discord message history if needed
    for chain_id, submissions in chain_submissions.items():
        submissions_serializable[chain_id] = [
            {
                'user_id': sub['user_id'],
                'user_name': sub['user_name'],
                'message_id': sub['message_id'],
                'filename': sub['filename'],
                'timestamp': sub['timestamp'].isoformat()
            }
            for sub in submissions
        ]
    
    return {
        'active_chains': chains_serializable,
        'chain_submissions': submissions_serializable
    }

def load_chain_data(chain_data):
    """Load chain data from backup"""
    global active_chains, chain_submissions
    
    if not chain_data:
        return
    
    # Load active chains
    chains_data = chain_data.get('active_chains', {})
    for chain_id, chain in chains_data.items():
        # Convert ISO strings back to datetime objects
        chain['created_at'] = datetime.fromisoformat(chain['created_at'])
        active_chains[chain_id] = chain
    
    # Load chain submissions (without image data - that would need to be re-downloaded)
    submissions_data = chain_data.get('chain_submissions', {})
    for chain_id, submissions in submissions_data.items():
        chain_submissions[chain_id] = []
        # Note: Image data would need to be re-downloaded from Discord if needed
        # For now, we just skip loading submissions data
    
    logger.info(f"Loaded {len(active_chains)} chains")

def clear_all_chains():
    """Clear all active chains and submissions (used for season reset or manual cleanup)"""
    global active_chains, chain_submissions
    
    chains_count = len(active_chains)
    submissions_count = sum(len(subs) for subs in chain_submissions.values())
    
    active_chains.clear()
    chain_submissions.clear()
    
    logger.info(f"Cleared {chains_count} chains and {submissions_count} submissions")
    return chains_count, submissions_count
