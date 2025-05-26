# cogs/fun_cog.py
import discord
from discord.ext import commands
from discord import app_commands
import random

class FunCog(commands.Cog):
    """
    A cog for fun, miscellaneous commands, grouped under /fun.
    """
    fun_commands_group = app_commands.Group(name="fun", description="Fun commands for your entertainment!")
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- Coinflip Command ---
    @fun_commands_group.command(name="coinflip", description="Flips a coin!")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙"
        embed = discord.Embed(
            title=f"{emoji} Coinflip Result {emoji}",
            description=f"The coin landed on: **{result}**!",
            color=discord.Color.gold() if result == "Heads" else discord.Color.dark_grey()
        )
        embed.set_footer(text=f"Flipped by: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # --- Slots Command ---
    @fun_commands_group.command(name="slots", description="Play the slot machine!")
    async def slots(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        emojis = ["🍒", "🔔", "🍊", "🍋", "🍉", "⭐", "💎", "�"]
        reels = [random.choice(emojis) for _ in range(3)]
        result_message = ""
        payout_color = discord.Color.light_grey()

        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "💎":
                result_message = f"🎉 JACKPOT! 🎉\nAll three are {reels[0]}! You win BIG!"
                payout_color = discord.Color.blue()
            elif reels[0] == "⭐":
                result_message = f"🌟 SUPER WIN! 🌟\nAll three are {reels[0]}! You win a lot!"
                payout_color = discord.Color.gold()
            else:
                result_message = f"🥳 WINNER! 🥳\nAll three are {reels[0]}! You win!"
                payout_color = discord.Color.green()
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            match_symbol = ""
            if reels[0] == reels[1]: match_symbol = reels[0]
            elif reels[1] == reels[2]: match_symbol = reels[1]
            else: match_symbol = reels[0] # reels[0] == reels[2]

            if match_symbol == "🍀":
                result_message = f"🍀 Lucky! 🍀\nTwo {match_symbol}! Small win!"
                payout_color = discord.Color.dark_green()
            else:
                result_message = f"👍 Nice! 👍\nTwo {match_symbol}! A small prize!"
                payout_color = 0xd37bff
        else:
            result_message = "😢 Better luck next time! 😢\nNo matching symbols."
            payout_color = discord.Color.red()

        slot_display = " | ".join(reels)
        embed = discord.Embed(
            title="🎰 Slot Machine 🎰",
            description=f"**{slot_display}**\n\n{result_message}",
            color=payout_color
        )
        embed.set_footer(text=f"Played by: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    # --- Dice Roll Command ---
    @fun_commands_group.command(name="roll", description="Rolls one or more dice.")
    @app_commands.describe(dice_format="Format of dice to roll (e.g., 1d6, 2d10, d20).")
    async def roll_dice(self, interaction: discord.Interaction, dice_format: str):
        try:
            dice_format = dice_format.lower()
            num_dice, num_sides = 1, 0
            if 'd' not in dice_format:
                raise ValueError("Invalid format. Use 'XdY' (e.g., 2d6) or 'dY' (e.g., d20).")
            parts = dice_format.split('d')
            if parts[0] == "": num_dice = 1
            else: num_dice = int(parts[0])
            num_sides = int(parts[1])

            if not 1 <= num_dice <= 100:
                await interaction.response.send_message("Number of dice must be between 1 and 100.", ephemeral=True)
                return
            if not 2 <= num_sides <= 1000:
                await interaction.response.send_message("Number of sides per die must be between 2 and 1000.", ephemeral=True)
                return

            rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
            total = sum(rolls)
            embed = discord.Embed(title="🎲 Dice Roll Result 🎲", description=f"You rolled **{dice_format}**:", color=discord.Color.purple())
            if num_dice == 1:
                embed.add_field(name="Result", value=f"**{total}**", inline=False)
            else:
                embed.add_field(name="Individual Rolls", value=f"`{', '.join(map(str, rolls))}`", inline=False)
                embed.add_field(name="Total", value=f"**{total}**", inline=False)
            embed.set_footer(text=f"Rolled by: {interaction.user.display_name}")
            await interaction.response.send_message(embed=embed)
        except ValueError as e:
            await interaction.response.send_message(f"Error: {e}\nPlease use a valid dice format (e.g., `2d6`, `d20`).", ephemeral=True)
        except Exception as e:
            print(f"Error in roll_dice: {e}")
            await interaction.response.send_message("An unexpected error occurred while rolling the dice.", ephemeral=True)

    # --- 8Ball Command ---
    @fun_commands_group.command(name="8ball", description="Ask the magic 8-ball a yes/no question.")
    @app_commands.describe(question="Your yes/no question for the magic 8-ball.")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes – definitely.",
            "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
            "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
            "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        answer = random.choice(responses)
        embed = discord.Embed(title="🎱 Magic 8-Ball 🎱", color=discord.Color.dark_blue())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)
        embed.set_footer(text=f"Asked by: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # --- Ask (Q&A) Command ---
    @fun_commands_group.command(name="ask", description="Ask a question and get a fun (not serious) answer.")
    @app_commands.describe(question="Your question for a whimsical answer.")
    async def ask_question(self, interaction: discord.Interaction, question: str):
        answers = [
            "Hmm, that's a thinker! Let me ponder that... or maybe not.",
            "The answer is 42. Or is it? Who knows!",
            "Sources say... maybe! Or perhaps consult a cookie.",
            "That's an excellent question! I wish I had an excellent answer.",
            "My circuits are buzzing with uncertainty on that one.",
            "Let's just say 'yes' and move on, shall we?",
            "Ask me again after my coffee break.",
            "The stars are not aligned to answer that right now.",
            "Could you repeat the question? I was busy admiring your avatar.",
            "That's classified information. Or I just don't know.",
            "The answer lies within you... or a quick web search.",
            "Probably.", "Unlikely.", "Definitely maybe."
        ]
        answer = random.choice(answers)
        embed = discord.Embed(title="💬 Q&A Time 💬", color=discord.Color.teal())
        embed.add_field(name="Your Question", value=question, inline=False)
        embed.add_field(name="My Whimsical Answer", value=answer, inline=False)
        embed.set_footer(text=f"Pondered by: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # --- Choose Command ---
    @fun_commands_group.command(name="choose", description="Let the bot choose from your options.")
    @app_commands.describe(options="A list of options separated by a comma (e.g., option1, option2, option3).")
    async def choose_options(self, interaction: discord.Interaction, options: str):
        choices = [choice.strip() for choice in options.split(',')]
        if not choices or (len(choices) == 1 and not choices[0]):
            await interaction.response.send_message("Please provide at least one option, separated by commas.", ephemeral=True)
            return
        if len(choices) < 2:
            await interaction.response.send_message("Please provide at least two options for me to choose from!", ephemeral=True)
            return

        chosen_option = random.choice(choices)
        embed = discord.Embed(title="🤔 My Choice 🤔", color=discord.Color.magenta())
        embed.add_field(name="You Provided", value=f"`{options}`", inline=False)
        embed.add_field(name="I Choose", value=f"**{chosen_option}**", inline=False)
        embed.set_footer(text=f"Decided for: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # --- Error Handler for FunCog ---
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message(
                "This command cannot be used in Direct Messages.",
                ephemeral=True)
        else:
            print(f"An error occurred in FunCog: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An unexpected error occurred with this fun command.",
                    ephemeral=True)
            else:
                await interaction.followup.send(
                     "An unexpected error occurred with this fun command.",
                    ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(FunCog(bot))
    print("FunCog loaded and 'fun' command group (with subcommands) should be registered.")
