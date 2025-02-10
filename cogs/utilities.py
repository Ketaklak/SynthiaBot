from discord.ext import commands
import discord
from datetime import datetime

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}

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
            message = f"✅ {len(deleted) - 1} messages supprimés"
            await ctx.send(message, delete_after=5)
        except discord.Forbidden:
            await ctx.send("❌ Permission manquante", delete_after=5)
        except discord.HTTPException:
            await ctx.send("❌ Erreur de suppression", delete_after=5)

    @commands.hybrid_command(name="afk", description="Définir un message d'absence")
    async def afk(self, ctx: commands.Context, *, reason: str = "Aucune raison donnée"):
        """Définit un message d'absence pour l'utilisateur."""
        self.afk_users[ctx.author.id] = reason
        try:
            await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}")
            await ctx.send(f"✅ Vous êtes maintenant AFK : {reason}", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de changer votre pseudo.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Vérifier si l'utilisateur est en mode AFK
        if message.author.id in self.afk_users:
            # Supprimer le mode AFK
            del self.afk_users[message.author.id]
            try:
                await message.author.edit(nick=message.author.name)
                await message.channel.send(f"📢 {message.author.mention} est de retour !")
            except discord.Forbidden:
                await message.channel.send(f"📢 {message.author.mention} est de retour ! (Je n'ai pas la permission de changer votre pseudo.)")

async def setup(bot):
    await bot.add_cog(Utilities(bot))
