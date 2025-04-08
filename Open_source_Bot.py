import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True  # Important for role checks

class XPBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)
        self.language = "english"  # Default language
        self.user_cooldowns = {}  # Dictionary to store user cooldowns

    async def on_ready(self):
        await self.tree.sync()  # Synchronizes all global slash commands
        print(f"Bot {self.user} is online!")
        print("Slash commands synchronized!")

bot = XPBot()

XP_FILE = "xp_data.json"
CHANNELS_FILE = "channels.json"
LANGUAGE_FILE = "language.json"

# Role IDs for level rewards (replace with actual role IDs from your server)
LEVEL_ROLES = {
    10: 1234,  # Replace with the actual role ID for "Starter"
    20: 1234,  # Replace with the actual role ID for "Regulars"
    50: 1234,  # Replace with the actual role ID for "Damn50?"
    100: 1234  # Replace with the actual role IF for "NO LIFE"
}

def load_xp():
    if os.path.exists(XP_FILE):
        try:
            with open(XP_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_xp(data):
    try:
        with open(XP_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving XP data: {e}")

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_channels(channels):
    try:
        with open(CHANNELS_FILE, "w") as f:
            json.dump(channels, f, indent=4)
    except IOError as e:
        print(f"Error saving channels: {e}")

def load_language():
    if os.path.exists(LANGUAGE_FILE):
        try:
            with open(LANGUAGE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"language": "english"}  # Default to English if file is corrupted
    return {"language": "english"}  # Default to English if file doesn't exist

def save_language(language):
    try:
        with open(LANGUAGE_FILE, "w") as f:
            json.dump({"language": language}, f, indent=4)
    except IOError as e:
        print(f"Error saving language: {e}")

def calculate_xp_needed(level):
    return 100 + (level * 50)

# List of allowed roles
ALLOWED_ROLES = ["Admin", "Mod", "Owner"]

def has_permission(interaction: discord.Interaction):
    # Checks if the user has administrator permissions or one of the allowed roles
    return interaction.user.guild_permissions.administrator or any(role.name in ALLOWED_ROLES for role in interaction.user.roles)

async def assign_level_roles(member: discord.Member, level: int):
    # Get the roles the user should have based on their level
    roles_to_add = []
    for lvl, role_id in LEVEL_ROLES.items():
        if level >= lvl:
            role = member.guild.get_role(role_id)
            if role and role not in member.roles:
                roles_to_add.append(role)
    
    # Add the new roles to the user
    if roles_to_add:
        await member.add_roles(*roles_to_add)
        if bot.language == "english":
            await member.send(f"🎉 You have unlocked the {roles_to_add[-1].name} role!")
        else:
            await member.send(f"🎉 Du hast die {roles_to_add[-1].name} Rolle freigeschaltet!")

@bot.tree.command(name="set_language", description="Set the bot's language (English or German)")
@app_commands.describe(language="The language to set (english/german)")
async def set_language(interaction: discord.Interaction, language: str):
    if not has_permission(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if language.lower() not in ["english", "german"]:
        await interaction.response.send_message("Invalid language. Please choose 'english' or 'german'.", ephemeral=True)
        return

    bot.language = language.lower()
    save_language(bot.language)
    await interaction.response.send_message(f"Language has been set to **{language.capitalize()}**!", ephemeral=True)

@bot.tree.command(name="setup", description="Set the XP channel")
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    if not has_permission(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    channels = load_channels()
    if channel.id not in channels:
        channels.append(channel.id)
        save_channels(channels)
        if bot.language == "english":
            await interaction.response.send_message(f'Channel {channel.mention} has been enabled for XP!', ephemeral=True)
        else:
            await interaction.response.send_message(f'Kanal {channel.mention} wurde für XP aktiviert!', ephemeral=True)
    else:
        if bot.language == "english":
            await interaction.response.send_message(f'Channel {channel.mention} is already enabled.', ephemeral=True)
        else:
            await interaction.response.send_message(f'Kanal {channel.mention} ist bereits aktiviert.', ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Anti-Spam: Check if the user is on cooldown
    user_id = str(message.author.id)
    current_time = datetime.utcnow()
    cooldown_time = timedelta(seconds=5)  # 5-second cooldown

    if user_id in bot.user_cooldowns:
        last_message_time = bot.user_cooldowns[user_id]
        if current_time - last_message_time < cooldown_time:
            return  # Ignore the message if the user is on cooldown
    
    # Update the user's last message time
    bot.user_cooldowns[user_id] = current_time

    data = load_xp()
    
    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 1}
    
    xp_gain = random.randint(5, 20)
    data[user_id]["xp"] += xp_gain
    needed_xp = calculate_xp_needed(data[user_id]["level"])

    if data[user_id]["xp"] >= needed_xp:
        data[user_id]["xp"] -= needed_xp
        data[user_id]["level"] += 1

        # Assign level roles
        await assign_level_roles(message.author, data[user_id]["level"])

        # Send the level-up message only once
        channels = load_channels()
        if channels:
            channel = bot.get_channel(channels[0])  # Use the first channel in the list
            if channel:
                if bot.language == "english":
                    await channel.send(f'{message.author.mention} has reached Level {data[user_id]["level"]}!')
                else:
                    await channel.send(f'{message.author.mention} hat Level {data[user_id]["level"]} erreicht!')
    
    # Save XP data after processing
    save_xp(data)
    
    await bot.process_commands(message)

@bot.tree.command(name="rank", description="Show your current level")
async def rank(interaction: discord.Interaction):
    data = load_xp()
    user_id = str(interaction.user.id)

    if user_id in data:
        xp = data[user_id]["xp"]
        level = data[user_id]["level"]
        needed_xp = calculate_xp_needed(level)

        progress_blocks = 10
        filled_blocks = min(int((xp / needed_xp) * progress_blocks), progress_blocks)
        progress_bar = "█" * filled_blocks + "░" * (progress_blocks - filled_blocks)

        if bot.language == "english":
            response = (
                f"**{interaction.user.mention}, here is your XP status!**\n\n"
                f"Level: `{level}`\n"
                f"XP: `{xp} / {needed_xp}`\n\n"
                f"Progress:\n"
                f"{progress_bar}\n\n"
                f"Only `{needed_xp - xp}` XP left to the next level!"
            )
        else:
            response = (
                f"**{interaction.user.mention}, hier ist dein XP-Status!**\n\n"
                f"Level: `{level}`\n"
                f"XP: `{xp} / {needed_xp}`\n\n"
                f"Fortschritt:\n"
                f"{progress_bar}\n\n"
                f"Noch `{needed_xp - xp}` XP bis zum nächsten Level!"
            )

        await interaction.response.send_message(response, ephemeral=True)
    else:
        if bot.language == "english":
            await interaction.response.send_message(
                f"{interaction.user.mention}, you haven't earned any XP yet. Be active to level up!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"{interaction.user.mention}, du hast noch keine XP gesammelt. Sei aktiv, um Level zu steigen!",
                ephemeral=True
            )

@bot.tree.command(name="give_lv", description="Set a user's level")
@app_commands.describe(member="The user whose level you want to set", level="The new level")
async def give_lv(interaction: discord.Interaction, member: discord.Member, level: int):
    if not has_permission(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    data = load_xp()
    user_id = str(member.id)

    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 1}

    data[user_id]["level"] = level
    data[user_id]["xp"] = 0

    # Assign level roles
    await assign_level_roles(member, level)

    save_xp(data)
    if bot.language == "english":
        await interaction.response.send_message(f'{member.mention} has been set to Level {level}!', ephemeral=True)
    else:
        await interaction.response.send_message(f'{member.mention} wurde auf Level {level} gesetzt!', ephemeral=True)

@bot.tree.command(name="lv_reset", description="Reset a user's level")
async def lv_reset(interaction: discord.Interaction, member: discord.Member):
    if not has_permission(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    data = load_xp()
    data[str(member.id)] = {"xp": 0, "level": 1}
    save_xp(data)

    # Remove all level roles
    roles_to_remove = []
    for role_id in LEVEL_ROLES.values():
        role = member.guild.get_role(role_id)
        if role and role in member.roles:
            roles_to_remove.append(role)
    
    if roles_to_remove:
        await member.remove_roles(*roles_to_remove)

    if bot.language == "english":
        await interaction.response.send_message(f'{member.mention} has been reset to Level 1!', ephemeral=True)
    else:
        await interaction.response.send_message(f'{member.mention} wurde auf Level 1 zurückgesetzt!', ephemeral=True)

@bot.tree.command(name="wipe_all", description="Reset all XP data")
async def wipe_all(interaction: discord.Interaction):
    if not has_permission(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    try:
        with open(XP_FILE, "w") as f:
            json.dump({}, f)
        if bot.language == "english":
            await interaction.response.send_message("All XP data has been reset!", ephemeral=True)
        else:
            await interaction.response.send_message("Alle XP-Daten wurden zurückgesetzt!", ephemeral=True)
    except IOError as e:
        if bot.language == "english":
            await interaction.response.send_message(f"Error resetting XP data: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Fehler beim Zurücksetzen der XP-Daten: {e}", ephemeral=True)

@bot.tree.command(name="leaderboard", description="Show the top 5 users by level")
async def leaderboard(interaction: discord.Interaction):
    data = load_xp()
    if not data:
        if bot.language == "english":
            await interaction.response.send_message("No XP data available yet.", ephemeral=True)
        else:
            await interaction.response.send_message("Es sind noch keine XP-Daten verfügbar.", ephemeral=True)
        return

    # Sort users by level (descending) and XP (descending)
    sorted_users = sorted(data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)
    top_users = sorted_users[:5]  # Get top 5 users

    if bot.language == "english":
        leaderboard_message = "🏆 **Top 5 Leaderboard** 🏆\n\n"
    else:
        leaderboard_message = "🏆 **Top 5 Bestenliste** 🏆\n\n"

    for idx, (user_id, user_data) in enumerate(top_users, start=1):
        user = await bot.fetch_user(user_id)
        level = user_data["level"]
        xp = user_data["xp"]

        if bot.language == "english":
            leaderboard_message += f"{idx}. **{user.name}** is Level {level} with {xp} XP!\n"
        else:
            leaderboard_message += f"{idx}. **{user.name}** ist Level {level} mit {xp} XP!\n"

    await interaction.response.send_message(leaderboard_message, ephemeral=False)

@bot.tree.command(name="help", description="Show all available commands")
async def help(interaction: discord.Interaction):
    if bot.language == "english":
        response = (
            "**Code and Work by: EULE_ON_CRACK**\n"
            "**Bot Version = 1.05 (06.04.2025) Latest**\n\n"
            "**📜 Command Overview:**\n\n"
            "**/setup [Channel]** - Set the channel for the XP system. (Admins/Mods/Owners only)\n"
            "**/rank** - Show your current XP status and level.\n"
            "**/leaderboard** - Show the top 5 users by level.\n"
            "**/give_lv [User] [Level]** - Set a user's level. (Admins/Mods/Owners only)\n"
            "**/lv_reset [User]** - Reset a user's level. (Admins/Mods/Owners only)\n"
            "**/wipe_all** - Reset all XP data. (Admins/Mods/Owners only)\n"
            "**/set_language [Language]** - Set the bot's language (english/german). (Admins/Mods/Owners only)\n"
            "**/help** - Show this help message.\n\n"
            "XP is automatically earned by sending messages."
        )
    else:
        response = (
            "**📜 Befehlsübersicht:**\n\n"
            "**/setup [Kanal]** - Setzt den Kanal für das XP-System. (Nur Admins/Mods/Owner)\n"
            "**/rank** - Zeigt deinen aktuellen XP-Stand und dein Level an.\n"
            "**/leaderboard** - Zeigt die Top 5 Benutzer nach Level an.\n"
            "**/give_lv [Nutzer] [Level]** - Setzt das Level eines Nutzers. (Nur Admins/Mods/Owner)\n"
            "**/lv_reset [Nutzer]** - Setzt das Level eines Nutzers zurück. (Nur Admins/Mods/Owner)\n"
            "**/wipe_all** - Setzt alle XP-Daten zurück. (Nur Admins/Mods/Owner)\n"
            "**/set_language [Sprache]** - Setzt die Sprache des Bots (english/german). (Nur Admins/Mods/Owner)\n"
            "**/help** - Zeigt diese Hilfe an.\n\n"
            "XP wird automatisch durch das Senden von Nachrichten vergeben."
        )

    await interaction.response.send_message(response, ephemeral=True)

TOKEN = "Deine Token"  # Replace with your bot token

bot.run(TOKEN)
