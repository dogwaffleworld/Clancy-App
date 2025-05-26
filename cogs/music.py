import discord
from discord.ext import commands
from discord import app_commands
import pomice
from urllib.parse import urlparse, parse_qs

def get_youtube_video_id(url):
    parsed_url = urlparse(url)
    return parse_qs(parsed_url.query).get('v', [None])[0]

class MusicCog(commands.Cog):
    music_commands_group = app_commands.Group(name="music", description="Music commands for your entertainment!")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # DON'T do: self.pomice = bot.pomice here because bot.pomice might not be ready

    def get_node(self):
        # Safe getter for the Lavalink node (pomice NodePool)
        return getattr(self.bot, "pomice", None)

    @music_commands_group.command(name="join", description="Join your voice channel.")
    async def join(self, interaction: discord.Interaction):
        pomice_node = self.get_node()
        if pomice_node is None:
            await interaction.response.send_message("Lavalink node not ready yet, please wait.", ephemeral=True)
            return

        if not interaction.user.voice:
            await interaction.response.send_message("You're not in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        vc = await channel.connect(cls=pomice.Player)
        pomice_node.set_player(interaction.guild.id, vc)
        await interaction.response.send_message(f"Joined {channel.name}!")

    @music_commands_group.command(name="leave", description="Leave the voice channel.")
    async def leave(self, interaction: discord.Interaction):
        pomice_node = self.get_node()
        if pomice_node is None:
            await interaction.response.send_message("Lavalink node not ready yet, please wait.", ephemeral=True)
            return

        player: pomice.Player = pomice_node.get_player(interaction.guild.id)
        if not player:
            await interaction.response.send_message("I'm not connected to a voice channel!", ephemeral=True)
            return

        await player.destroy()
        await interaction.response.send_message("Disconnected!")

    @music_commands_group.command(name="play", description="Play a song from YouTube or a URL.")
    @app_commands.describe(search="The name or URL of the song")
    async def play(self, interaction: discord.Interaction, search: str):
        pomice_node = self.get_node()
        if pomice_node is None:
            await interaction.response.send_message("Lavalink node not ready yet, please wait.", ephemeral=True)
            return

        await interaction.response.defer()

        player: pomice.Player = pomice_node.get_player(interaction.guild.id)

        if not player:
            if not interaction.user.voice:
                await interaction.followup.send("You're not in a voice channel!", ephemeral=True)
                return
            channel = interaction.user.voice.channel
            player = await channel.connect(cls=pomice.Player)
            pomice_node.set_player(interaction.guild.id, player)

        try:
            tracks = await player.get_tracks(search)
            if not tracks:
                await interaction.followup.send("No tracks found.")
                return

            track = tracks[0]
            video_id = get_youtube_video_id(track.uri)

            embed = discord.Embed(
                description=f"# 🎶 **Now Playing**\n`{track.title}`\n🔗 [YouTube Link]({track.uri})",
                color=0xd37bff
            )
            if video_id:
                embed.set_thumbnail(url=f"https://i3.ytimg.com/vi/{video_id}/maxresdefault.jpg")
            embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar.url)

            await player.play(track=track)
            await player.set_volume(100)
            await interaction.followup.send(embed=embed)

        except pomice.exceptions.TrackLoadError as e:
            await interaction.followup.send(f"Failed to load track: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))
