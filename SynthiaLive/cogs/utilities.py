from discord.ext import commands
import discord
from datetime import datetime

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

async def setup(bot):
    await bot.add_cog(Utilities(bot))