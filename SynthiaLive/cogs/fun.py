import random

from discord.ext import commands


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="dice", description="Lance un dé et affiche le résultat (1 à 6).")
    async def dice(self, ctx: commands.Context):
        """Lance un dé et affiche le résultat (1 à 6)."""
        result = random.randint(1, 6)
        await ctx.send(f'🎲 Tu as lancé un dé : **{result}** !')


async def setup(bot):
    # Enregistre les cogs
    await bot.add_cog(Fun(bot))
