from discord.ext import commands
import discord
from datetime import datetime

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}
        self.returned_users = set()

    # ---------------------------------------------------
    # Quelques commandes présentes dans ce ou d'autres cogs
    # ---------------------------------------------------

    @commands.hybrid_command(name="heure", description="Affiche l'heure actuelle")
    async def heure(self, ctx: commands.Context):
        await ctx.send(f"🕒 Il est actuellement **{datetime.now().strftime('%H:%M:%S')}**")

    @commands.hybrid_command(name="serverinfo", description="Affiche les infos du serveur")
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        embed = discord.Embed(
            title=f"Informations sur {guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="👥 Membres", value=guild.member_count)
        embed.add_field(name="📆 Créé le", value=guild.created_at.strftime('%d/%m/%Y %H:%M'))
        embed.add_field(name="👑 Propriétaire", value=guild.owner.mention)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="userinfo", description="Affiche les infos d'un utilisateur")
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(
            title=f"Informations sur {member.display_name}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="🆔 ID", value=member.id)
        embed.add_field(name="📅 Rejoint le", value=member.joined_at.strftime('%d/%m/%Y %H:%M'))
        embed.add_field(name="📝 Compte créé", value=member.created_at.strftime('%d/%m/%Y %H:%M'))
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clear", description="Supprime des messages")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 1):
        if amount < 1 or amount > 100:
            return await ctx.send("❌ Le nombre doit être entre 1 et 100", ephemeral=True)
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            await ctx.send(f"✅ {len(deleted) - 1} messages supprimés", delete_after=5)
        except discord.Forbidden:
            await ctx.send("❌ Permission manquante", delete_after=5)
        except discord.HTTPException:
            await ctx.send("❌ Erreur de suppression", delete_after=5)

    @commands.hybrid_command(name="afk", description="Définir un message d'absence")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def afk(self, ctx: commands.Context, *, reason: str = "Aucune raison donnée"):
        if ctx.author.id in self.afk_users:
            return await ctx.send("Vous êtes déjà en mode AFK.", ephemeral=True)
        self.afk_users[ctx.author.id] = {"reason": reason, "time": datetime.now()}
        try:
            afk_role = discord.utils.get(ctx.guild.roles, name="AFK")
            if afk_role:
                await ctx.author.add_roles(afk_role)
            await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}")
            await ctx.send(f"✅ Vous êtes maintenant AFK : {reason}", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de changer votre pseudo ou de gérer les rôles.", ephemeral=True)

    # ---------------------------------------------------
    # Commande d'aide regroupant les commandes par Cog
    # ---------------------------------------------------
    @commands.hybrid_command(name="help_me", description="Affiche la liste des commandes disponibles")
    async def help_me(self, ctx: commands.Context):
        """
        Affiche une liste de toutes les commandes du bot regroupées par Cog.
        Chaque section correspond à un Cog, c'est-à-dire un regroupement fonctionnel défini
        dans un fichier séparé. Cela signifie que les commandes présentées ici proviennent
        de différents cogs.
        """
        grouped = {}
        # Parcourt toutes les commandes du bot
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue
            # Si la commande n'est pas liée à un cog, on la place dans "Divers"
            cog_name = cmd.cog_name if cmd.cog_name is not None else "Divers"
            grouped.setdefault(cog_name, []).append(cmd)

        embed = discord.Embed(
            title="Liste des commandes",
            description=(
                "Les commandes ci-dessous proviennent de différents cogs.\n"
                "Chaque section correspond à un cog regroupant des fonctionnalités spécifiques."
            ),
            color=discord.Color.blue()
        )

        for cog_name, cmds in grouped.items():
            # Concatène le nom et la description de chaque commande
            cmd_list = "\n".join([f"`/{cmd.name}` - {cmd.description or 'Aucune description'}" for cmd in cmds])
            embed.add_field(name=cog_name, value=cmd_list, inline=False)

        await ctx.send(embed=embed)

    # ---------------------------------------------------
    # Listener on_message pour la gestion du mode AFK
    # ---------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.content.startswith(f"{self.bot.command_prefix}afk"):
            return

        if message.author.id in self.afk_users:
            afk_data = self.afk_users.pop(message.author.id)
            if message.author.id not in self.returned_users:
                self.returned_users.add(message.author.id)
                try:
                    afk_role = discord.utils.get(message.guild.roles, name="AFK")
                    if afk_role:
                        await message.author.remove_roles(afk_role)
                    new_nick = message.author.display_name
                    if new_nick.startswith("[AFK] "):
                        new_nick = new_nick[6:]
                    await message.author.edit(nick=new_nick)
                    embed = discord.Embed(
                        title="Retour d'AFK",
                        description=f"{message.author.mention} est de retour !",
                        color=discord.Color.green()
                    )
                    await message.channel.send(embed=embed)
                except discord.Forbidden:
                    await message.channel.send(
                        f"📢 {message.author.mention} est de retour ! (Je n'ai pas la permission de changer votre pseudo ou de gérer les rôles.)"
                    )

async def setup(bot):
    await bot.add_cog(Utilities(bot))
