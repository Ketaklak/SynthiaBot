import discord

from discord.ext import commands
from yt_dlp import YoutubeDL
from collections import deque
import asyncio

# Configuration de youtube-dl
YTDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookies': 'logs/cookies.txt'
}

FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}


class Song:
    def __init__(self, source, data):
        self.source = source
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')


class MusicPlayer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.queue = deque()
        self.current = None
        self.volume = 0.5
        self.ydl = YoutubeDL(YTDL_OPTS)

    async def play_next(self):
        if len(self.queue) > 0:
            self.current = self.queue.popleft()

            def after_playing(error):
                if error:
                    print(f'Erreur de lecture: {error}')
                fut = asyncio.run_coroutine_threadsafe(self.play_next(), self.ctx.bot.loop)
                try:
                    fut.result()
                except:
                    pass

            self.current.source = discord.FFmpegPCMAudio(self.current.url, **FFMPEG_OPTS)
            self.ctx.voice_client.play(self.current.source, after=after_playing)
            self.ctx.voice_client.source = discord.PCMVolumeTransformer(self.ctx.voice_client.source)
            self.ctx.voice_client.source.volume = self.volume

            await self.ctx.send(f"🎶 En cours de lecture : **{self.current.title}**")
        else:
            await self.ctx.send("✅ File d'attente vide. Déconnexion dans 60 secondes...")
            await asyncio.sleep(60)
            if not self.ctx.voice_client.is_playing():
                await self.ctx.voice_client.disconnect()


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(ctx)
        return self.players[guild_id]

    @commands.hybrid_command(name="join", description="Rejoint le canal vocal")
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("❌ Vous devez être dans un canal vocal !", ephemeral=True)

        if ctx.voice_client:
            if ctx.voice_client.channel == ctx.author.voice.channel:
                return await ctx.send("✅ Déjà connecté à votre canal vocal !")
            await ctx.voice_client.move_to(ctx.author.voice.channel)
        else:
            await ctx.author.voice.channel.connect()

        await ctx.send(f"✅ Connecté à {ctx.author.voice.channel.mention}")

    @commands.hybrid_command(name="leave", description="Quitte le canal vocal")
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("✅ Déconnecté du canal vocal")
        else:
            await ctx.send("❌ Je ne suis pas dans un canal vocal !")

    @commands.hybrid_command(name="play", description="Joue une musique depuis YouTube")
    async def play(self, ctx, *, query: str):
        await ctx.defer()

        if not ctx.author.voice:
            return await ctx.send("❌ Vous devez être dans un canal vocal !", ephemeral=True)

        player = self.get_player(ctx)

        with player.ydl as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            except:
                info = ydl.extract_info(query, download=False)

            song = Song(None, info)
            player.queue.append(song)

        if not ctx.voice_client.is_playing():
            await player.play_next()

        await ctx.send(f"🎵 **{song.title}** ajouté à la file d'attente")

    @commands.hybrid_command(name="queue", description="Affiche la file d'attente")
    async def queue(self, ctx):
        player = self.get_player(ctx)

        if not player.queue:
            return await ctx.send("❌ La file d'attente est vide !")

        embed = discord.Embed(title="🎶 File d'attente", color=discord.Color.blue())
        for i, song in enumerate(player.queue, 1):
            embed.add_field(
                name=f"#{i} - {song.title}",
                value=f"Durée: {song.duration}s",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="skip", description="Passe à la musique suivante")
    async def skip(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭ Musique suivante...")
        else:
            await ctx.send("❌ Aucune musique en cours de lecture !")

    @commands.hybrid_command(name="pause", description="Met la musique en pause")
    async def pause(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸ Musique en pause")
        else:
            await ctx.send("❌ Aucune musique en cours de lecture !")

    @commands.hybrid_command(name="resume", description="Reprend la musique")
    async def resume(self, ctx):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶ Reprise de la lecture")
        else:
            await ctx.send("❌ La lecture n'est pas en pause !")

    @commands.hybrid_command(name="volume", description="Ajuste le volume (0-100)")
    async def volume(self, ctx, volume: int):
        player = self.get_player(ctx)

        if 0 <= volume <= 100:
            player.volume = volume / 100
            if ctx.voice_client.source:
                ctx.voice_client.source.volume = player.volume
            await ctx.send(f"🔉 Volume ajusté à {volume}%")
        else:
            await ctx.send("❌ Volume doit être entre 0 et 100 !")

    @play.before_invoke
    @skip.before_invoke
    async def ensure_voice(self, ctx):
        if not ctx.voice_client:
            await ctx.invoke(self.join)


async def setup(bot):
    await bot.add_cog(Music(bot))