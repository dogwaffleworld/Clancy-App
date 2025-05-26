import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio

API_URL = "https://groq.dogwaffle.world/"

class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        await self.session.close()

    @app_commands.command(name="ask", description="Sends a prompt to a custom AI endpoint.")
    @app_commands.describe(prompt="The text you want to send to the AI.")
    async def ask_ai_command(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer(thinking=True)

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "session_id": str(interaction.user.name)
        }

        headers = {
            "Content-Type": "application/json" # Assuming the request still needs to be JSON
        }

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with self.session.post(API_URL, json=payload, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    ai_message_content = "<:Ai:1376557302127001600>" + await response.text()

                    if ai_message_content:
                        # Discord messages have a 2000 character limit.
                        if len(ai_message_content) <= 2000:
                            await interaction.followup.send(ai_message_content)
                        else:
                            # If the message is too long, send the beginning and indicate truncation.
                            # Alternatively, you could send it as a file or split it into multiple messages.
                            await interaction.followup.send(ai_message_content[:1980] + "\n\n[Response truncated due to length]")
                    else:
                        await interaction.followup.send("AI returned an empty response.", ephemeral=True)
                else:
                    response_text = await response.text() # Get error response as text
                    error_message = f"Error calling AI endpoint: {response.status} - {response.reason}\n```\n{response_text[:1000]}\n```"
                    await interaction.followup.send(error_message, ephemeral=True)

        except aiohttp.ClientConnectorError:
            await interaction.followup.send(f"Error: Could not connect to the AI endpoint at `{API_URL}`. It might be down or inaccessible.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send(f"Error: The request to the AI endpoint timed out after 30 seconds.", ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred in ask_ai_command: {e}")
            await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                ephemeral=True
            )
        elif isinstance(error, app_commands.NoPrivateMessage): # Should not be hit if command is global
            await interaction.response.send_message(
                "This command cannot be used in Direct Messages.",
                ephemeral=True
            )
        else:
            print(f"An error occurred in AICog: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An unexpected error occurred. Please try again later.",
                    ephemeral=True
                )
            else:
                # If defer() was called, response is already "done" in a way, so use followup
                await interaction.followup.send(
                    "An unexpected error occurred. Please try again later.",
                    ephemeral=True
                )

async def setup(bot: commands.Bot):
    await bot.add_cog(AICog(bot))
    print("AICog loaded.")