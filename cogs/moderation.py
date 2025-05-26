# cogs/moderation.py
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import typing # For Optional

class Moderation(commands.Cog):
    """
    A cog for server moderation commands, grouped under /mod.
    """
    mod_commands_group = app_commands.Group(name="mod", description="Moderation commands for server management.")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _create_embed(self, title: str, description: str, color: discord.Color, member: discord.Member = None, moderator: discord.Member = None, reason: str = None, duration: datetime.timedelta = None, fields: typing.Optional[list[tuple[str,str,bool]]] = None):
        embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
        if member:
            embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        if moderator:
            embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})", inline=False)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        if duration:
            embed.add_field(name="Duration", value=str(duration), inline=False)
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        embed.set_footer(text=f"Bot: {self.bot.user.name}")
        return embed

    @mod_commands_group.command(name="kick", description="Kicks a member from the server.")
    @app_commands.describe(
        member="The member to kick.",
        reason="The reason for kicking the member."
    )
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.guild_only()
    async def kick_member(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
        if member == interaction.user:
            await interaction.response.send_message("You cannot kick yourself.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user :
            await interaction.response.send_message("You cannot kick a member with a higher or equal role.", ephemeral=True)
            return
        if member == interaction.guild.owner:
            await interaction.response.send_message("You cannot kick the server owner.", ephemeral=True)
            return
        if member.guild_permissions.administrator and interaction.guild.owner != interaction.user:
             await interaction.response.send_message("You cannot kick an administrator unless you are the server owner.", ephemeral=True)
             return

        try:
            await member.kick(reason=f"Kicked by {interaction.user.name} | Reason: {reason}")
            embed = self._create_embed(
                title="<:hammer:123456789012345678> Member Kicked", # Replace with valid emoji
                description=f"{member.mention} has been kicked from the server.",
                color=0xd37bff,
                member=member,
                moderator=interaction.user,
                reason=reason
            )
            await interaction.response.send_message(embed=embed)
            try:
                dm_embed = self._create_embed(
                    title="You Have Been Kicked",
                    description=f"You have been kicked from **{interaction.guild.name}**.",
                    color=0xd37bff,
                    reason=reason,
                    moderator=interaction.user
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                print(f"Could not DM {member.name} after kicking.")
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to kick this member.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"An error occurred while trying to kick the member: {e}", ephemeral=True)

    @mod_commands_group.command(name="ban", description="Bans a member from the server.")
    @app_commands.describe(
        member="The member to ban.",
        reason="The reason for banning the member.",
        delete_message_days="Number of days of messages to delete (0-7). Default is 0."
    )
    @app_commands.choices(delete_message_days=[
        app_commands.Choice(name="Don't delete any", value=0),
        app_commands.Choice(name="1 Day", value=1),
        app_commands.Choice(name="3 Days", value=3),
        app_commands.Choice(name="7 Days", value=7)
    ])
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.guild_only()
    async def ban_member(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided.", delete_message_days: int = 0):
        if member == interaction.user:
            await interaction.response.send_message("You cannot ban yourself.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
            await interaction.response.send_message("You cannot ban a member with a higher or equal role.", ephemeral=True)
            return
        if member == interaction.guild.owner:
            await interaction.response.send_message("You cannot ban the server owner.", ephemeral=True)
            return
        if member.guild_permissions.administrator and interaction.guild.owner != interaction.user:
             await interaction.response.send_message("You cannot ban an administrator unless you are the server owner.", ephemeral=True)
             return

        if not 0 <= delete_message_days <= 7:
            await interaction.response.send_message("`delete_message_days` must be between 0 and 7.", ephemeral=True)
            return

        try:
            await member.ban(reason=f"Banned by {interaction.user.name} | Reason: {reason}", delete_message_days=delete_message_days)
            embed = self._create_embed(
                title="<:no_entry_sign:123456789012345678> Member Banned", # Replace with valid emoji
                description=f"{member.mention} has been banned from the server.",
                color=discord.Color.red(),
                member=member,
                moderator=interaction.user,
                reason=reason,
                fields=[("Messages Deleted", f"{delete_message_days} day(s) worth", False)]
            )
            await interaction.response.send_message(embed=embed)
            try:
                dm_embed = self._create_embed(
                    title="You Have Been Banned",
                    description=f"You have been banned from **{interaction.guild.name}**.",
                    color=discord.Color.red(),
                    reason=reason,
                    moderator=interaction.user
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                print(f"Could not DM {member.name} after banning.")
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to ban this member.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"An error occurred while trying to ban the member: {e}", ephemeral=True)

    @mod_commands_group.command(name="unban", description="Unbans a user from the server.")
    @app_commands.describe(
        user_id="The ID of the user to unban.",
        reason="The reason for unbanning the user."
    )
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.guild_only()
    async def unban_user(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided."):
        try:
            user_id_int = int(user_id)
        except ValueError:
            await interaction.response.send_message("Invalid User ID format. Please provide a numerical ID.", ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(user_id_int)
        except discord.NotFound:
            await interaction.response.send_message(f"User with ID `{user_id_int}` not found.", ephemeral=True)
            return
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Failed to fetch user: {e}", ephemeral=True)
            return

        try:
            await interaction.guild.unban(user, reason=f"Unbanned by {interaction.user.name} | Reason: {reason}")
            embed = self._create_embed(
                title="<:unlock:123456789012345678> User Unbanned", # Replace with valid emoji
                description=f"{user.mention} ({user.id}) has been unbanned from the server.",
                color=discord.Color.green(),
                moderator=interaction.user,
                reason=reason
            )
            # Add a field for the unbanned user since 'member' object isn't available directly
            embed.add_field(name="User", value=f"{user.name}#{user.discriminator} ({user.id})", inline=False)
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to unban users.", ephemeral=True)
        except discord.HTTPException as e:
            if "Unknown Ban" in str(e):
                 await interaction.response.send_message(f"User {user.name}#{user.discriminator} is not banned from this server.", ephemeral=True)
            else:
                await interaction.response.send_message(f"An error occurred while trying to unban the user: {e}", ephemeral=True)

    @mod_commands_group.command(name="mute", description="Mutes (times out) a member for a specified duration.")
    @app_commands.describe(
        member="The member to mute.",
        duration_str="Duration (e.g., 10m, 1h, 1d). Max 28 days. s=seconds, m=minutes, h=hours, d=days.",
        reason="The reason for muting the member."
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def mute_member(self, interaction: discord.Interaction, member: discord.Member, duration_str: str, reason: str = "No reason provided."):
        if member == interaction.user:
            await interaction.response.send_message("You cannot mute yourself.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
            await interaction.response.send_message("You cannot mute a member with a higher or equal role.", ephemeral=True)
            return
        if member == interaction.guild.owner:
            await interaction.response.send_message("You cannot mute the server owner.", ephemeral=True)
            return
        if member.guild_permissions.administrator and interaction.guild.owner != interaction.user:
             await interaction.response.send_message("You cannot mute an administrator unless you are the server owner.", ephemeral=True)
             return
        if member.is_timed_out():
            await interaction.response.send_message(f"{member.mention} is already timed out.", ephemeral=True)
            return

        delta = None
        unit = duration_str[-1].lower()
        try:
            time_value = int(duration_str[:-1])
            if unit == 's':
                delta = datetime.timedelta(seconds=time_value)
            elif unit == 'm':
                delta = datetime.timedelta(minutes=time_value)
            elif unit == 'h':
                delta = datetime.timedelta(hours=time_value)
            elif unit == 'd':
                delta = datetime.timedelta(days=time_value)
            else:
                await interaction.response.send_message("Invalid duration unit. Use 's', 'm', 'h', or 'd'.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Invalid duration format. Example: `10m`, `1h`, `2d`.", ephemeral=True)
            return

        if delta is None or delta <= datetime.timedelta(seconds=0):
            await interaction.response.send_message("Duration must be positive.", ephemeral=True)
            return

        max_duration = datetime.timedelta(days=28)
        if delta > max_duration:
            await interaction.response.send_message(f"Duration cannot exceed 28 days. You provided: {delta}", ephemeral=True)
            return

        try:
            await member.timeout(delta, reason=f"Muted by {interaction.user.name} | Reason: {reason}")
            timeout_until = discord.utils.utcnow() + delta
            embed = self._create_embed(
                title="<:mute:123456789012345678> Member Muted (Timed Out)", # Replace with valid emoji
                description=f"{member.mention} has been muted.",
                color=discord.Color.light_grey(),
                member=member,
                moderator=interaction.user,
                reason=reason,
                duration=delta,
                fields=[("Muted Until", f"<t:{int(timeout_until.timestamp())}:F> (<t:{int(timeout_until.timestamp())}:R>)", False)]
            )
            await interaction.response.send_message(embed=embed)
            try:
                dm_embed = self._create_embed(
                    title="You Have Been Muted",
                    description=f"You have been muted in **{interaction.guild.name}**.",
                    color=discord.Color.light_grey(),
                    reason=reason,
                    moderator=interaction.user,
                    duration=delta,
                    fields=[("Muted Until", f"<t:{int(timeout_until.timestamp())}:F>", False)]
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                print(f"Could not DM {member.name} after muting.")
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to timeout this member.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"An error occurred while trying to mute the member: {e}", ephemeral=True)

    @mod_commands_group.command(name="unmute", description="Unmutes (removes timeout from) a member.")
    @app_commands.describe(
        member="The member to unmute.",
        reason="The reason for unmuting the member."
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def unmute_member(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
        if not member.is_timed_out():
            await interaction.response.send_message(f"{member.mention} is not currently timed out.", ephemeral=True)
            return

        try:
            await member.timeout(None, reason=f"Unmuted by {interaction.user.name} | Reason: {reason}")
            embed = self._create_embed(
                title="<:speaker:123456789012345678> Member Unmuted", # Replace with valid emoji
                description=f"{member.mention} has been unmuted.",
                color=discord.Color.dark_green(),
                member=member,
                moderator=interaction.user,
                reason=reason
            )
            await interaction.response.send_message(embed=embed)
            try:
                dm_embed = self._create_embed(
                    title="You Have Been Unmuted",
                    description=f"You have been unmuted in **{interaction.guild.name}**.",
                    color=discord.Color.dark_green(),
                    reason=reason,
                    moderator=interaction.user
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                print(f"Could not DM {member.name} after unmuting.")
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to remove the timeout from this member.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"An error occurred while trying to unmute the member: {e}", ephemeral=True)

    @mod_commands_group.command(name="clear", description="Deletes a specified number of messages from a channel.")
    @app_commands.rename(amount_to_delete='amount') # Rename for clarity in slash command
    @app_commands.describe(
        amount_to_delete="The number of messages to delete (1-100).",
        member="Optional: Filter messages by this member."
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def clear_messages(self, interaction: discord.Interaction, amount_to_delete: app_commands.Range[int, 1, 100], member: typing.Optional[discord.Member] = None):
        await interaction.response.defer(ephemeral=True, thinking=True) # Ephemeral defer for mod action

        def check(m):
            if member:
                return m.author == member
            return True

        try:
            deleted_messages = await interaction.channel.purge(limit=amount_to_delete, check=check)
            response_message = f"Successfully deleted {len(deleted_messages)} message(s)."
            if member:
                response_message += f" from {member.mention}."
            await interaction.followup.send(response_message, ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("I do not have permission to delete messages in this channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"An error occurred while deleting messages: {e}", ephemeral=True)


    @mod_commands_group.command(name="warn", description="Warns a member.")
    @app_commands.describe(
        member="The member to warn.",
        reason="The reason for the warning."
    )
    @app_commands.checks.has_permissions(kick_members=True) # Or moderate_members, depending on desired strictness
    @app_commands.guild_only()
    async def warn_member(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if member == interaction.user:
            await interaction.response.send_message("You cannot warn yourself.", ephemeral=True)
            return
        if member.bot:
            await interaction.response.send_message("You cannot warn a bot.", ephemeral=True)
            return
        # Add role hierarchy check if desired (similar to kick/ban)

        warning_embed_channel = self._create_embed(
            title="<:warning:123456789012345678> Member Warned", # Replace with valid emoji
            description=f"{member.mention} has been warned.",
            color=discord.Color.gold(),
            member=member,
            moderator=interaction.user,
            reason=reason
        )

        warning_embed_dm = self._create_embed(
            title="You Have Been Warned",
            description=f"You have received a warning in **{interaction.guild.name}**.",
            color=discord.Color.gold(),
            reason=reason,
            moderator=interaction.user,
            fields=[("Server", interaction.guild.name, False)]
        )

        try:
            await member.send(embed=warning_embed_dm)
            dm_sent = True
        except discord.Forbidden:
            dm_sent = False
            print(f"Could not DM {member.name} about their warning.")

        await interaction.response.send_message(embed=warning_embed_channel)
        if not dm_sent:
            await interaction.followup.send(f"(Could not send a DM to {member.mention})", ephemeral=True)


    @mod_commands_group.command(name="slowmode", description="Sets the slowmode for the current channel.")
    @app_commands.describe(
        seconds="The slowmode delay in seconds (0 to disable, max 21600)."
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def set_slowmode(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
        if not isinstance(interaction.channel, discord.TextChannel): # Should be caught by guild_only too
            await interaction.response.send_message("This command can only be used in text channels.", ephemeral=True)
            return

        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            if seconds == 0:
                await interaction.response.send_message(f"Slowmode has been disabled for {interaction.channel.mention}.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Slowmode for {interaction.channel.mention} has been set to {seconds} second(s).", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to change slowmode in this channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"An error occurred while setting slowmode: {e}", ephemeral=True)


    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await interaction.response.send_message(
                f"You don't have the required permissions to use this command. Missing: `{missing_perms}`",
                ephemeral=True
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await interaction.response.send_message(
                f"I don't have the required permissions to perform this action. Missing: `{missing_perms}`.",
                ephemeral=True
            )
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                ephemeral=True
            )
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message(
                "This command cannot be used in Direct Messages.",
                ephemeral=True
            )
        else:
            print(f"An error occurred in Moderation cog: {error} (Original: {getattr(error, 'original', error)})")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An unexpected error occurred. Please try again later.",
                    ephemeral=True
                )
            else:
                try:
                    await interaction.followup.send("An unexpected error occurred. Please try again later.",ephemeral=True)
                except discord.NotFound: # Interaction might have expired
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
    print("Moderation cog loaded and 'mod' command group (with subcommands) should be registered.")

