import aiosqlite
from discord.ext import commands, tasks
import discord
import random
from datetime import datetime

class ComprehensiveLeveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "leveling_data.db"
        self.create_table()
        self.update_leaderboard.start()

    async def create_table(self):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    xp INTEGER,
                    level INTEGER,
                    last_claimed TEXT,
                    badges TEXT,
                    credits INTEGER DEFAULT 0
                )
            ''')
            # Ajouter la colonne credits si elle n'existe pas
            try:
                await conn.execute("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0")
            except aiosqlite.OperationalError:
                pass  # La colonne existe déjà
            await conn.commit()

    async def get_user(self, user_id):
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return await cursor.fetchone()

    async def insert_or_update_user(self, user_id, xp, level, last_claimed, badges, credits):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                INSERT INTO users (user_id, xp, level, last_claimed, badges, credits)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                xp = excluded.xp,
                level = excluded.level,
                last_claimed = excluded.last_claimed,
                badges = excluded.badges,
                credits = excluded.credits
            ''', (user_id, xp, level, last_claimed, badges, credits))
            await conn.commit()

    def calculate_level(self, xp):
        return int((xp // 100) ** 0.55)

    def calculate_xp(self, level):
        return int((level ** 2) * 100)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = str(message.author.id)
        xp_gain = random.randint(15, 25)

        user = await self.get_user(user_id)
        if user is None:
            await self.insert_or_update_user(user_id, xp_gain, 0, None, "", 0)
            xp = xp_gain
            credits = 0
        else:
            xp = user[1] + xp_gain
            credits = user[5] if len(user) > 5 else 0

        new_level = self.calculate_level(xp)
        badges = user[4].split(",") if user and user[4] else []

        if new_level > (user[2] if user else 0):
            badges.append(f"Level {new_level}")
            await self.assign_role(message.author, new_level)
            await message.channel.send(
                f"🎉 Félicitations {message.author.mention}, vous êtes passé au niveau **{new_level}** !"
            )
            await message.author.send(f"Félicitations ! Vous êtes passé au niveau **{new_level}** !")

        await self.insert_or_update_user(user_id, xp, new_level, None, ",".join(badges), credits)

    async def assign_role(self, member, level):
        role_name = f"Level {level}"
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role:
            await member.add_roles(role)

    @commands.hybrid_command(name="rank", description="Affiche le rang de l'utilisateur")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        user_id = str(member.id)
        user = await self.get_user(user_id)

        if user is None:
            await ctx.send("Cet utilisateur n'a pas encore de données de niveau.")
            return

        level = user[2]
        xp = user[1]
        next_level_xp = self.calculate_xp(level + 1)
        xp_needed = next_level_xp - xp
        badges = user[4].split(",") if user[4] else []
        credits = user[5] if len(user) > 5 else 0

        progress_bar = "█" * int((xp / next_level_xp) * 10)

        embed = discord.Embed(
            title=f"Rang de {member.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Niveau", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"**{xp}** / **{next_level_xp}**", inline=True)
        embed.add_field(name="XP restant", value=f"**{xp_needed}**", inline=True)
        embed.add_field(name="Progression", value=f"[{progress_bar}]", inline=False)
        embed.add_field(name="Badges", value=", ".join(badges) or "Aucun badge", inline=False)
        embed.add_field(name="Crédits", value=f"**{credits}**", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Continuez à être actif pour gagner plus d'XP et de badges !")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="leaderboard", description="Affiche le classement des utilisateurs")
    async def leaderboard(self, ctx: commands.Context):
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM users ORDER BY xp DESC LIMIT 10")
            sorted_users = await cursor.fetchall()

        embed = discord.Embed(
            title="Classement",
            description="Top 10 des utilisateurs par XP",
            color=discord.Color.gold()
        )

        for index, user in enumerate(sorted_users, start=1):
            member = ctx.guild.get_member(int(user[0]))
            if member:
                embed.add_field(
                    name=f"{index}. {member.display_name}",
                    value=f"Niveau **{user[2]}** - XP **{user[1]}**",
                    inline=False
                )

        embed.set_footer(text="Soyez actif pour monter dans le classement et gagner des badges !")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="daily", description="Réclamez votre récompense quotidienne")
    @commands.cooldown(1, 86400, commands.BucketType.user)  # Cooldown de 24 heures
    async def daily(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        daily_reward = 100

        user = await self.get_user(user_id)
        if user and user[3] and (datetime.now() - datetime.fromisoformat(user[3])).days < 1:
            await ctx.send("Vous avez déjà réclamé votre récompense quotidienne aujourd'hui !", ephemeral=True)
            return

        new_xp = user[1] + daily_reward if user else daily_reward
        new_credits = user[5] + 50 if user and len(user) > 5 else 50
        await self.insert_or_update_user(user_id, new_xp, self.calculate_level(new_xp), datetime.now().isoformat(), user[4] if user else "", new_credits)

        await ctx.send(f"Vous avez réclamé votre récompense quotidienne de **{daily_reward}** XP et **50** crédits !")

    @commands.hybrid_command(name="redeem", description="Échangez vos crédits contre des récompenses")
    async def redeem(self, ctx: commands.Context, reward: str):
        user_id = str(ctx.author.id)
        user = await self.get_user(user_id)

        if user is None:
            await ctx.send("Vous n'avez pas encore de crédits.")
            return

        # Exemple de récompenses
        rewards = {
            "role_special": 100,
            "badge_exclusif": 150
        }

        if reward not in rewards:
            await ctx.send("Récompense invalide. Veuillez choisir une récompense valide.")
            return

        if user[5] < rewards[reward]:
            await ctx.send("Vous n'avez pas assez de crédits pour cette récompense.")
            return

        new_credits = user[5] - rewards[reward]
        new_badges = user[4].split(",") if user[4] else []

        if reward == "badge_exclusif":
            new_badges.append("Badge Exclusif")

        await self.insert_or_update_user(user_id, user[1], user[2], user[3], ",".join(new_badges), new_credits)

        await ctx.send(f"Vous avez échangé vos crédits contre **{reward}** !")

    @tasks.loop(hours=24)
    async def update_leaderboard(self):
        # Logique pour mettre à jour le classement quotidiennement, si nécessaire
        pass

async def setup(bot):
    await bot.add_cog(ComprehensiveLeveling(bot))
