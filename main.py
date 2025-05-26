import discord
import discord_ios
from discord.ext import commands
import pomice
import os
from dotenv import load_dotenv 
import asyncio


load_dotenv() 

BOT_TOKEN = os.environ.get("DISCORD_TOKEN")
COGS_DIR = "cogs"
BOT_OWNER_ID = 895722260726440007

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    intents=intents,
    activity=discord.CustomActivity(name='hello?'),
    owner_id=BOT_OWNER_ID,
)

async def init_lavalink_node():
    await bot.wait_until_ready()  # Wait until the bot is ready
    if not hasattr(bot, "pomice"):
        bot.pomice = await pomice.NodePool().create_node(
            bot=bot,
            host="lavalinkv3.devxcode.in",
            port=443,
            password="DevamOP",
            identifier="MAIN",
            secure=True,
        )
        print("[init_lavalink_node] Lavalink node initialized.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

async def load_cogs():
    if not os.path.exists(COGS_DIR):
        os.makedirs(COGS_DIR)
        print(f"Created directory {COGS_DIR}")
        return

    for filename in os.listdir(COGS_DIR):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = f"{COGS_DIR}.{filename[:-3]}"
            try:
                await bot.load_extension(cog_name)
                print(f"Loaded cog: {cog_name}")
            except Exception as e:
                print(f"Failed to load cog {cog_name}: {e}")

async def main():
    async with bot:
        # Load cogs first
        await load_cogs()

        # Start lavalink node initialization task without awaiting here
        bot.loop.create_task(init_lavalink_node())

        if BOT_TOKEN == "YOUR_BOT_TOKEN":
            print("ERROR: Replace BOT_TOKEN with your actual token.")
            return

        try:
            await bot.start(BOT_TOKEN)
        except discord.LoginFailure:
            print("Login failed: Invalid token.")
        except Exception as e:
            print(f"Bot error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutting down...")
