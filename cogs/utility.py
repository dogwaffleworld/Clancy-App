# cogs/utility_cog.py
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from io import BytesIO
from PIL import Image, UnidentifiedImageError
import urllib.parse # For URL encoding location in weather
import typing
import datetime

class UtilityCog(commands.Cog):
    """
    A cog for various utility commands.
    """
    utility_commands_group = app_commands.Group(name="util", description="Utility commands.")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None
        self.sniped_messages: dict[int, discord.Message] = {} # {channel_id: message_object}
        self.afk_users: dict[int, dict[str, typing.Any]] = {} # {user_id: {"message": str, "timestamp": datetime, "original_nick": str|None}}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def cog_unload(self):
        if self._session:
            await self._session.close()

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild: # Ignore bots and DMs for snipe
            return
        self.sniped_messages[message.channel.id] = message

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if message.author.id in self.afk_users:
            afk_data = self.afk_users.pop(message.author.id)
            welcome_back_message = f"Welcome back, {message.author.mention}! Your AFK status has been removed."
            try:
                if afk_data.get("original_nick") and message.author.display_name.startswith("[AFK]"):
                    await message.author.edit(nick=afk_data["original_nick"])
                    welcome_back_message += " Your nickname has been restored."
            except discord.Forbidden:
                welcome_back_message += " (I couldn't restore your nickname due to permissions.)"
            except discord.HTTPException as e:
                 print(f"Error restoring nickname for {message.author.name}: {e}")

            try:
                await message.channel.send(welcome_back_message, delete_after=10)
            except discord.Forbidden:
                pass

        if message.mentions:
            for mentioned_user in message.mentions:
                if mentioned_user.id in self.afk_users:
                    afk_data = self.afk_users[mentioned_user.id]
                    afk_since = discord.utils.format_dt(afk_data["timestamp"], style='R')
                    afk_message = afk_data["message"]
                    try:
                        await message.reply(
                            f"{mentioned_user.display_name} is AFK ({afk_since}): {afk_message}",
                            delete_after=15
                        )
                    except discord.Forbidden:
                        pass

    # --- Snipe Command ---
    @utility_commands_group.command(name="snipe", description="Shows the last deleted message in this channel.")
    @app_commands.guild_only()
    async def snipe_message(self, interaction: discord.Interaction):
        sniped_msg = self.sniped_messages.get(interaction.channel.id)

        if not sniped_msg:
            await interaction.response.send_message("There's nothing to snipe in this channel!", ephemeral=True)
            return

        embed = discord.Embed(
            description=sniped_msg.content or "[No text content]",
            color=0xd37bff,
            timestamp=sniped_msg.created_at
        )
        embed.set_author(name=str(sniped_msg.author), icon_url=sniped_msg.author.display_avatar.url)
        embed.set_footer(text=f"Sniped message from {sniped_msg.author.display_name}")

        if sniped_msg.attachments:
            first_attachment = sniped_msg.attachments[0]
            if first_attachment.content_type and first_attachment.content_type.startswith("image/"):
                embed.set_image(url=first_attachment.url)
            else:
                embed.add_field(name="Attachment", value=f"[{first_attachment.filename}]({first_attachment.url})", inline=False)
        
        self.sniped_messages.pop(interaction.channel.id, None)
        await interaction.response.send_message(embed=embed)

    # --- AFK Group ---
    afk_group = app_commands.Group(name="afk", description="Set or remove your AFK status.", parent=utility_commands_group)

    @afk_group.command(name="set", description="Sets your AFK status.")
    @app_commands.describe(message="Optional message to display when you are AFK.")
    @app_commands.guild_only()
    async def afk_set(self, interaction: discord.Interaction, message: typing.Optional[str] = "AFK"):
        if interaction.user.id in self.afk_users:
            await interaction.response.send_message("You are already AFK. Use `/util afk remove` to remove it.", ephemeral=True)
            return

        original_nick = None
        new_nick = f"[AFK] {interaction.user.display_name}"
        if len(new_nick) > 32:
            new_nick = new_nick[:28] + "..."

        try:
            if interaction.user.display_name != new_nick:
                original_nick = interaction.user.display_name
                await interaction.user.edit(nick=new_nick)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Your AFK status is set, but I couldn't change your nickname due to permissions.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            print(f"Error setting AFK nickname for {interaction.user.name}: {e}")
            await interaction.response.send_message(
                f"Your AFK status is set, but there was an issue changing your nickname: {e}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(f"You are now AFK. Message: {message}", ephemeral=True)

        self.afk_users[interaction.user.id] = {
            "message": message,
            "timestamp": discord.utils.utcnow(),
            "original_nick": original_nick
        }

    @afk_group.command(name="remove", description="Removes your AFK status.")
    @app_commands.guild_only()
    async def afk_remove(self, interaction: discord.Interaction):
        if interaction.user.id not in self.afk_users:
            await interaction.response.send_message("You are not currently AFK.", ephemeral=True)
            return

        afk_data = self.afk_users.pop(interaction.user.id)
        response_msg = "Your AFK status has been removed."
        try:
            if afk_data.get("original_nick") and interaction.user.display_name.startswith("[AFK]"):
                await interaction.user.edit(nick=afk_data["original_nick"])
                response_msg += " Your nickname has been restored."
        except discord.Forbidden:
            response_msg += " (I couldn't restore your nickname due to permissions.)"
        except discord.HTTPException as e:
            print(f"Error restoring nickname for {interaction.user.name}: {e}")
            response_msg += f" (Error restoring nickname: {e})"
        await interaction.response.send_message(response_msg, ephemeral=True)

    # --- PNG to Static GIF Command ---
    @utility_commands_group.command(name="togif", description="Converts an uploaded PNG image to a static GIF image.")
    @app_commands.describe(image_file="The PNG file to convert.")
    async def png_to_static_gif(self, interaction: discord.Interaction, image_file: discord.Attachment):
        await interaction.response.defer(thinking=True)
        if not image_file.content_type or not image_file.content_type.startswith("image/png"):
            await interaction.followup.send("Please upload a valid PNG file.", ephemeral=True)
            return
        try:
            png_bytes = await image_file.read()
            with Image.open(BytesIO(png_bytes)) as img:
                if img.mode in ['RGBA', 'LA']: pass 
                output_buffer = BytesIO()
                img.save(output_buffer, format="GIF", save_all=False) 
                output_buffer.seek(0)
                discord_file = discord.File(fp=output_buffer, filename=f"{image_file.filename.rsplit('.', 1)[0]}.gif")
                await interaction.followup.send("Here is your converted static GIF:", file=discord_file)
        except UnidentifiedImageError:
            await interaction.followup.send("Could not identify the image. Please ensure it's a valid PNG.", ephemeral=True)
        except Exception as e:
            print(f"Error in png_to_static_gif: {e}")
            await interaction.followup.send(f"An error occurred during conversion: {e}", ephemeral=True)

    # --- Combine Emojis Command ---
    @utility_commands_group.command(name="combineemojis", description="Combines 2 or 3 custom server emojis side-by-side.")
    @app_commands.describe(
        emoji1_str="The first custom emoji (name, ID, or full tag like <:name:id>).",
        emoji2_str="The second custom emoji (name, ID, or full tag).",
        emoji3_str="The third custom emoji (optional; name, ID, or full tag)."
    )
    async def combine_emojis(self,
                             interaction: discord.Interaction,
                             emoji1_str: str,
                             emoji2_str: str,
                             emoji3_str: typing.Optional[str] = None):
        await interaction.response.defer(thinking=True)
        emoji_inputs = [emoji1_str, emoji2_str]
        if emoji3_str: emoji_inputs.append(emoji3_str)
        processed_emojis: typing.List[discord.Emoji] = []
        converter = commands.EmojiConverter()
        for i, emoji_input_str in enumerate(emoji_inputs):
            if emoji_input_str is None: continue
            try:
                emoji_obj = await converter.convert(interaction, emoji_input_str) # type: ignore
                processed_emojis.append(emoji_obj)
            except commands.CommandError as e: 
                await interaction.followup.send(f"Could not find or process emoji '{emoji_input_str}': {e}", ephemeral=True)
                return
            except Exception as e:
                await interaction.followup.send(f"An unexpected error occurred while processing emoji '{emoji_input_str}': {e}", ephemeral=True)
                return
        if len(processed_emojis) < 2:
            await interaction.followup.send("Please provide at least two valid custom emojis to combine.", ephemeral=True)
            return
        images = []
        session = await self._get_session()
        try:
            for emoji_obj in processed_emojis:
                async with session.get(str(emoji_obj.url)) as resp:
                    if resp.status == 200:
                        image_bytes = await resp.read()
                        images.append(Image.open(BytesIO(image_bytes)).convert("RGBA"))
                    else:
                        await interaction.followup.send(f"Failed to download image for emoji: {emoji_obj.name} (Status: {resp.status})", ephemeral=True)
                        return
        except Exception as e:
            print(f"Error downloading emoji images: {e}")
            await interaction.followup.send(f"Error downloading emoji images: {e}", ephemeral=True)
            return
        if not images:
            await interaction.followup.send("No emoji images could be processed.", ephemeral=True)
            return
        target_height = 64
        resized_images = []
        total_width = 0
        padding = 5 
        for img in images:
            aspect_ratio = img.width / img.height
            new_width = int(target_height * aspect_ratio)
            if new_width == 0: new_width = 1 
            resized_img = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
            resized_images.append(resized_img)
            total_width += new_width
        total_width += padding * (len(resized_images) - 1)
        if total_width <= 0: total_width = target_height 
        combined_image = Image.new("RGBA", (total_width, target_height), (0, 0, 0, 0))
        current_x = 0
        for img in resized_images:
            combined_image.paste(img, (current_x, 0), img) 
            current_x += img.width + padding
        output_buffer = BytesIO()
        combined_image.save(output_buffer, format="PNG") 
        output_buffer.seek(0)
        discord_file = discord.File(fp=output_buffer, filename="combined_emojis.png")
        await interaction.followup.send("Here are your combined emojis:", file=discord_file)

    # --- Weather Command ---
    @utility_commands_group.command(name="weather", description="Gets the weather for a location (using wttr.in).")
    @app_commands.describe(location="The city or location to get weather for (e.g., London or New York).")
    async def get_weather(self, interaction: discord.Interaction, location: str):
        await interaction.response.defer(thinking=True)
        session = await self._get_session()
        encoded_location = urllib.parse.quote_plus(location)
        weather_url_png = f"https://wttr.in/{encoded_location}_0pq_transparency=200.png"
        weather_url_text = f"https://wttr.in/{encoded_location}?format=3"
        try:
            async with session.get(weather_url_png) as resp:
                if resp.status == 200:
                    if resp.content_type and resp.content_type.startswith('image/'):
                        image_bytes = await resp.read()
                        discord_file = discord.File(BytesIO(image_bytes), filename=f"{encoded_location}_weather.png")
                        await interaction.followup.send(f"Weather for **{location}**:", file=discord_file)
                        return
                    else: 
                        print(f"wttr.in PNG request for '{location}' returned non-image content type: {resp.content_type}")
                else:
                    print(f"wttr.in PNG request for '{location}' failed with status: {resp.status}")
            async with session.get(weather_url_text) as resp_text:
                if resp_text.status == 200:
                    weather_data = await resp_text.text()
                    if "Unknown location" in weather_data or "Sorry, we are run out of queries" in weather_data:
                         await interaction.followup.send(f"Could not find weather information for **{location}**, or the service is temporarily unavailable.", ephemeral=True)
                    else:
                        embed = discord.Embed(title=f"Weather for {location}", description=f"```\n{weather_data}\n```", color=discord.Color.blue())
                        await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(f"Failed to retrieve weather information for **{location}** using text fallback (Status: {resp_text.status}).", ephemeral=True)
        except aiohttp.ClientConnectorError:
            await interaction.followup.send("Could not connect to the weather service. Please try again later.", ephemeral=True)
        except Exception as e:
            print(f"Error in get_weather: {e}")
            await interaction.followup.send(f"An unexpected error occurred while fetching weather: {e}", ephemeral=True)

    # --- Start Activity Command ---
    @utility_commands_group.command(name="startactivity", description="Starts a Discord activity in a voice channel.")
    @app_commands.describe(
        voice_channel="The voice channel to start the activity in.",
        activity="The activity to start."
    )
    @app_commands.choices(activity=[
        app_commands.Choice(name="YouTube Together", value="880218394199220334"),
        app_commands.Choice(name="Watch Together (Old YT)", value="755600276941176913"),
        app_commands.Choice(name="Poker Night", value="755827207812677713"),
        app_commands.Choice(name="Betrayal.io", value="773336526917861400"),
        app_commands.Choice(name="Fishington.io", value="814288819477020702"),
        app_commands.Choice(name="Chess in the Park", value="832012774040141894"),
        app_commands.Choice(name="Sketch Heads", value="902271654783242291"),
        app_commands.Choice(name="Letter League", value="879863686565621790"),
        app_commands.Choice(name="Word Snacks", value="879863976006127627"),
        app_commands.Choice(name="SpellCast", value="852509694341283871"),
        app_commands.Choice(name="Checkers in the Park", value="832013003968348200"),
        app_commands.Choice(name="Blazing 8s", value="832025144389533716"),
        app_commands.Choice(name="Putt Party", value="945737671220760586"),
        app_commands.Choice(name="Land.io", value="903769130790969345"),
        app_commands.Choice(name="Bobble League", value="947957217959759964"),
        app_commands.Choice(name="Ask Away", value="976052223358406656"),
        app_commands.Choice(name="Know What I Meme", value="950505761862189096"),
        # For custom activities, users would need to know the application ID.
        # Consider adding a 'custom_activity_id' parameter if needed.
    ])
    @app_commands.guild_only()
    async def start_activity_command(self, interaction: discord.Interaction, voice_channel: discord.VoiceChannel, activity: str):
        """Starts a Discord activity in the specified voice channel."""
        if not interaction.guild: # Should be caught by guild_only, but good practice
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        # Check if the bot has permission to create invites in the channel
        bot_member = interaction.guild.me
        if not voice_channel.permissions_for(bot_member).create_instant_invite:
            await interaction.response.send_message(
                f"I don't have permission to create invites (and thus start activities) in {voice_channel.mention}.",
                ephemeral=True
            )
            return

        try:
            # The 'activity' parameter from choices is the application_id (as a string)
            invite = await voice_channel.create_activity_invite(int(activity), max_age=3600) # Invite valid for 1 hour
            await interaction.response.send_message(
                f"Click here to start **{activity_choice_to_name(activity)}** in {voice_channel.mention}:\n{invite.url}"
            )
        except discord.HTTPException as e:
            print(f"Error creating activity invite: {e}")
            await interaction.response.send_message(f"Failed to start the activity: {e}. This might be due to an invalid activity ID or a temporary Discord issue.", ephemeral=True)
        except ValueError: # If activity ID isn't a valid integer (shouldn't happen with choices)
            await interaction.response.send_message("Invalid activity ID format.", ephemeral=True)
        except Exception as e:
            print(f"Unexpected error in start_activity_command: {e}")
            await interaction.response.send_message("An unexpected error occurred while trying to start the activity.", ephemeral=True)

    # --- Error Handler for UtilityCog ---
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original_error = getattr(error, 'original', error)
        print(f"An error occurred in UtilityCog: {error} (Original: {original_error})")

        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage): 
            await interaction.response.send_message(
                "This command cannot be used in Direct Messages.",
                ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions): # Catch if bot lacks Create Invite
            missing_perms_str = ", ".join(error.missing_permissions)
            await interaction.response.send_message(f"I'm missing the following permissions to do that: `{missing_perms_str}`", ephemeral=True)

        else:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An unexpected error occurred with this utility command.",
                    ephemeral=True)
            else:
                try:
                    await interaction.followup.send(
                         "An unexpected error occurred with this utility command.",
                        ephemeral=True)
                except discord.NotFound: 
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
    print("UtilityCog loaded.")

def activity_choice_to_name(activity_id: str) -> str:
    """Helper function to get a display name from an activity ID for nicer messages."""
    # This mapping should ideally match the choices provided in the command.
    mapping = {
        "880218394199220334": "YouTube Together",
        "755600276941176913": "Watch Together (Old YT)",
        "755827207812677713": "Poker Night",
        "773336526917861400": "Betrayal.io",
        "814288819477020702": "Fishington.io",
        "832012774040141894": "Chess in the Park",
        "902271654783242291": "Sketch Heads",
        "879863686565621790": "Letter League",
        "879863976006127627": "Word Snacks",
        "852509694341283871": "SpellCast",
        "832013003968348200": "Checkers in the Park",
        "832025144389533716": "Blazing 8s",
        "945737671220760586": "Putt Party",
        "903769130790969345": "Land.io",
        "947957217959759964": "Bobble League",
        "976052223358406656": "Ask Away",
        "950505761862189096": "Know What I Meme",
    }
    return mapping.get(activity_id, "the selected activity")
