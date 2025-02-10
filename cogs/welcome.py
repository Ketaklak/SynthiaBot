import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="bienvenue")
    @commands.is_owner()
    async def bienvenue(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🏰 Bienvenue dans le Monde des Douze ! 🌍",
            description=(
                "👋 **Salutations, aventuriers, stratèges du Kolizéum et maîtres artisans !** ⚔️✨\n\n"
                "Nous sommes ravis de vous accueillir dans **cette grande communauté dédiée à DOFUS Unity** ! "
                "Que vous soyez un **Xélor méthodique**, un **Iop intrépide**, ou même un **Sadida en pleine sieste**, "
                "ce serveur est votre nouveau **Zaap de ralliement**.\n\n"
                "**||@here**||"  # Ceci est le ping qui sera envoyé
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="📢 **Appel aux héros du Krosmoz !**",
            value=(
                "Le Monde des Douze a besoin de **plus d’aventuriers** pour prospérer ! 🌟\n"
                "Pour cela, nous avons besoin de **VOUS**, que vous soyez un vétéran des guerres d’Allister "
                "ou un nouveau venu cherchant son premier Tofu.\n\n"
                "🔗 **Recrutez vos compagnons de voyage via ce portail dimensionnel :**\n"
                "➡️ **<https://discord.gg/dofus-3>**\n\n"
                "Chaque nouvel arrivant nous rapproche d’un **succès digne d’un drop de Dofus Légendaire** ! 🐉"
            ),
            inline=False
        )

        embed.add_field(
            name="🎉 **Des événements inédits !**",
            value=(
                "Notre but est simple : **vous offrir une expérience unique et des récompenses à la hauteur !**\n"
                "🏆 **Des animations communautaires autour de DOFUS Unity !**\n"
                "🎁 **Des Ogrines et autres cadeaux exclusifs à gagner !**\n"
                "🔥 **Des débats, des conseils et des discussions pour progresser ensemble !**\n\n"
                "Mais **rien de tout cela ne sera possible sans vous** ! Plus nous serons nombreux, "
                "plus nous pourrons organiser des **événements épiques**."
            ),
            inline=False
        )

        embed.set_footer(text="⚡ L’aventure ne fait que commencer… et vous en êtes les héros ! 📜🔥")
        embed.set_image(url="https://www.anomalya.fr/img/banner1.png")

        # Pour que @here soit effectivement envoyé, on autorise les mentions everyone.
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True))

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
