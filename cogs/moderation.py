import discord
from discord.ext import commands, tasks
import re
from datetime import datetime, timezone, timedelta
import asyncio
from main import ConfigManager
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings = {}
        self.temp_roles = {}
        self.pending_actions = {}
        self.check_temp_roles.start()
        self.check_pending_actions.start()

    @commands.hybrid_command(name="setup_annonces")
    @commands.has_permissions(administrator=True)
    async def setup_annonces(self, ctx: commands.Context,
                             salon: discord.TextChannel,
                             logs: discord.TextChannel):
        """Configure les salons d'annonces pour ce serveur."""
        ConfigManager.update_guild(ctx.guild.id, "moderation", {
            "announce_channel": salon.id,
            "log_channel": logs.id
        })

        embed = self._create_embed(
            title="Configuration des annonces",
            description="Paramètres sauvegardés avec succès ✅",
            fields=[
                ("📢 Salon d'annonces", salon.mention),
                ("📜 Salon des logs", logs.mention)
            ],
            color=0x00ff00
        )

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="annonce")
    @commands.has_permissions(manage_messages=True)
    async def annonce(self, ctx: commands.Context,
                      titre: str,
                      description: str,
                      couleur: str = "vert",
                      image: str = None):
        """Crée une annonce stylisée."""
        config = ConfigManager.get_guild(ctx.guild.id, "moderation")

        if not config.get("announce_channel"):
            return await ctx.send(
                "❌ Salon d'annonces non configuré ! Utilisez `/setup_annonces`",
                ephemeral=True,
                delete_after=10
            )

        channel = self.bot.get_channel(config["announce_channel"])

        if not channel:
            return await ctx.send(
                "❌ Salon d'annonces introuvable ! Vérifiez la configuration.",
                ephemeral=True
            )

        couleurs = {
            "urgent": discord.Color.red(),
            "infos": discord.Color.gold(),
            "basique": discord.Color.green()
        }

        if couleur.lower() not in couleurs:
            return await ctx.send(
                "❌ Couleur invalide ! Options : urgent/infos/basique",
                ephemeral=True,
                delete_after=10
            )

        if image and not re.match(r'https?://\S+\.(?:png|jpg|jpeg|gif|webp)', image):
            return await ctx.send(
                "❌ URL d'image invalide !",
                ephemeral=True,
                delete_after=10
            )

        embed = self._create_embed(
            title=titre,
            description=description,
            color=couleurs[couleur.lower()],
            timestamp=datetime.now(timezone.utc)
        )

        types_annonces = {
            "urgent": "🔴 URGENCE",
            "infos": "🟡 INFORMATION",
            "basique": "🟢 ANNONCE"
        }

        embed.set_author(name=f"{types_annonces[couleur.lower()]} - {ctx.guild.name}")

        if image:
            embed.set_image(url=image)

        embed.set_footer(
            text=f"Publié par {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )

        await self._send_announce(channel, embed, ctx)

    async def _send_announce(self, channel, embed, ctx):
        try:
            await channel.send(embed=embed)
            await ctx.send("✅ Annonce publiée !", ephemeral=True, delete_after=5)

            if not ctx.interaction:
                await ctx.message.delete()

            if log_channel := self.bot.get_channel(ConfigManager.get_guild(ctx.guild.id, "moderation").get("log_channel")):
                await log_channel.send(
                    f"📢 Nouvelle annonce par {ctx.author.mention}",
                    embed=embed
                )

        except discord.Forbidden:
            await ctx.send(
                "❌ Permission refusée ! Vérifiez les droits du bot.",
                ephemeral=True
            )

    @commands.hybrid_command(name="setup_moderation")
    @commands.has_permissions(administrator=True)
    async def setup_moderation(self, ctx: commands.Context,
                               log_channel: discord.TextChannel):
        """Configure la modération pour ce serveur."""
        mute_role = await self._get_or_create_mute_role(ctx.guild)

        ConfigManager.update_guild(ctx.guild.id, "moderation", {
            "log_channel": log_channel.id,
            "mute_role": mute_role.id
        })

        embed = self._create_embed(
            title="Configuration de la Modération",
            description="Paramètres sauvegardés avec succès ✅",
            fields=[
                ("📜 Salon des logs", log_channel.mention),
                ("🔇 Rôle Mute", mute_role.mention)
            ],
            color=0x00ff00
        )

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context,
                   member: discord.Member,
                   raison: str = "Aucune raison fournie"):
        """Expulse un membre du serveur."""
        await self._moderate_member(ctx, member, "kick", raison)

    @commands.hybrid_command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context,
                  member: discord.Member,
                  jours: int = 0,
                  raison: str = "Aucune raison fournie"):
        """Bannit un membre du serveur."""
        await self._moderate_member(ctx, member, "ban", raison, jours)

    @commands.hybrid_command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context,
                    user: discord.User):
        """Lève le bannissement d'un utilisateur."""
        try:
            await ctx.guild.unban(user)
            await self._log_action(ctx.guild,
                                   f"🎉 **Unban**\n"
                                   f"👤 Utilisateur : {user.mention}\n"
                                   f"🛠️ Modérateur : {ctx.author.mention}"
                                   )
            await ctx.send(f"✅ {user.name} a été débanni !", ephemeral=True)
        except discord.NotFound:
            await ctx.send("❌ Utilisateur non banni !", ephemeral=True)

    @commands.hybrid_command(name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context,
                   member: discord.Member,
                   duree: str = "permanent",
                   raison: str = "Aucune raison fournie"):
        """Mute un membre (ex: 1h, 30m)."""
        await ctx.defer(ephemeral=True)

        config = ConfigManager.get_guild(ctx.guild.id, "moderation")
        mute_role = ctx.guild.get_role(config.get("mute_role"))

        if not mute_role:
            return await ctx.send("❌ Configuration manquante ! Utilisez `/setup_moderation`", ephemeral=True)

        await member.add_roles(mute_role, reason=raison)
        await self._log_action(ctx.guild,
                               f"🔇 **Mute**\n"
                               f"👤 Utilisateur : {member.mention}\n"
                               f"⏱️ Durée : {duree}\n"
                               f"🛠️ Modérateur : {ctx.author.mention}\n"
                               f"📝 Raison : `{raison}`"
                               )

        if duree != "permanent":
            delta = self._parse_duration(duree)
            await self._schedule_unmute(member, delta)

        await ctx.send(f"✅ {member.display_name} a été mute !", ephemeral=True)

    @commands.hybrid_command(name="warn")
    @commands.has_permissions(manage_roles=True)
    async def warn(self, ctx: commands.Context,
                   member: discord.Member,
                   raison: str = "Aucune raison fournie"):
        """Avertit un membre."""
        await self._warn_member(ctx, member, raison)

    @commands.hybrid_command(name="temprole")
    @commands.has_permissions(manage_roles=True)
    async def temprole(self, ctx: commands.Context,
                       member: discord.Member,
                       role: discord.Role,
                       duree: str):
        """Assigne un rôle temporaire à un membre."""
        delta = self._parse_duration(duree)
        await member.add_roles(role, reason="Rôle temporaire")

        self.temp_roles[(ctx.guild.id, member.id)] = (role.id, datetime.now(timezone.utc) + delta)
        await ctx.send(f"✅ Rôle temporaire assigné à {member.display_name} pour {duree} !", ephemeral=True)

    @tasks.loop(seconds=60)
    async def check_temp_roles(self):
        """Vérifie et supprime les rôles temporaires expirés."""
        now = datetime.now(timezone.utc)
        to_remove = []

        for (guild_id, member_id), (role_id, end_time) in self.temp_roles.items():
            if now >= end_time:
                guild = self.bot.get_guild(guild_id)
                member = guild.get_member(member_id)
                role = guild.get_role(role_id)

                if member and role:
                    await member.remove_roles(role, reason="Fin du rôle temporaire")
                    to_remove.append((guild_id, member_id))

        for key in to_remove:
            del self.temp_roles[key]

    @commands.hybrid_command(name="remindme")
    @commands.has_permissions(manage_roles=True)
    async def remindme(self, ctx: commands.Context,
                        action: str,
                        duree: str):
        """Envoie un rappel pour une action après une durée spécifiée."""
        delta = self._parse_duration(duree)
        end_time = datetime.now(timezone.utc) + delta
        self.pending_actions[(ctx.guild.id, ctx.author.id)] = (action, end_time)
        await ctx.send(f"✅ Rappel programmé pour l'action `{action}` dans {duree}.", ephemeral=True)

    @tasks.loop(seconds=60)
    async def check_pending_actions(self):
        """Vérifie et envoie des rappels pour les actions en attente."""
        now = datetime.now(timezone.utc)
        to_remind = []

        for (guild_id, user_id), (action, end_time) in self.pending_actions.items():
            if now >= end_time:
                guild = self.bot.get_guild(guild_id)
                member = guild.get_member(user_id)

                if member:
                    await member.send(f"🕒 Rappel : Vous avez demandé à être rappelé pour l'action `{action}`.")
                    to_remind.append((guild_id, user_id))

        for key in to_remind:
            del self.pending_actions[key]

    @commands.hybrid_command(name="stats")
    @commands.has_permissions(administrator=True)
    async def stats(self, ctx: commands.Context):
        """Affiche les statistiques de modération."""
        config = ConfigManager.get_guild(ctx.guild.id, "moderation")
        log_channel = self.bot.get_channel(config.get("log_channel"))

        if not log_channel:
            return await ctx.send("❌ Salon des logs non configuré !", ephemeral=True)

        total_warns = sum(self.warnings.get(ctx.guild.id, {}).values())

        embed = self._create_embed(
            title="Statistiques de Modération",
            description="Statistiques des actions de modération",
            fields=[("Avertissements", total_warns)],
            color=0x00ff00
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="feedback")
    async def feedback(self, ctx: commands.Context, *, message: str):
        """Permet aux utilisateurs de donner du feedback sur les actions de modération."""
        config = ConfigManager.get_guild(ctx.guild.id, "moderation")
        log_channel = self.bot.get_channel(config.get("log_channel"))

        if not log_channel:
            return await ctx.send("❌ Salon des logs non configuré !", ephemeral=True)

        embed = discord.Embed(
            title="Feedback reçu",
            description=f"**Utilisateur** : {ctx.author.mention}\n\n**Feedback** : {message}",
            color=0x3498db
        )
        await log_channel.send(embed=embed)
        await ctx.send("Merci pour votre feedback !", ephemeral=True)

    @commands.hybrid_command(name="lockdown")
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx: commands.Context, salon: discord.TextChannel):
        """Verrouille un salon pour empêcher les membres d'envoyer des messages."""
        overwrite = salon.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await salon.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"✅ {salon.mention} est maintenant verrouillé !", ephemeral=True)

    @commands.hybrid_command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, salon: discord.TextChannel, delai: int):
        """Active le mode lent dans un salon."""
        await salon.edit(slowmode_delay=delai)
        await ctx.send(f"✅ Mode lent activé dans {salon.mention} avec un délai de {delai} secondes !", ephemeral=True)

    @commands.hybrid_command(name="nick")
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx: commands.Context, member: discord.Member, *, surnom: str):
        """Change le surnom d'un membre."""
        try:
            await member.edit(nick=surnom)
            await ctx.send(f"✅ Surnom de {member.mention} changé en `{surnom}` !", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Permission refusée !", ephemeral=True)
        except discord.HTTPException as e:
            await ctx.send(f"❌ Erreur lors du changement de surnom : {e}", ephemeral=True)

    @commands.hybrid_command(name="prune")
    @commands.has_permissions(kick_members=True)
    async def prune(self, ctx: commands.Context, days: int):
        """Supprime les membres inactifs du serveur avec confirmation."""
        if days < 1 or days > 30:
            return await ctx.send("❌ Le nombre de jours doit être compris entre 1 et 30.", ephemeral=True)

        # Demande de confirmation
        confirm_message = await ctx.send(
            f"Attention ! Vous êtes sur le point de supprimer les membres inactifs depuis plus de {days} jours. "
            "Êtes-vous sûr de vouloir continuer ? Répondez par `oui` ou `non`."
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["oui", "non"]

        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("❌ Opération annulée. Vous n'avez pas répondu à temps.", ephemeral=True)

        if response.content.lower() == "non":
            return await ctx.send("❌ Opération annulée.", ephemeral=True)

        pruned = await ctx.guild.prune_members(days=days, compute_prune_count=True)

        if pruned:
            await ctx.send(f"✅ {pruned} membres inactifs depuis plus de {days} jours ont été supprimés.",
                           ephemeral=True)
        else:
            await ctx.send(f"❌ Aucun membre inactif n'a été trouvé ou supprimé.", ephemeral=True)

    async def _get_or_create_mute_role(self, guild: discord.Guild) -> discord.Role:
        """Crée le rôle mute si inexistant."""
        config = ConfigManager.get_guild(guild.id, "moderation")
        if role_id := config.get("mute_role"):
            return guild.get_role(role_id)

        role = await guild.create_role(
            name="Muted",
            color=discord.Color.dark_grey(),
            reason="Création automatique du rôle mute"
        )

        for channel in guild.channels:
            await channel.set_permissions(
                role,
                send_messages=False,
                add_reactions=False,
                speak=False
            )

        ConfigManager.update_guild(guild.id, "moderation", {"mute_role": role.id})
        return role

    def _parse_duration(self, duration: str) -> timedelta:
        """Convertit la durée en timedelta."""
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            count = int(duration[:-1])
            unit = duration[-1].lower()
            return timedelta(seconds=count * units[unit])
        except (KeyError, ValueError):
            raise commands.BadArgument("Format invalide (ex: 1h, 30m)")

    async def _schedule_unmute(self, member: discord.Member, delta: timedelta):
        """Programme le unmute automatique."""
        await asyncio.sleep(delta.total_seconds())
        config = ConfigManager.get_guild(member.guild.id, "moderation")
        if mute_role := member.guild.get_role(config.get("mute_role")):
            await member.remove_roles(mute_role)

    async def _log_action(self, guild: discord.Guild, description: str):
        """Envoie les logs de modération."""
        config = ConfigManager.get_guild(guild.id, "moderation")
        if log_channel := self.bot.get_channel(config.get("log_channel")):
            embed = self._create_embed(
                title="Journal de Modération",
                description=description,
                color=0xFF0000,
                timestamp=datetime.now(timezone.utc)
            )
            await log_channel.send(embed=embed)

    def _create_embed(self, title: str, description: str, fields: list = None, color: discord.Color = discord.Color.blue()) -> discord.Embed:
        """Crée un embed discord."""
        embed = discord.Embed(title=title, description=description, color=color)
        if fields:
            for name, value in fields:
                embed.add_field(name=name, value=value, inline=False)
        return embed

    async def _moderate_member(self, ctx, member, action, raison, jours=0):
        """Modère un membre (kick/ban)."""
        try:
            if action == "kick":
                await member.kick(reason=raison)
                action_str = "🚪 **Kick**"
            elif action == "ban":
                await member.ban(delete_message_days=jours, reason=raison)
                action_str = "🔨 **Ban**"

            await self._log_action(ctx.guild,
                                   f"{action_str}\n"
                                   f"👤 Utilisateur : {member.mention}\n"
                                   f"🛠️ Modérateur : {ctx.author.mention}\n"
                                   f"📝 Raison : `{raison}`"
                                   )
            await ctx.send(f"✅ {member.display_name} a été {action}é !", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Permission refusée !", ephemeral=True)

    async def _warn_member(self, ctx, member, raison):
        """Avertit un membre."""
        try:
            if ctx.guild.id not in self.warnings:
                self.warnings[ctx.guild.id] = {}

            if member.id not in self.warnings[ctx.guild.id]:
                self.warnings[ctx.guild.id][member.id] = 0

            self.warnings[ctx.guild.id][member.id] += 1

            await self._log_action(ctx.guild,
                                   f"⚠️ **Avertissement**\n"
                                   f"👤 Utilisateur : {member.mention}\n"
                                   f"🛠️ Modérateur : {ctx.author.mention}\n"
                                   f"📝 Raison : `{raison}`\n"
                                   f"🔢 Nombre d'avertissements : {self.warnings[ctx.guild.id][member.id]}"
                                   )

            if self.warnings[ctx.guild.id][member.id] >= 3:
                await member.ban(reason="Trop d'avertissements")
                await ctx.send(f"✅ {member.display_name} a été banni pour trop d'avertissements !", ephemeral=True)
            else:
                await ctx.send(f"✅ {member.display_name} a été averti !", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Permission refusée !", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
