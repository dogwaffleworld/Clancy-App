# cogs/manage_cog.py
import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
import traceback # For detailed error messages

# Directory where your cogs are stored, relative to the main bot file.
# Ensure this matches the COGS_DIR in your main.py if you're referencing it.
COGS_DIR = "cogs"

async def is_bot_owner_check(interaction: discord.Interaction) -> bool:
    """Checks if the user invoking the command is the bot owner."""
    if await interaction.client.is_owner(interaction.user):
        return True
    # Send the response only if the check fails and the interaction hasn't been responded to.
    # This prevents "already responded" errors if a command also tries to respond.
    if not interaction.response.is_done():
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
    return False

class ManageCog(commands.Cog):
    """
    A cog for bot management commands, restricted to the bot owner.
    """
    manage_commands_group = app_commands.Group(
        name="manage",
        description="Bot management commands (owner only)."
        # The 'checks' argument is removed from here.
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @manage_commands_group.command(name="status", description="Changes the bot's presence/status.")
    @app_commands.check(is_bot_owner_check) # Apply check here
    @app_commands.describe(
        activity_type="The type of activity to display.",
        name="The text to display for the status (required for most types).",
        url="The URL for streaming status (only for Streaming type)."
    )
    @app_commands.choices(activity_type=[
        app_commands.Choice(name="Playing", value="playing"),
        app_commands.Choice(name="Listening to", value="listening"),
        app_commands.Choice(name="Watching", value="watching"),
        app_commands.Choice(name="Streaming", value="streaming"),
        app_commands.Choice(name="Clear Status", value="clear"),
    ])
    async def change_status(self, interaction: discord.Interaction, activity_type: str, name: str = None, url: str = None):
        activity = None
        current_status = self.bot.guilds[0].me.status if self.bot.guilds else discord.Status.online

        if activity_type == "clear":
            activity = None
        elif activity_type == "playing":
            if not name:
                await interaction.response.send_message("A name is required for 'Playing' status.", ephemeral=True)
                return
            activity = discord.Game(name=name)
        elif activity_type == "listening":
            if not name:
                await interaction.response.send_message("A name is required for 'Listening to' status.", ephemeral=True)
                return
            activity = discord.Activity(type=discord.ActivityType.listening, name=name)
        elif activity_type == "watching":
            if not name:
                await interaction.response.send_message("A name is required for 'Watching' status.", ephemeral=True)
                return
            activity = discord.Activity(type=discord.ActivityType.watching, name=name)
        elif activity_type == "streaming":
            if not name:
                await interaction.response.send_message("A name is required for 'Streaming' status.", ephemeral=True)
                return
            if not url:
                await interaction.response.send_message("A URL is required for 'Streaming' status.", ephemeral=True)
                return
            activity = discord.Streaming(name=name, url=url)
        else:
            await interaction.response.send_message("Invalid activity type selected.", ephemeral=True)
            return

        try:
            await self.bot.change_presence(activity=activity, status=current_status)
            if activity_type == "clear":
                await interaction.response.send_message("Bot status cleared.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Bot status updated to: {activity_type.capitalize()} {name or ''}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to update status: {e}", ephemeral=True)

    async def _cog_operation(self, interaction: discord.Interaction, operation: str, cog_name: str):
        proper_cog_name = cog_name if cog_name.startswith(f"{COGS_DIR}.") else f"{COGS_DIR}.{cog_name}"
        action_past_tense = {
            "load": "loaded", "unload": "unloaded", "reload": "reloaded"
        }.get(operation, operation + "ed")

        try:
            if operation == "load":
                await self.bot.load_extension(proper_cog_name)
            elif operation == "unload":
                await self.bot.unload_extension(proper_cog_name)
            elif operation == "reload":
                await self.bot.reload_extension(proper_cog_name)
            else:
                # This path should ideally not be reached if called internally
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"Unknown cog operation: {operation}", ephemeral=True)
                else:
                    await interaction.followup.send(f"Unknown cog operation: {operation}", ephemeral=True)
                return
            # Send response only if not already done (e.g. by a check failure)
            if not interaction.response.is_done():
                 await interaction.response.send_message(f"Cog `{proper_cog_name}` has been {action_past_tense}.", ephemeral=True)
            else: # If response was already sent (e.g. by a check that failed but command continued), use followup
                 await interaction.followup.send(f"Cog `{proper_cog_name}` has been {action_past_tense}.", ephemeral=True)

        except commands.ExtensionNotFound:
            if not interaction.response.is_done(): await interaction.response.send_message(f"Cog `{proper_cog_name}` not found.", ephemeral=True)
            else: await interaction.followup.send(f"Cog `{proper_cog_name}` not found.", ephemeral=True)
        except commands.ExtensionAlreadyLoaded:
            if not interaction.response.is_done(): await interaction.response.send_message(f"Cog `{proper_cog_name}` is already loaded.", ephemeral=True)
            else: await interaction.followup.send(f"Cog `{proper_cog_name}` is already loaded.", ephemeral=True)
        except commands.ExtensionNotLoaded:
            if not interaction.response.is_done(): await interaction.response.send_message(f"Cog `{proper_cog_name}` is not loaded.", ephemeral=True)
            else: await interaction.followup.send(f"Cog `{proper_cog_name}` is not loaded.", ephemeral=True)
        except commands.NoEntryPointError:
            if not interaction.response.is_done(): await interaction.response.send_message(f"Cog `{proper_cog_name}` does not have a setup function.", ephemeral=True)
            else: await interaction.followup.send(f"Cog `{proper_cog_name}` does not have a setup function.", ephemeral=True)
        except commands.ExtensionFailed as e:
            error_info = f"{type(e.original).__name__}: {e.original}"
            traceback_info = traceback.format_exc()
            msg = (
                f"Failed to {operation} cog `{proper_cog_name}`.\n"
                f"Error: `{error_info}`\n"
                f"```py\n{traceback_info[:1800]}\n```"
            )
            if not interaction.response.is_done(): await interaction.response.send_message(msg, ephemeral=True)
            else: await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            msg = f"An unexpected error occurred while trying to {operation} `{proper_cog_name}`: {e}"
            if not interaction.response.is_done(): await interaction.response.send_message(msg, ephemeral=True)
            else: await interaction.followup.send(msg, ephemeral=True)

    @manage_commands_group.command(name="load_cog", description="Loads a cog.")
    @app_commands.check(is_bot_owner_check) # Apply check here
    @app_commands.describe(cog_name="The name of the cog to load (e.g., fun_cog).")
    async def load_cog_command(self, interaction: discord.Interaction, cog_name: str):
        await self._cog_operation(interaction, "load", cog_name)

    @manage_commands_group.command(name="unload_cog", description="Unloads a cog.")
    @app_commands.check(is_bot_owner_check) # Apply check here
    @app_commands.describe(cog_name="The name of the cog to unload (e.g., fun_cog).")
    async def unload_cog_command(self, interaction: discord.Interaction, cog_name: str):
        if f"{COGS_DIR}.{cog_name}" == __name__:
             # Check if response is already done by is_bot_owner_check
            if not interaction.response.is_done():
                await interaction.response.send_message("You cannot unload the management cog itself.", ephemeral=True)
            else: # If is_bot_owner_check already responded (e.g. on failure), use followup
                await interaction.followup.send("You cannot unload the management cog itself.", ephemeral=True)
            return
        await self._cog_operation(interaction, "unload", cog_name)

    @manage_commands_group.command(name="reload_cog", description="Reloads a specific cog.")
    @app_commands.check(is_bot_owner_check) # Apply check here
    @app_commands.describe(cog_name="The name of the cog to reload (e.g., fun_cog).")
    async def reload_cog_command(self, interaction: discord.Interaction, cog_name: str):
        await self._cog_operation(interaction, "reload", cog_name)

    @manage_commands_group.command(name="reload_all_cogs", description="Reloads all cogs in the cogs directory.")
    @app_commands.check(is_bot_owner_check) # Apply check here
    async def reload_all_cogs_command(self, interaction: discord.Interaction):
        # Deferral should happen after the check, or the check's response might be lost.
        # However, for long operations, defer early. Let's assume check is fast.
        await interaction.response.defer(ephemeral=True, thinking=True)
        reloaded_cogs = []
        failed_cogs = {}

        extensions_to_unload = list(self.bot.extensions.keys())
        for extension_name in extensions_to_unload:
            if extension_name == __name__:
                continue
            try:
                await self.bot.unload_extension(extension_name)
            except Exception as e:
                failed_cogs[extension_name] = f"Failed to unload: {e}"

        if not os.path.exists(COGS_DIR):
            await interaction.followup.send(f"Error: Cogs directory '{COGS_DIR}' not found.", ephemeral=True)
            return

        for filename in os.listdir(COGS_DIR):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_module_name = f"{COGS_DIR}.{filename[:-3]}"
                try:
                    await self.bot.load_extension(cog_module_name)
                    reloaded_cogs.append(cog_module_name)
                except Exception as e:
                    failed_cogs[cog_module_name] = f"Failed to load: {e}"

        response_message = "Cog reload process finished.\n"
        if reloaded_cogs:
            response_message += f"Successfully loaded/reloaded: `{'`, `'.join(reloaded_cogs)}`\n"
        if failed_cogs:
            response_message += "Failed operations:\n"
            for cog, error in failed_cogs.items():
                response_message += f"- `{cog}`: {error}\n"

        await interaction.followup.send(response_message[:2000], ephemeral=True)


    @manage_commands_group.command(name="shutdown", description="Shuts down the bot gracefully.")
    @app_commands.check(is_bot_owner_check) # Apply check here
    async def shutdown_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Shutting down the bot...", ephemeral=True)
        await self.bot.close()

    @manage_commands_group.command(name="restart", description="Restarts the bot.")
    @app_commands.check(is_bot_owner_check) # Apply check here
    async def restart_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Attempting to restart the bot...", ephemeral=True)
        try:
            await self.bot.close()
        except Exception as e:
            print(f"Error during pre-restart shutdown: {e}")
        
        try:
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            print(f"Failed to execv for restart: {e}")
            try:
                # This followup might not always work if the bot is in a bad state after close()
                await interaction.followup.send(f"Critical error during restart: {e}. Manual restart may be required.",ephemeral=True)
            except:
                pass # Best effort

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original_error = getattr(error, 'original', error)
        
        # Check if the error is a CheckFailure and if a response has already been sent by our check
        if isinstance(error, app_commands.CheckFailure):
            # is_bot_owner_check sends its own message, so we don't need to send another one here
            # if interaction.response.is_done() is True due to that check.
            # However, if another check failed that didn't send a message, this would be a fallback.
            if not interaction.response.is_done():
                 await interaction.response.send_message("You do not have permission to use this command or a check failed.", ephemeral=True)
            return # Stop further processing for CheckFailure if handled or already responded.

        # Handle other specific app command errors if needed
        # ...

        # Generic fallback for other errors
        print(f"An error occurred in ManageCog: {error} (Original: {original_error})")
        if not interaction.response.is_done():
            await interaction.response.send_message("An unexpected error occurred with this management command.", ephemeral=True)
        else:
            # If deferred or a check failed but the command proceeded somehow and then errored.
            await interaction.followup.send("An unexpected error occurred with this management command.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ManageCog(bot))
    print("ManageCog loaded and 'manage' command group (with subcommands) should be registered.")
