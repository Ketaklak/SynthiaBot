import discord
from discord.ext import commands
import re
from datetime import datetime, timezone, timedelta
import asyncio
from main import ConfigManager


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup_annonces")
    @commands.has_permissions(administrator=True)
    async def setup_annonces(self, ctx: commands.Context,
                             salon: discord.TextChannel,
                             logs: discord.TextChannel):
        """Configure les salons d'annonces pour CE serveur"""
        ConfigManager.update_guild(ctx.guild.id, "moderation", {
            "announce_channel": salon.id,
            "log_channel": logs.id
        })

        embed = discord.Embed(
            title="Configuration des annonces",
            description="Paramètres sauvegardés avec succès ✅",
            color=0x00ff00
        )
        embed.add_field(name="📢 Salon d'annonces", value=salon.mention)
        embed.add_field(name="📜 Salon des logs", value=logs.mention)

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="annonce")
    @commands.has_permissions(manage_messages=True)
    async def annonce(self, ctx: commands.Context,
                      titre: str,
                      description: str,
                      couleur: str = "vert",
                      image: str = None):
        """Crée une annonce stylisée"""
        # Récupération de la configuration DU SERVEUR
        config = ConfigManager.get_guild(ctx.guild.id, "moderation")

        # Vérification de la configuration
        if not config.get("announce_channel"):
            return await ctx.send(
                "❌ Salon d'annonces non configuré ! Utilisez `/setup_annonces`",
                ephemeral=True,
                delete_after=10
            )

        # Récupération du salon configuré
        channel = self.bot.get_channel(config["announce_channel"])

        if not channel:
            return await ctx.send(
                "❌ Salon d'annonces introuvable ! Vérifiez la configuration.",
                ephemeral=True
            )

        # Validation de la couleur
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

        # Validation de l'image
        if image and not re.match(r'https?://\S+\.(?:png|jpg|jpeg|gif|webp)', image):
            return await ctx.send(
                "❌ URL d'image invalide !",
                ephemeral=True,
                delete_after=10
            )

        # Création de l'embed
        embed = discord.Embed(
            title=titre,
            description=description,
            color=couleurs[couleur.lower()],
            timestamp=datetime.now(timezone.utc)
        )

        # Personnalisation du style
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

        try:
            await channel.send(embed=embed)
            await ctx.send("✅ Annonce publiée !", ephemeral=True, delete_after=5)

            # Suppression du message de commande
            if not ctx.interaction:
                await ctx.message.delete()

            # Logging
            if log_channel := self.bot.get_channel(config.get("log_channel")):
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
        """Configure la modération pour ce serveur"""
        # Création du rôle mute
        mute_role = await self._get_or_create_mute_role(ctx.guild)

        # Sauvegarde de la config
        ConfigManager.update_guild(ctx.guild.id, "moderation", {
            "log_channel": log_channel.id,
            "mute_role": mute_role.id
        })

        embed = discord.Embed(
            title="Configuration de la Modération",
            description="Paramètres sauvegardés avec succès ✅",
            color=0x00ff00
        )
        embed.add_field(name="📜 Salon des logs", value=log_channel.mention)
        embed.add_field(name="🔇 Rôle Mute", value=mute_role.mention)

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context,
                   member: discord.Member,
                   raison: str = "Aucune raison fournie"):
        """Expulse un membre du serveur"""
        try:
            await member.kick(reason=raison)
            await self._log_action(ctx.guild,
                                   f"🚪 **Kick**\n"
                                   f"👤 Utilisateur : {member.mention}\n"
                                   f"🛠️ Modérateur : {ctx.author.mention}\n"
                                   f"📝 Raison : `{raison}`"
                                   )
            await ctx.send(f"✅ {member.display_name} a été expulsé !", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Permission refusée !", ephemeral=True)

    @commands.hybrid_command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context,
                  member: discord.Member,
                  jours: int = 0,
                  raison: str = "Aucune raison fournie"):
        """Bannit un membre du serveur"""
        try:
            await member.ban(delete_message_days=jours, reason=raison)
            await self._log_action(ctx.guild,
                                   f"🔨 **Ban**\n"
                                   f"👤 Utilisateur : {member.mention}\n"
                                   f"🗑️ Messages supprimés : {jours} jours\n"
                                   f"🛠️ Modérateur : {ctx.author.mention}\n"
                                   f"📝 Raison : `{raison}`"
                                   )
            await ctx.send(f"✅ {member.display_name} a été banni !", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Permission refusée !", ephemeral=True)

    @commands.hybrid_command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context,
                    user: discord.User):
        """Lève le bannissement d'un utilisateur"""
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
        """Mute un membre (ex: 1h, 30m)"""
        await ctx.defer(ephemeral=True)

        config = ConfigManager.get_guild(ctx.guild.id, "moderation")
        mute_role = ctx.guild.get_role(config.get("mute_role"))

        if not mute_role:
            return await ctx.send("❌ Configuration manquante ! Utilisez `/setup_moderation`", ephemeral=True)

        try:
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
        except discord.Forbidden:
            await ctx.send("❌ Permission refusée !", ephemeral=True)

    async def _get_or_create_mute_role(self, guild: discord.Guild) -> discord.Role:
        """Crée le rôle mute si inexistant"""
        config = ConfigManager.get_guild(guild.id, "moderation")
        if role_id := config.get("mute_role"):
            return guild.get_role(role_id)

        # Création du rôle
        role = await guild.create_role(
            name="Muted",
            color=discord.Color.dark_grey(),
            reason="Création automatique du rôle mute"
        )

        # Configuration des permissions
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
        """Convertit la durée en timedelta"""
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            count = int(duration[:-1])
            unit = duration[-1].lower()
            return timedelta(seconds=count * units[unit])
        except (KeyError, ValueError):
            raise commands.BadArgument("Format invalide (ex: 1h, 30m)")

    async def _schedule_unmute(self, member: discord.Member, delta: timedelta):
        """Programme le unmute automatique"""
        await asyncio.sleep(delta.total_seconds())
        config = ConfigManager.get_guild(member.guild.id, "moderation")
        if mute_role := member.guild.get_role(config.get("mute_role")):
            await member.remove_roles(mute_role)

    async def _log_action(self, guild: discord.Guild, description: str):
        """Envoie les logs de modération"""
        config = ConfigManager.get_guild(guild.id, "moderation")
        if log_channel := self.bot.get_channel(config.get("log_channel")):
            embed = discord.Embed(
                title="Journal de Modération",
                description=description,
                color=0xFF0000,
                timestamp=datetime.now()
            )
            await log_channel.send(embed=embed)



async def setup(bot):
    await bot.add_cog(Moderation(bot))