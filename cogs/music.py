import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
from collections import deque
import asyncio
import logging

# ---- Configuration youtube-dl ----
YTDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookies': 'logs/cookies.txt'
}

# ---- Configuration FFmpeg ----
FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class Song:
    def __init__(self, data):
        self.data = data
        self.title = data.get('title')
        self.duration = data.get('duration')

class MusicPlayer:
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.queue = deque()
        self.current: Song | None = None
        self.volume = 0.5

    async def play_next(self):
        """Joue la musique suivante dans la file, sinon déconnecte après 60s."""
        if len(self.queue) == 0:
            await self.send_message("✅ File d'attente vide. Déconnexion dans 60 secondes...")
            await asyncio.sleep(60)
            # Si rien ne se joue encore, on quitte
            if self.ctx.voice_client and not self.ctx.voice_client.is_playing():
                await self.ctx.voice_client.disconnect()
            return

        self.current = self.queue.popleft()

        # On ré-extrait une URL fraîche (pour éviter l'expiration des liens)
        webpage_url = self.current.data.get('webpage_url')
        if webpage_url:
            try:
                fresh_info = await asyncio.to_thread(
                    lambda: YoutubeDL(YTDL_OPTS).extract_info(webpage_url, download=False)
                )
                stream_url = fresh_info.get('url')
            except Exception as e:
                logging.error("Erreur lors de la ré-extraction : %s", e)
                stream_url = self.current.data.get('url')
        else:
            stream_url = self.current.data.get('url')

        def after_playing(error):
            if error:
                logging.error("Erreur de lecture : %s", error)
            fut = asyncio.run_coroutine_threadsafe(self.play_next(), self.ctx.bot.loop)
            try:
                fut.result()
            except Exception as exc:
                logging.error("Erreur lors du lancement de la prochaine musique : %s", exc)

        # Vérifier que le bot est toujours connecté au vocal
        if not self.ctx.voice_client or not self.ctx.voice_client.is_connected():
            logging.error("Impossible de lire : pas connecté au vocal.")
            return

        # Lancer la lecture
        source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTS)
        self.ctx.voice_client.play(source, after=after_playing)
        self.ctx.voice_client.source = discord.PCMVolumeTransformer(self.ctx.voice_client.source)
        self.ctx.voice_client.source.volume = self.volume

        await self.send_message(f"🎶 En cours de lecture : **{self.current.title}**")

    async def send_message(self, message):
        if isinstance(self.ctx, discord.Interaction):
            await self.ctx.interaction.followup.send(message)
        else:
            await self.ctx.send(message)

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, MusicPlayer] = {}

    def get_player(self, ctx: commands.Context) -> MusicPlayer:
        """Récupère (ou crée) le MusicPlayer associé au serveur."""
        guild_id = ctx.guild.id
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(ctx)
        return self.players[guild_id]

    # ----------- Commandes -----------

    @commands.hybrid_command(name="join", description="Rejoint le canal vocal")
    async def join(self, ctx: commands.Context):
        """Commande explicite pour se connecter au canal vocal."""
        if isinstance(ctx, discord.Interaction) and not ctx.interaction.response.is_done():
            try:
                await ctx.defer()
            except Exception as e:
                logging.error("Erreur lors du defer : %s", e)

        if not ctx.author.voice:
            return await self.send_message(ctx, "❌ Vous devez être dans un canal vocal !")

        voice_client = ctx.voice_client
        if voice_client:
            if voice_client.channel == ctx.author.voice.channel:
                return await self.send_message(ctx, "✅ Déjà connecté à votre canal vocal !")
            else:
                await voice_client.move_to(ctx.author.voice.channel)
        else:
            await ctx.author.voice.channel.connect()

        await self.send_message(ctx, f"✅ Connecté à {ctx.author.voice.channel.mention}")

    @commands.command(name="play", description="Joue une musique depuis YouTube")
    async def play(self, ctx: commands.Context, *, query: str):
        # 1) Si c'est un slash et qu'on n'a pas encore répondu, on défère immédiatement
        if isinstance(ctx, discord.Interaction) and not ctx.interaction.response.is_done():
            await ctx.defer()  # évite l'erreur "Unknown interaction" si fait dans les 3s

        # 2) Vérifier que l'utilisateur est en vocal
        if not ctx.author.voice:
            msg = "❌ Vous devez être dans un canal vocal !"
            return await self.send_message(ctx, msg)

        # 3) Connecter le bot si besoin
        voice_client = ctx.voice_client
        if voice_client:
            if voice_client.channel != ctx.author.voice.channel:
                await voice_client.move_to(ctx.author.voice.channel)
        else:
            await ctx.author.voice.channel.connect()

        # 4) Extraire les infos YouTube (en thread pour ne pas bloquer l'event loop)
        try:
            info = await asyncio.to_thread(
                lambda: YoutubeDL(YTDL_OPTS).extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            )
        except Exception as e:
            logging.error("Erreur lors de l'extraction (recherche) : %s", e)
            # On retente en direct
            try:
                info = await asyncio.to_thread(
                    lambda: YoutubeDL(YTDL_OPTS).extract_info(query, download=False)
                )
            except Exception as e2:
                logging.error("Erreur lors de l'extraction (direct) : %s", e2)
                msg = "❌ Impossible de trouver la musique demandée."
                return await self.send_message(ctx, msg)

        # 5) Ajouter la musique à la file
        player = self.get_player(ctx)
        song = Song(info)
        player.queue.append(song)

        # 6) Si rien ne joue, on lance la lecture
        if not ctx.voice_client.is_playing():
            await player.play_next()

        # 7) Réponse finale
        final_msg = f"🎵 **{song.title}** ajouté à la file d'attente"
        await self.send_message(ctx, final_msg)

    @commands.hybrid_command(name="queue", description="Affiche la file d'attente")
    async def queue(self, ctx: commands.Context):
        player = self.get_player(ctx)
        if not player.queue:
            return await self.send_message(ctx, "❌ La file d'attente est vide !")

        embed = discord.Embed(title="🎶 File d'attente", color=discord.Color.blue())
        for i, song in enumerate(player.queue, 1):
            embed.add_field(
                name=f"#{i} - {song.title}",
                value=f"Durée : {song.duration}s",
                inline=False
            )
        await self.send_message(ctx, embed=embed)

    @commands.hybrid_command(name="skip", description="Passe à la musique suivante")
    async def skip(self, ctx: commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await self.send_message(ctx, "⏭ Musique suivante...")
        else:
            await self.send_message(ctx, "❌ Aucune musique en cours de lecture !")

    @commands.hybrid_command(name="pause", description="Met la musique en pause")
    async def pause(self, ctx: commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await self.send_message(ctx, "⏸ Musique en pause")
        else:
            await self.send_message(ctx, "❌ Aucune musique en cours de lecture !")

    @commands.hybrid_command(name="resume", description="Reprend la musique")
    async def resume(self, ctx: commands.Context):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await self.send_message(ctx, "▶ Reprise de la lecture")
        else:
            await self.send_message(ctx, "❌ La lecture n'est pas en pause !")

    @commands.hybrid_command(name="volume", description="Ajuste le volume (0-100)")
    async def volume(self, ctx: commands.Context, volume: int):
        if volume < 0 or volume > 100:
            return await self.send_message(ctx, "❌ Le volume doit être entre 0 et 100 !")

        player = self.get_player(ctx)
        player.volume = volume / 100

        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = player.volume

        await self.send_message(ctx, f"🔉 Volume ajusté à {volume}%")

    @commands.hybrid_command(name="leave", description="Fait quitter le canal vocal au bot")
    async def leave(self, ctx: commands.Context):
        """Déconnecte le bot du canal vocal."""
        # Si on est en slash, on "defer" la réponse si besoin
        if isinstance(ctx, discord.Interaction) and not ctx.interaction.response.is_done():
            try:
                await ctx.defer()
            except Exception as e:
                logging.error("Erreur lors du defer : %s", e)

        voice_client = ctx.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            await self.send_message(ctx, "✅ Déconnecté du canal vocal.")
        else:
            await self.send_message(ctx, "❌ Le bot n'est pas connecté à un canal vocal.")

    async def send_message(self, ctx, message):
        if isinstance(ctx, discord.Interaction):
            await ctx.interaction.followup.send(message)
        else:
            await ctx.send(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
